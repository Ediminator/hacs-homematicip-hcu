# custom_components/hcu_integration/climate.py
"""
Climate platform for the Homematic IP HCU integration.

This platform creates climate entities for Homematic IP heating groups.
"""
import logging
from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACMode
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE, API_PATHS
from .entity import HcuGroupBaseEntity
from .api import HcuApiClient, HcuApiError

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate platform from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = coordinator.client
    
    new_entities = [
        HcuClimate(client, group_data, config_entry)
        for group_data in client.state.get("groups", {}).values()
        if group_data.get("type") == "HEATING"
    ]

    if new_entities:
        async_add_entities(new_entities)

class HcuClimate(HcuGroupBaseEntity, ClimateEntity):
    """Representation of an HCU Climate entity based on a Heating Group."""
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = ["boost", "none"]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, client: HcuApiClient, group_data: dict, config_entry: ConfigEntry):
        """Initialize the climate entity."""
        super().__init__(client, group_data)
        self._config_entry = config_entry
        self._attr_name = self._group.get("label") or "Unknown Heating Group"
        self._attr_unique_id = self._group_id
        
        self._attr_min_temp = self._group.get("minTemperature", 5.0)
        self._attr_max_temp = self._group.get("maxTemperature", 30.0)
        self._attr_target_temperature_step = self._group.get("temperatureStep", 0.5)

        self._attr_hvac_mode: HVACMode | None = None
        self._attr_target_temperature: float | None = None

    @callback
    def _handle_update(self, updated_ids: set) -> None:
        """Handle a state update signal from the coordinator."""
        if self._group_id in updated_ids:
            self._attr_hvac_mode = None
            self._attr_target_temperature = None
            self._attr_assumed_state = False
            self.async_write_ha_state()

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode."""
        if self._attr_hvac_mode is not None:
            return self._attr_hvac_mode
        
        control_mode = self._group.get("controlMode")
        if (
            control_mode == "MANUAL" 
            and self._group.get("setPointTemperature") == self._attr_min_temp
        ):
            return HVACMode.OFF
        if control_mode == "AUTOMATIC":
            return HVACMode.AUTO
        return HVACMode.HEAT
        
    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return "boost" if self._group.get("boostMode") else "none"

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature for the group."""
        if (temp := self._group.get("actualTemperature")) is not None:
            return temp

        for channel_ref in self._group.get("channels", []):
            if device := self._client.get_device_by_address(channel_ref.get("deviceId")):
                channel_idx_str = str(channel_ref.get("channelIndex"))
                channel = device.get("functionalChannels", {}).get(channel_idx_str)
                if channel and (temp := (channel.get("actualTemperature") or channel.get("valveActualTemperature"))):
                    return temp
        
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if self._attr_target_temperature is not None:
            return self._attr_target_temperature
        return self._group.get("setPointTemperature")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set a new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        # Check the real mode from the cached state before applying optimistic updates.
        is_in_auto_mode = self._group.get("controlMode") == "AUTOMATIC"

        # Optimistically set the state for a responsive UI.
        self._attr_target_temperature = temperature
        self._attr_hvac_mode = HVACMode.HEAT
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            if self.preset_mode == "boost":
                await self._client.async_group_control(API_PATHS.SET_GROUP_BOOST, self._group_id, {"boost": False})
            
            # If in AUTO mode, we must explicitly switch to MANUAL to override the schedule.
            if is_in_auto_mode:
                 await self._client.async_group_control(
                    API_PATHS.SET_GROUP_CONTROL_MODE, self._group_id, {"controlMode": "MANUAL"}
                )

            await self._client.async_group_control(
                API_PATHS.SET_GROUP_SET_POINT_TEMP, self._group_id, {"setPointTemperature": temperature}
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set temperature for %s: %s", self.name, err)
            # Revert optimistic state on failure.
            self._attr_target_temperature = None
            self._attr_hvac_mode = None
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set a new HVAC mode."""
        self._attr_hvac_mode = hvac_mode
        self._attr_assumed_state = True
        self.async_write_ha_state()
        
        try:
            if self.preset_mode == "boost":
                await self._client.async_group_control(API_PATHS.SET_GROUP_BOOST, self._group_id, {"boost": False})
            
            if hvac_mode == HVACMode.OFF:
                self._attr_target_temperature = self._attr_min_temp
                await self._client.async_group_control(
                    API_PATHS.SET_GROUP_SET_POINT_TEMP, self._group_id, {"setPointTemperature": self._attr_min_temp}
                )
            elif hvac_mode == HVACMode.AUTO:
                await self._client.async_group_control(
                    API_PATHS.SET_GROUP_CONTROL_MODE, self._group_id, {"controlMode": "AUTOMATIC"}
                )
            elif hvac_mode == HVACMode.HEAT:
                await self._client.async_group_control(
                    API_PATHS.SET_GROUP_CONTROL_MODE, self._group_id, {"controlMode": "MANUAL"}
                )
                if self.target_temperature == self._attr_min_temp:
                    comfort_temp = self._config_entry.options.get(
                        CONF_COMFORT_TEMPERATURE, DEFAULT_COMFORT_TEMPERATURE
                    )
                    self._attr_target_temperature = comfort_temp
                    self.async_write_ha_state()
                    await self._client.async_group_control(
                        API_PATHS.SET_GROUP_SET_POINT_TEMP, self._group_id, {"setPointTemperature": comfort_temp}
                    )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set HVAC mode for %s: %s", self.name, err)
            self._attr_hvac_mode = None
            self._attr_assumed_state = False
            self.async_write_ha_state()
            
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set a new preset mode (e.g., boost)."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        
        try:
            is_boost = (preset_mode == "boost")
            await self._client.async_group_control(
                API_PATHS.SET_GROUP_BOOST, self._group_id, {"boost": is_boost}
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set preset mode for %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()