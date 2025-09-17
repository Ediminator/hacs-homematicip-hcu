# custom_components/hcu_integration/sensor.py
"""Sensor platform for the Homematic IP HCU integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_FEATURE_MAP
from .entity import HcuBaseEntity

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    devices = coordinator.data.get("devices", {})
    
    new_entities = []
    for device_data in devices.values():
        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            for feature, mapping in HMIP_FEATURE_MAP.items():
                if mapping.get("platform") == "sensor" and feature in channel_data:
                    # Exclude the RSSI sensor for the HCU itself.
                    if feature == "rssiDeviceValue" and device_data.get("type") == "ACCESS_POINT":
                        continue
                        
                    new_entities.append(HcuSensor(coordinator, device_data, channel_index, feature, mapping))
    
    if new_entities: async_add_entities(new_entities)

class HcuSensor(HcuBaseEntity, SensorEntity):
    """Representation of an HCU sensor."""
    def __init__(self, coordinator, device_data, channel_index, feature, mapping):
        """Initialize the sensor."""
        super().__init__(coordinator, device_data, channel_index)
        self._feature = feature
        device_label = self._device.get("label", "Unknown Device")
        self._attr_name = f"{device_label} {mapping.get('name')}"
        self._attr_unique_id = f"{self._device.get('id')}_{self._channel_index}_{feature}"
        self._attr_device_class = mapping.get("device_class")
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_state_class = mapping.get("state_class")
        self._attr_icon = mapping.get("icon")

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self._updated_channel.get(self._feature)
        
        if value is None:
            return None

        if self._feature == "valvePosition":
            return round(value * 100.0, 1)
            
        return value