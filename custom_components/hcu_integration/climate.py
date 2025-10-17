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
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import HcuApiClient
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
        
        # Attributes for optimistic state
        self._attr_hvac_mode: HVACMode | None = None
        self._attr_target_temperature: float | None = None

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
        """
        Return the current humidity.
        Prefers the group's humidity, but falls back to the first available
        humidity sensor of a device within the group.
        """
        if (humidity := self._group.get("humidity")) is not None:
            return humidity

        for channel_ref in self._group.get("channels", []):
            device_id = channel_ref.get("deviceId")
            channel_index = str(channel_ref.get("channelIndex"))
            
            if device := self._client.get_device_by_address(device_id):
                if channel := device.get("functionalChannels", {}).get(channel_index):
                    if (humidity := channel.get("humidity")) is not None:
                        return humidity
        return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if self._attr_assumed_state and self._attr_hvac_mode:
            return self._attr_hvac_mode
            
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
        """
        Return the current temperature.
        Prefers the group's temperature, but falls back to the first available
        temperature sensor (wall or valve) of a device within the group.
        """
        if (temp := self._group.get("actualTemperature")) is not None:
            return temp

        for channel_ref in self._group.get("channels", []):
            device_id = channel_ref.get("deviceId")
            channel_index = str(channel_ref.get("channelIndex"))
            
            if device := self._client.get_device_by_address(device_id):
                if channel := device.get("functionalChannels", {}).get(channel_index):
                    if (temp := channel.get("actualTemperature")) is not None:
                        return temp
                    if (temp := channel.get("valveActualTemperature")) is not None:
                        return temp
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if self._attr_assumed_state and self._attr_target_temperature is not None:
            return self._attr_target_temperature

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

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        self._attr_assumed_state = True
        self._attr_hvac_mode = HVACMode.HEAT if temperature > self.min_temp else HVACMode.OFF
        self._attr_target_temperature = temperature
        self.async_write_ha_state()

        if self.hvac_mode == HVACMode.AUTO:
            await self._client.async_set_group_control_mode(
                self._group_id, "MANUAL"
            )

        await self._client.async_set_group_setpoint_temperature(
            self._group_id, temperature
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode with improved optimistic state handling."""
        self._attr_assumed_state = True
        self._attr_hvac_mode = hvac_mode

        if hvac_mode == HVACMode.OFF:
            self._attr_target_temperature = self.min_temp
            self.async_write_ha_state()
            await self._client.async_set_group_control_mode(self._group_id, "MANUAL")
            await self._client.async_set_group_setpoint_temperature(self._group_id, self.min_temp)

        elif hvac_mode == HVACMode.AUTO:
            self.async_write_ha_state()
            await self._client.async_set_group_control_mode(self._group_id, "AUTOMATIC")

        elif hvac_mode == HVACMode.HEAT:
            if self.target_temperature is not None and self.target_temperature <= self.min_temp:
                self._attr_target_temperature = self._config_entry.options.get(
                    CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
                )
            self.async_write_ha_state()
            
            await self._client.async_set_group_control_mode(self._group_id, "MANUAL")
            if self.target_temperature is not None and self.target_temperature <= self.min_temp:
                await self._client.async_set_group_setpoint_temperature(
                    self._group_id, self._attr_target_temperature
                )


    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        self._attr_assumed_state = True
        self.async_write_ha_state()

        if preset_mode == PRESET_BOOST:
            await self._client.async_set_group_boost(group_id=self._group_id, boost=True)
            
        elif preset_mode == PRESET_ECO:
            await self._client.async_activate_absence_permanent()
            
        elif preset_mode == PRESET_PARTY:
            comfort_temp = self._config_entry.options.get(CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE)
            end_time = dt_util.now() + timedelta(hours=4)
            await self.async_activate_party_mode(temperature=comfort_temp, end_time_str=end_time.strftime("%Y_%m_%d %H:%M"))

        elif preset_mode in self._profiles:
            await self._client.async_set_group_control_mode(group_id=self._group_id, mode="AUTOMATIC")
            profile_index = self._profiles[preset_mode]
            await self._client.async_set_group_active_profile(group_id=self._group_id, profile_index=profile_index)
            
        elif preset_mode == PRESET_NONE:
            current_preset = self.preset_mode
            if current_preset == PRESET_BOOST:
                await self._client.async_set_group_boost(group_id=self._group_id, boost=False)
            elif current_preset == PRESET_ECO:
                await self._client.async_deactivate_absence()
            elif current_preset == PRESET_PARTY:
                await self._client.async_deactivate_vacation()
            else:
                await self._client.async_set_group_control_mode(group_id=self._group_id, mode="AUTOMATIC")
            
            if self._default_profile_index:
                 await self._client.async_set_group_active_profile(group_id=self._group_id, profile_index=self._default_profile_index)
    
    async def async_activate_party_mode(
        self, temperature: float, end_time_str: str | None = None, duration: int | None = None
    ) -> None:
        """Service call to activate party mode."""
        if end_time_str is None and duration is None:
            raise ValueError("Either end_time or duration must be provided for party mode.")

        if end_time_str:
            end_time = end_time_str
        else:
            end_time_dt = dt_util.now() + timedelta(seconds=duration)
            end_time = end_time_dt.strftime("%Y_%m_%d %H:%M")
        
        self._attr_assumed_state = True
        self.async_write_ha_state()

        await self._client.async_activate_group_party_mode(
            group_id=self._group_id,
            temperature=temperature,
            end_time=end_time,
        )