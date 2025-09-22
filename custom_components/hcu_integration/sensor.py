# custom_components/hcu_integration/sensor.py
"""Sensor platform for the Homematic IP HCU integration."""
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_FEATURE_MAP
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    devices = data["initial_state"].get("devices", {})
    
    new_entities = []
    created_entity_ids = set()

    for device_data in devices.values():
        if device_data.get("PARENT"):
            continue

        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            # Special handling for temperature to create one authoritative sensor.
            if "actualTemperature" in channel_data or "valveActualTemperature" in channel_data:
                unique_id = f"{device_data['id']}_{channel_index}_temperature"
                if unique_id not in created_entity_ids:
                    new_entities.append(HcuTemperatureSensor(client, device_data, channel_index))
                    created_entity_ids.add(unique_id)
            
            # Generic handling for all other sensor types.
            for feature, mapping in HMIP_FEATURE_MAP.items():
                # Create entity only if it's a sensor and the feature value is not null.
                if mapping.get("platform") == "sensor" and channel_data.get(feature) is not None:
                    if feature in ("actualTemperature", "valveActualTemperature"):
                        continue
                        
                    unique_id = f"{device_data['id']}_{channel_index}_{feature}"
                    if unique_id not in created_entity_ids:
                        if feature == "rssiDeviceValue" and device_data.get("type") == "HOME_CONTROL_ACCESS_POINT":
                            continue
                        new_entities.append(HcuGenericSensor(client, device_data, channel_index, feature, mapping))
                        created_entity_ids.add(unique_id)
    
    if new_entities:
        async_add_entities(new_entities)

class HcuGenericSensor(HcuBaseEntity, SensorEntity):
    """Representation of a generic HCU sensor."""
    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str, feature: str, mapping: dict):
        """Initialize the sensor."""
        super().__init__(client, device_data, channel_index)
        self._feature = feature
        device_label = self._device.get("label", "Unknown Device")
        self._attr_name = f"{device_label} {mapping.get('name')}"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_{feature}"
        self._attr_device_class = mapping.get("device_class")
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_state_class = mapping.get("state_class")
        self._attr_icon = mapping.get("icon")
        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping["entity_registry_enabled_default"]

    @property
    def native_value(self):
        """Return the state of the sensor."""
        value = self._channel.get(self._feature)
        if value is None:
            return None
        if self._feature == "valvePosition":
            return round(value * 100.0, 1)
        if self._feature == "vaporAmount":
            return round(value, 2)
        return value

class HcuTemperatureSensor(HcuBaseEntity, SensorEntity):
    """Representation of an HCU temperature sensor."""
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the temperature sensor."""
        super().__init__(client, device_data, channel_index)
        device_label = self._device.get("label", "Unknown Device")
        self._attr_name = f"{device_label} Temperature"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_temperature"

    @property
    def native_value(self) -> float | None:
        """Return the temperature, checking both possible keys."""
        return self._channel.get("actualTemperature") or self._channel.get("valveActualTemperature")