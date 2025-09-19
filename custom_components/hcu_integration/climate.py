# custom_components/hcu_integration/climate.py
"""Climate platform for the Homematic IP HCU integration."""
import logging
from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACMode
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HcuGroupBaseEntity
from .api import HcuApiClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    groups = data["initial_state"].get("groups", {})
    
    new_climates = []
    for group_data in groups.values():
        if group_data.get("type") == "HEATING":
            new_climates.append(HcuClimate(client, group_data))

    if new_climates:
        async_add_entities(new_climates)

class HcuClimate(HcuGroupBaseEntity, ClimateEntity):
    """Representation of an HCU Climate entity that sources its state from a group."""
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT]
    _attr_preset_modes = ["none", "boost"]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, client: HcuApiClient, group_data: dict):
        """Initialize the climate entity."""
        super().__init__(client, group_data)
        self._attr_name = self._group.get("label") or "Unknown Heating Group"
        self._attr_unique_id = self._group_id
        
        self._attr_min_temp = self._group.get("minTemperature", 5.0)
        self._attr_max_temp = self._group.get("maxTemperature", 30.0)
        self._attr_target_temperature_step = 0.5

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode from the group's state."""
        # This is now a direct and simple mapping from the HCU's state.
        if self._group.get("controlMode") == "AUTOMATIC":
            return HVACMode.AUTO
        return HVACMode.HEAT
        
    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if self._group.get("boostMode", False):
            return "boost"
        return "none"

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature reported by the group."""
        return self._group.get("actualTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._group.get("setPointTemperature")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set a new target temperature, which always implies switching to MANUAL mode."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        if self.preset_mode == "boost":
            await self._client.async_set_boost(self._group_id, False)
        
        await self._client.async_set_control_mode(self._group_id, "MANUAL")
        await self._client.async_set_setpoint_temperature(self._group_id, temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set a new HVAC mode."""
        if self.preset_mode == "boost":
            await self._client.async_set_boost(self._group_id, False)
        
        if hvac_mode == HVACMode.AUTO:
            await self._client.async_set_control_mode(self._group_id, "AUTOMATIC")
        elif hvac_mode == HVACMode.HEAT:
            await self._client.async_set_control_mode(self._group_id, "MANUAL")
            
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set a new preset mode."""
        if preset_mode == "boost":
            await self._client.async_set_boost(self._group_id, True)
        elif preset_mode == "none":
            await self._client.async_set_boost(self._group_id, False)