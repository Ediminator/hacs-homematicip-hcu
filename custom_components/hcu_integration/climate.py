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
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .api import HcuApiClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the climate platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    coordinator = data["coordinator"]
    groups = coordinator.data.get("groups", {})
    
    new_climates = []
    for group_data in groups.values():
        if group_data.get("type") == "HEATING":
            new_climates.append(HcuClimate(client, coordinator, group_data))

    if new_climates:
        async_add_entities(new_climates)

class HcuClimate(CoordinatorEntity, ClimateEntity):
    """Representation of an HCU Climate entity that sources its state from a group."""
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT, HVACMode.OFF]
    _attr_preset_modes = ["none", "boost"]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, client, coordinator, group_data):
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._client = client
        self._group_id = group_data.get("id")
        self._attr_name = group_data.get("label") or "Unknown Heating Group"
        self._attr_unique_id = self._group_id
        
        self._attr_min_temp = 5.0
        self._attr_max_temp = 30.0
        self._attr_target_temperature_step = 0.5

    @property
    def _updated_group(self) -> dict:
        """Helper to get the latest group data from the coordinator."""
        return self.coordinator.data.get("groups", {}).get(self._group_id, {})

    @property
    def hvac_mode(self) -> HVACMode:
        """Return the current HVAC mode from the group's state."""
        group_state = self._updated_group
        set_point = group_state.get("setPointTemperature", 0)

        # The 'Off' state is determined by a low setpoint while in MANUAL mode.
        if group_state.get("controlMode") == "MANUAL" and set_point <= self._attr_min_temp:
            return HVACMode.OFF
        if group_state.get("controlMode") == "AUTOMATIC":
            return HVACMode.AUTO
        if group_state.get("controlMode") == "MANUAL":
            return HVACMode.HEAT
        return HVACMode.OFF
        
    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode from the group's state."""
        if self._updated_group.get("boostMode", False):
            return "boost"
        return "none"

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature from the group's state."""
        return self._updated_group.get("actualTemperature")

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature from the group's state."""
        return self._updated_group.get("setPointTemperature")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature by sending a command to the group."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None: return

        if self.preset_mode == "boost":
            await self._client.async_set_boost(self._group_id, False)
        await self._client.async_set_control_mode(self._group_id, "MANUAL")
        await self._client.async_set_setpoint_temperature(self._group_id, temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode by sending a command to the group."""
        if self.preset_mode == "boost":
            await self._client.async_set_boost(self._group_id, False)
        
        if hvac_mode == HVACMode.AUTO:
            await self._client.async_set_control_mode(self._group_id, "AUTOMATIC")
        elif hvac_mode == HVACMode.HEAT:
            await self._client.async_set_control_mode(self._group_id, "MANUAL")
            if self.hvac_mode == HVACMode.OFF:
                await self._client.async_set_setpoint_temperature(self._group_id, 21.0)
        elif hvac_mode == HVACMode.OFF:
            await self._client.async_set_control_mode(self._group_id, "MANUAL")
            await self._client.async_set_setpoint_temperature(self._group_id, 4.5)
            
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        if preset_mode == "boost":
            await self._client.async_set_boost(self._group_id, True)
        elif preset_mode == "none":
            await self._client.async_set_boost(self._group_id, False)
            
    @property
    def device_info(self):
        """Return device information for this virtual group entity."""
        return {
            "identifiers": {(DOMAIN, self._group_id)},
            "name": self.name,
            "manufacturer": "Homematic IP",
            "model": "Heating Group",
            "via_device": (DOMAIN, self.coordinator.data.get("home", {}).get("id")),
        }

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return super().available and self._group_id in self.coordinator.data.get("groups", {})