import logging
from typing import TYPE_CHECKING

from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACMode
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
from .entity import HcuGroupBaseEntity
from .api import HcuApiClient, HcuApiError

if TYPE_CHECKING:
    from . import HcuCoordinator


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][config_entry.entry_id]
    if entities := coordinator.entities.get(Platform.CLIMATE):
        async_add_entities(entities)


class HcuClimate(HcuGroupBaseEntity, ClimateEntity):
    """
    Representation of an HCU Climate entity based on a Heating Group.
    
    Heating groups in Homematic IP can contain multiple thermostats and valves.
    This entity provides unified control over the entire group.
    """
    PLATFORM = Platform.CLIMATE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = ["boost", "none"]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | 
        ClimateEntityFeature.PRESET_MODE | 
        ClimateEntityFeature.TURN_OFF | 
        ClimateEntityFeature.TURN_ON
    )
    _enable_turn_on_off_backwards_compatibility = False
    _attr_has_entity_name = True # This entity is the primary feature of the device
    _attr_name = None # Name is inherited from the device (the group name)


    def __init__(self, coordinator: "HcuCoordinator", client: HcuApiClient, group_data: dict, config_entry: ConfigEntry):
        super().__init__(coordinator, client, group_data)
        self._config_entry = config_entry
        self._attr_unique_id = self._group_id

        self._attr_min_temp = self._group.get("minTemperature", 5.0)
        self._attr_max_temp = self._group.get("maxTemperature", 30.0)
        self._attr_target_temperature_step = self._group.get("temperatureStep", 0.5)

        # Optimistic state tracking (set when command sent, cleared when HCU confirms)
        self._attr_hvac_mode: HVACMode | None = None
        self._attr_target_temperature: float | None = None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._group_id in self.coordinator.data:
            # Clear optimistic state when real update received
            self._attr_hvac_mode = None
            self._attr_target_temperature = None
            self._attr_assumed_state = False
            self.async_write_ha_state()
        super()._handle_coordinator_update()


    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        # Use optimistic state if available
        if self._attr_hvac_mode is not None:
            return self._attr_hvac_mode

        control_mode = self._group.get("controlMode")
        
        # OFF = Manual mode with temperature set to minimum
        if (
            control_mode == "MANUAL"
            and self._group.get("setPointTemperature") == self._attr_min_temp
        ):
            return HVACMode.OFF
        
        # AUTO = Schedule-based temperature control
        if control_mode == "AUTOMATIC":
            return HVACMode.AUTO
        
        # HEAT = Manual temperature control
        return HVACMode.HEAT

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode (boost or none)."""
        return "boost" if self._group.get("boostMode") else "none"

    @property
    def current_temperature(self) -> float | None:
        """
        Return the current measured temperature.
        
        Tries group-level temperature first, then searches member devices.
        """
        # Prefer group-level temperature if available
        if (temp := self._group.get("actualTemperature")) is not None:
            return temp

        # Fall back to first available device temperature
        for channel_ref in self._group.get("channels", []):
            if device := self._client.get_device_by_address(channel_ref.get("deviceId")):
                channel_idx_str = str(channel_ref.get("channelIndex"))
                channel = device.get("functionalChannels", {}).get(channel_idx_str)
                
                if channel and (temp := (channel.get("actualTemperature") or channel.get("valveActualTemperature"))):
                    return temp

        return None
        
    @property
    def current_humidity(self) -> float | None:
        """
        Return the current humidity.
        
        Prioritizes group-level humidity first, then wall thermostats
        (most accurate placement) over other devices.
        """
        if (humidity := self._group.get("humidity")) is not None:
            return humidity

        wall_thermostat_channel = None
        any_thermostat_channel = None

        for channel_ref in self._group.get("channels", []):
            device = self._client.get_device_by_address(channel_ref.get("deviceId"))
            if not device:
                continue
            
            channel_idx_str = str(channel_ref.get("channelIndex"))
            channel = device.get("functionalChannels", {}).get(channel_idx_str)
            
            if not channel or "humidity" not in channel:
                continue
            
            # Prioritize wall-mounted thermostats for humidity readings
            if "WALL_MOUNTED_THERMOSTAT" in device.get("type", ""):
                wall_thermostat_channel = channel
                break  # Use this one immediately
            
            # Keep track of any device with humidity as fallback
            if any_thermostat_channel is None:
                any_thermostat_channel = channel
        
        target_channel = wall_thermostat_channel or any_thermostat_channel
        return target_channel.get("humidity") if target_channel else None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        # Use optimistic state if available
        if self._attr_target_temperature is not None:
            return self._attr_target_temperature
        return self._group.get("setPointTemperature")

    async def async_set_temperature(self, **kwargs) -> None:
        """
        Set target temperature.
        
        Automatically switches to manual mode and disables boost if active.
        """
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        is_in_auto_mode = self._group.get("controlMode") == "AUTOMATIC"

        # Set optimistic state immediately for UI responsiveness
        self._attr_target_temperature = temperature
        self._attr_hvac_mode = HVACMode.HEAT
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            # Disable boost if active
            if self.preset_mode == "boost":
                await self._client.async_set_group_boost(self._group_id, boost=False)

            # Switch from automatic to manual mode if needed
            if is_in_auto_mode:
                await self._client.async_set_group_control_mode(self._group_id, mode="MANUAL")

            # Set the target temperature
            await self._client.async_set_group_setpoint_temperature(self._group_id, temperature=temperature)
            
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set temperature for %s: %s", self.name, err)
            # Clear optimistic state on failure
            self._attr_target_temperature = None
            self._attr_hvac_mode = None
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """
        Set HVAC mode.
        
        - OFF: Sets temperature to minimum
        - AUTO: Enables schedule-based control
        - HEAT: Enables manual control with comfort temperature
        """
        # Set optimistic state immediately
        self._attr_hvac_mode = hvac_mode
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            # Disable boost if active
            if self.preset_mode == "boost":
                await self._client.async_set_group_boost(self._group_id, boost=False)

            if hvac_mode == HVACMode.OFF:
                # Turn off by setting temperature to minimum
                self._attr_target_temperature = self._attr_min_temp
                await self._client.async_set_group_setpoint_temperature(
                    self._group_id, 
                    temperature=self._attr_min_temp
                )
                
            elif hvac_mode == HVACMode.AUTO:
                # Enable automatic schedule-based control
                await self._client.async_set_group_control_mode(self._group_id, mode="AUTOMATIC")
                
            elif hvac_mode == HVACMode.HEAT:
                # Enable manual control
                await self._client.async_set_group_control_mode(self._group_id, mode="MANUAL")
                
                # If currently at minimum temp, set to comfort temperature
                if self.target_temperature == self._attr_min_temp:
                    comfort_temp = self._config_entry.options.get(
                        CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
                    )
                    self._attr_target_temperature = comfort_temp
                    self.async_write_ha_state()
                    await self._client.async_set_group_setpoint_temperature(
                        self._group_id, 
                        temperature=comfort_temp
                    )
                    
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set HVAC mode for %s: %s", self.name, err)
            # Clear optimistic state on failure
            self._attr_hvac_mode = None
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """
        Set preset mode.
        
        - boost: Temporarily heat at maximum for quick warmup
        - none: Normal operation
        """
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            is_boost = (preset_mode == "boost")
            await self._client.async_set_group_boost(self._group_id, boost=is_boost)
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set preset mode for %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()