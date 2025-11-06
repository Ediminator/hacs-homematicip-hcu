# custom_components/hcu_integration/climate.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from datetime import timedelta

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    PRESET_BOOST,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import HcuApiClient, HcuApiError
from .const import (
    CONF_COMFORT_TEMPERATURE,
    DEFAULT_COMFORT_TEMPERATURE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
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
    _attr_has_entity_name = False
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        group_data: dict,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the HCU Climate entity."""
        super().__init__(coordinator, client, group_data)
        self._attr_name = self._group.get("label")
        self._attr_unique_id = self._group_id
        self._config_entry = config_entry
        self._default_profile_name = "Standard"
        self._default_profile_index = "PROFILE_1"

        self._profiles: dict[str, str] = {}
        for profile in self._group.get("profiles", {}).values():
            if profile.get("enabled") and profile.get("visible"):
                profile_index = profile["index"]
                profile_name = profile.get("name")

                if profile_index == "PROFILE_1":
                    # Always include PROFILE_1, name it 'Standard' if unnamed
                    self._default_profile_name = profile_name or "Standard"
                    self._profiles[self._default_profile_name] = profile_index
                elif profile_name:  # Only include other profiles if they have a name
                    self._profiles[profile_name] = profile_index

        self._attr_preset_modes = [
            PRESET_BOOST,
            PRESET_ECO,
            PRESET_PARTY,
            *self._profiles.keys(),
        ]

        self._update_attributes_from_group_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attributes_from_group_data()
        super()._handle_coordinator_update()

    def _update_attributes_from_group_data(self) -> None:
        """Update all HA state attributes from the latest group data."""
        # Update temperature limits from group data with fallback to HCU defaults
        self._attr_min_temp = self._group.get("minTemperature", DEFAULT_MIN_TEMP)
        self._attr_max_temp = self._group.get("maxTemperature", DEFAULT_MAX_TEMP)

        control_mode = self._group.get("controlMode")
        target_temp = self._group.get("setPointTemperature")

        # Prevent state flapping during optimistic updates
        if (
            self._attr_assumed_state
            and self._attr_hvac_mode == HVACMode.OFF
            and control_mode == "MANUAL"
            and target_temp is not None
            and target_temp > self.min_temp
        ):
            return

        # Determine HVAC mode
        if not self._group.get("controllable", True):
            self._attr_hvac_mode = HVACMode.OFF
        else:
            if control_mode == "MANUAL":
                self._attr_hvac_mode = (
                    HVACMode.OFF
                    if target_temp is not None and target_temp <= self.min_temp
                    else HVACMode.HEAT
                )
            elif control_mode in ("AUTOMATIC", "ECO"):
                self._attr_hvac_mode = HVACMode.AUTO
            else:
                self._attr_hvac_mode = HVACMode.OFF

        # Determine Target Temperature
        heating_home = (
            self._client.state.get("home", {})
            .get("functionalHomes", {})
            .get("HEATING", {})
        )
        if heating_home.get("absenceType") == "PERMANENT":
            self._attr_target_temperature = heating_home.get("ecoTemperature")
        else:
            self._attr_target_temperature = self._group.get("setPointTemperature")

        # Determine Preset Mode
        if self._group.get("boostMode"):
            self._attr_preset_mode = PRESET_BOOST
        elif heating_home.get("absenceType") == "PERMANENT":
            self._attr_preset_mode = PRESET_ECO
        elif self._group.get("partyMode") == "ACTIVE":
            self._attr_preset_mode = PRESET_PARTY
        else:
            active_profile_index = self._group.get("activeProfile")
            self._attr_preset_mode = self._default_profile_name
            for name, index in self._profiles.items():
                if index == active_profile_index:
                    self._attr_preset_mode = name
                    break

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        if (humidity := self._group.get("humidity")) is not None:
            return humidity

        # Fallback: Find humidity from a device in the group
        for channel_ref in self._group.get("channels", []):
            device_id, channel_index = channel_ref.get("deviceId"), str(
                channel_ref.get("channelIndex")
            )
            if device := self._client.get_device_by_address(device_id):
                if channel := device.get("functionalChannels", {}).get(channel_index):
                    if (humidity := channel.get("humidity")) is not None:
                        return humidity
        return None

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        if (temp := self._group.get("actualTemperature")) is not None:
            return temp

        # Fallback: Find temperature from a device in the group
        for channel_ref in self._group.get("channels", []):
            device_id, channel_index = channel_ref.get("deviceId"), str(
                channel_ref.get("channelIndex")
            )
            if device := self._client.get_device_by_address(device_id):
                if channel := device.get("functionalChannels", {}).get(channel_index):
                    if (
                        temp := channel.get("actualTemperature")
                        or channel.get("valveActualTemperature")
                    ) is not None:
                        return temp
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._attr_assumed_state = True
        self._attr_target_temperature = temperature
        self._attr_hvac_mode = (
            HVACMode.HEAT if temperature > self.min_temp else HVACMode.OFF
        )
        self.async_write_ha_state()

        if self._group.get("controlMode") != "MANUAL":
            await self._client.async_set_group_control_mode(self._group_id, "MANUAL")

        await self._client.async_set_group_setpoint_temperature(
            self._group_id, temperature
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        self._attr_assumed_state = True
        self._attr_hvac_mode = hvac_mode

        if hvac_mode == HVACMode.OFF:
            self._attr_target_temperature = self.min_temp
            self.async_write_ha_state()
            if self._group.get("controlMode") != "MANUAL":
                await self._client.async_set_group_control_mode(self._group_id, "MANUAL")
            if self._group.get("setPointTemperature") != self.min_temp:
                await self._client.async_set_group_setpoint_temperature(
                    self._group_id, self.min_temp
                )

        elif hvac_mode == HVACMode.AUTO:
            self.async_write_ha_state()
            if self._group.get("controlMode") != "AUTOMATIC":
                await self._client.async_set_group_control_mode(
                    self._group_id, "AUTOMATIC"
                )

        elif hvac_mode == HVACMode.HEAT:
            comfort_temp = self._config_entry.options.get(
                CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
            )
            self._attr_target_temperature = comfort_temp
            self.async_write_ha_state()

            if self._group.get("controlMode") != "MANUAL":
                await self._client.async_set_group_control_mode(self._group_id, "MANUAL")

            await self._client.async_set_group_setpoint_temperature(
                self._group_id, comfort_temp
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        current_preset = self.preset_mode
        self._attr_assumed_state = True
        self._attr_preset_mode = preset_mode
        self.async_write_ha_state()

        try:
            if preset_mode == PRESET_BOOST:
                await self._client.async_set_group_boost(
                    group_id=self._group_id, boost=True
                )
            elif preset_mode == PRESET_ECO:
                await self._client.async_activate_absence_permanent()
            elif preset_mode == PRESET_PARTY:
                comfort_temp = self._config_entry.options.get(
                    CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
                )
                end_time = dt_util.now() + timedelta(hours=4)
                await self.async_activate_party_mode(
                    temperature=comfort_temp,
                    end_time_str=end_time.strftime("%Y_%m_%d %H:%M"),
                )

            elif preset_mode in self._profiles:
                if current_preset == PRESET_BOOST:
                    await self._client.async_set_group_boost(
                        group_id=self._group_id, boost=False
                    )
                elif current_preset == PRESET_ECO:
                    await self._client.async_deactivate_absence()
                elif current_preset == PRESET_PARTY:
                    await self._client.async_deactivate_vacation()

                if self._group.get("controlMode") != "AUTOMATIC":
                    await self._client.async_set_group_control_mode(
                        group_id=self._group_id, mode="AUTOMATIC"
                    )

                await self._client.async_set_group_active_profile(
                    group_id=self._group_id, profile_index=self._profiles[preset_mode]
                )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set preset mode: %s", err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_activate_party_mode(
        self,
        temperature: float,
        end_time_str: str | None = None,
        duration: int | None = None,
    ) -> None:
        """Service call to activate party mode."""
        if not end_time_str and not duration:
            raise ValueError(
                "Either end_time or duration must be provided for party mode."
            )

        end_time = end_time_str or (
            dt_util.now() + timedelta(seconds=duration)
        ).strftime("%Y_%m_%d %H:%M")

        self._attr_assumed_state = True
        self._attr_preset_mode = PRESET_PARTY
        self.async_write_ha_state()

        try:
            await self._client.async_activate_group_party_mode(
                group_id=self._group_id,
                temperature=temperature,
                end_time=end_time,
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to activate party mode: %s", err)
            self._attr_assumed_state = False
            self.async_write_ha_state()