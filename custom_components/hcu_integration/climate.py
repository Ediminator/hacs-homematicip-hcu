from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from datetime import timedelta

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    PRESET_BOOST,
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import HcuApiClient, HcuApiError
from .const import (
    CONF_COMFORT_TEMPERATURE,
    DEFAULT_COMFORT_TEMPERATURE,
    PRESET_ECO,
    PRESET_PARTY,
)
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
        self._default_profile_index: str | None = None

        # Dynamically build the list of supported presets from the group's profiles.
        self._attr_preset_modes = [PRESET_NONE, PRESET_BOOST, PRESET_ECO, PRESET_PARTY]
        profile_indices: list[str] = []
        for profile in self._group.get("profiles", {}).values():
            if profile.get("enabled") and profile.get("visible"):
                profile_index = profile["index"]
                # Use the given name, or default to "Standard" if empty.
                profile_name = profile.get("name") or "Standard"
                
                self._profiles[profile_name] = profile_index
                self._attr_preset_modes.append(profile_name)
                profile_indices.append(profile_index)
        
        if profile_indices:
            # Assume the lowest indexed profile is the default 'auto' schedule.
            self._default_profile_index = sorted(profile_indices)[0]

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return the list of supported features."""
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
        )
        return features
    
    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._group.get("humidity")

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
        
        if control_mode in ("AUTOMATIC", "ECO"):
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
        heating_home = self._client.state.get("home", {}).get("functionalHomes", {}).get("HEATING", {})
        if heating_home.get("absenceType") == "PERMANENT":
            return heating_home.get("ecoTemperature")
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
        
        heating_home = self._client.state.get("home", {}).get("functionalHomes", {}).get("HEATING", {})
        if heating_home.get("absenceType") == "PERMANENT":
            return PRESET_ECO

        if self._group.get("partyMode") == "ACTIVE":
            return PRESET_PARTY
        
        active_profile_index = self._group.get("activeProfile")
        for name, index in self._profiles.items():
            if index == active_profile_index:
                # If the active profile is the default one, don't report it as a custom preset.
                if index == self._default_profile_index:
                    break
                return name

        return PRESET_NONE

    async def _async_set_group_property(self, method: str, *args: Any, **kwargs: Any) -> None:
        """Optimistically update state and call a group-level API method."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            api_method = getattr(self._client, method)
            await api_method(*args, **kwargs)
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set group property for %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def _async_set_home_property(self, method: str, *args: Any, **kwargs: Any) -> None:
        """Optimistically update state and call a home-level API method."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            api_method = getattr(self._client, method)
            await api_method(*args, **kwargs)
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set home property for %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        # When temperature is changed while in AUTO mode, switch to MANUAL mode.
        if self.hvac_mode == HVACMode.AUTO:
            await self._async_set_group_property(
                "async_set_group_control_mode", 
                group_id=self._group_id, 
                mode="MANUAL"
            )

        await self._async_set_group_property(
            "async_set_group_setpoint_temperature",
            group_id=self._group_id,
            temperature=temperature,
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            if hvac_mode == HVACMode.AUTO:
                await self._client.async_set_group_control_mode(self._group_id, "AUTOMATIC")
            elif hvac_mode == HVACMode.HEAT:
                if self.target_temperature and self.target_temperature <= self.min_temp:
                    comfort_temp = self._config_entry.options.get(
                        CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
                    )
                    await self._client.async_set_group_setpoint_temperature(
                        self._group_id, comfort_temp
                    )
                await self._client.async_set_group_control_mode(self._group_id, "MANUAL")
            elif hvac_mode == HVACMode.OFF:
                await self._client.async_set_group_setpoint_temperature(
                    self._group_id, self.min_temp
                )
                await self._client.async_set_group_control_mode(self._group_id, "MANUAL")
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set HVAC mode for %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()


    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == PRESET_BOOST:
            await self._async_set_group_property(
                "async_set_group_boost", group_id=self._group_id, boost=True
            )
            
        elif preset_mode == PRESET_ECO:
            await self._async_set_home_property("async_activate_absence_permanent")
            
        elif preset_mode == PRESET_PARTY:
            comfort_temp = self._config_entry.options.get(
                CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
            )
            end_time = dt_util.now() + timedelta(hours=4)
            await self._async_set_group_property(
                "async_activate_group_party_mode",
                group_id=self._group_id,
                temperature=comfort_temp,
                end_time=end_time.strftime("%Y_%m_%d %H:%M"),
            )

        elif preset_mode in self._profiles:
            # First, ensure the HVAC mode is AUTO, as profiles only work in this mode.
            await self._async_set_group_property(
                "async_set_group_control_mode", group_id=self._group_id, mode="AUTOMATIC"
            )
            # Then, set the active profile using the correct API call.
            profile_index = self._profiles[preset_mode]
            await self._async_set_group_property(
                "async_set_group_active_profile", group_id=self._group_id, profile_index=profile_index
            )
        elif preset_mode == PRESET_NONE:
            current_preset = self.preset_mode
            if current_preset == PRESET_BOOST:
                await self._async_set_group_property(
                    "async_set_group_boost", group_id=self._group_id, boost=False
                )
            elif current_preset == PRESET_ECO:
                await self._async_set_home_property("async_deactivate_absence")
            elif current_preset == PRESET_PARTY:
                await self._async_set_home_property("async_deactivate_vacation")
            else:
                await self._async_set_group_property(
                    "async_set_group_control_mode", group_id=self._group_id, mode="AUTOMATIC"
                )
            
            # Revert to the default automatic profile if available.
            if self._default_profile_index:
                 await self._async_set_group_property(
                    "async_set_group_active_profile", group_id=self._group_id, profile_index=self._default_profile_index
                )