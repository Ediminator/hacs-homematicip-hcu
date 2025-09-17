# custom_components/hcu_integration/binary_sensor.py
"""Binary sensor platform for the Homematic IP HCU integration."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_FEATURE_MAP
from .entity import HcuBaseEntity

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the binary_sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    devices = coordinator.data.get("devices", {})
    
    new_entities = []
    for device_data in devices.values():
        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            for feature, mapping in HMIP_FEATURE_MAP.items():
                if mapping.get("platform") == "binary_sensor" and feature in channel_data:
                    # Only create a lowBat sensor if the value is not None.
                    if feature == "lowBat" and channel_data.get(feature) is None:
                        continue
                    
                    new_entities.append(HcuBinarySensor(coordinator, device_data, channel_index, feature, mapping))
    
    if new_entities: async_add_entities(new_entities)

class HcuBinarySensor(HcuBaseEntity, BinarySensorEntity):
    """Representation of an HCU binary sensor."""
    def __init__(self, coordinator, device_data, channel_index, feature, mapping):
        """Initialize the binary sensor."""
        super().__init__(coordinator, device_data, channel_index)
        self._feature = feature
        self._on_state = mapping.get("on_state", True)
        self._invert_state = mapping.get("invert_state", False)
        device_label = self._device.get("label", "Unknown Device")
        self._attr_name = f"{device_label} {mapping.get('name')}"
        self._attr_unique_id = f"{self._device.get('id')}_{self._channel_index}_{feature}"
        self._attr_device_class = mapping.get("device_class")

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        value = self._updated_channel.get(self._feature)
        if value is None:
            return None
            
        is_on_state = (value == self._on_state)
        return not is_on_state if self._invert_state else is_on_state