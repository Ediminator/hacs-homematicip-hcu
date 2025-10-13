from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import HcuApiClient, HcuApiError
from .const import CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
from .entity import HcuGroupBaseEntity

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.CLIMATE):
        async_add_entities(entities)


class HcuClimate(HcuGroupBaseEntity, ClimateEntity):
    """Representation of a Homematic IP HCU heating group."""

    PLATFORM = Platform.CLIMATE
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_has_entity_name = False  # Use the group name as the entity name
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        group_data: dict,
        config_entry: ConfigEntry,
    ):
        super().__init__(coordinator, client, group_data)
        self._attr_name = self._group.get("label")
        self._attr_unique_id = self._group_id
        self._config_entry = config_entry
        self._profiles: dict[str, str] = {}

        # Dynamically build the list of supported presets from the group's profiles
        self._attr_preset_modes = [PRESET_NONE, PRESET_BOOST, PRESET_COMFORT]
        for profile in self._group.get("profiles", {}).values():
            if profile.get("enabled") and profile.get("visible") and profile.get("name"):
                profile_name = profile["name"].lower()
                self._attr_preset_modes.append(profile_name)
                self._profiles[profile_name] = profile["index"]

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        return features

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if not self._group.get("controllable", True):
            return HVACMode.OFF

        control_mode = self._group.get("controlMode")
        if control_mode == "MANUAL":
            # Emulate OFF mode if the temperature is set to the minimum.
            if self.target_temperature is not None and self.target_temperature <= self.min_temp:
                return HVACMode.OFF
            return HVACMode.HEAT
        
        if control_mode == "AUTOMATIC":
            return HVACMode.AUTO
        
        # Fallback case, default to OFF if no mode is matched.
        return HVACMode.OFF

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._group.get("actualTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._group.get("setPointTemperature")

    @property
    def min_temp(self) -> float:
        """Return the minimum supported temperature."""
        return self._group.get("minTemperature", 4.5)

    @property
    def max_temp(self) -> float:
        """Return the maximum supported temperature."""
        return self._group.get("maxTemperature", 30.5)

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if self._group.get("boostMode"):
            return PRESET_BOOST
        
        active_profile_index = self._group.get("activeProfile")
        for name, index in self._profiles.items():
            if index == active_profile_index:
                return name
            
        # Check for our custom 'comfort' preset
        comfort_temp = self._config_entry.options.get(
            CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
        )
        if (
            self.hvac_mode == HVACMode.HEAT
            and self.target_temperature == comfort_temp
        ):
            return PRESET_COMFORT

        return PRESET_NONE

    async def _async_set_group_property(self, method: str, *args, **kwargs) -> None:
        """Optimistically update state and call the API."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            api_method = getattr(self._client, method)
            await api_method(*args, **kwargs)
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set property for %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        # When changing temperature manually, the mode should switch to manual (HEAT).
        if self._group.get("controlMode") == "AUTOMATIC":
            await self._async_set_group_property(
                "async_set_group_control_mode", group_id=self._group_id, mode="MANUAL"
            )

        await self._async_set_group_property(
            "async_set_group_setpoint_temperature",
            group_id=self._group_id,
            temperature=temperature,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode == HVACMode.AUTO:
            await self._async_set_group_property(
                "async_set_group_control_mode", group_id=self._group_id, mode="AUTOMATIC"
            )
        elif hvac_mode == HVACMode.HEAT:
            # When switching to HEAT from OFF, set a comfortable temperature.
            if self.hvac_mode == HVACMode.OFF:
                comfort_temp = self._config_entry.options.get(
                    CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
                )
                await self._async_set_group_property(
                    "async_set_group_setpoint_temperature",
                    group_id=self._group_id,
                    temperature=comfort_temp,
                )
            # Ensure mode is set to MANUAL for HEAT
            await self._async_set_group_property(
                "async_set_group_control_mode", group_id=self._group_id, mode="MANUAL"
            )
        elif hvac_mode == HVACMode.OFF:
            # Emulate 'OFF' by setting manual mode and the minimum temperature.
            await self._async_set_group_property(
                "async_set_group_control_mode", group_id=self._group_id, mode="MANUAL"
            )
            await self._async_set_group_property(
                "async_set_group_setpoint_temperature",
                group_id=self._group_id,
                temperature=self.min_temp,
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_BOOST:
            await self._async_set_group_property(
                "async_set_group_boost", group_id=self._group_id, boost=True
            )
        elif preset_mode == PRESET_COMFORT:
            comfort_temp = self._config_entry.options.get(
                CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
            )
            await self.async_set_hvac_mode(HVACMode.HEAT)
            await self.async_set_temperature(temperature=comfort_temp)
            
        elif preset_mode in self._profiles:
            await self._async_set_group_property(
                "async_set_group_control_mode", group_id=self._group_id, mode="AUTOMATIC", profile=self._profiles[preset_mode]
            )
        elif preset_mode == PRESET_NONE:
            # When turning off a preset, revert to AUTOMATIC mode.
            if self.preset_mode == PRESET_BOOST:
                await self._async_set_group_property(
                    "async_set_group_boost", group_id=self._group_id, boost=False
                )
            else:
                 await self._async_set_group_property(
                    "async_set_group_control_mode", group_id=self._group_id, mode="AUTOMATIC"
            )