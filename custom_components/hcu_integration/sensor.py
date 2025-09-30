# custom_components/hcu_integration/sensor.py
"""
Sensor platform for the Homematic IP HCU integration.

This platform creates sensor entities for various device features and for the home hub.
"""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_FEATURE_TO_ENTITY, HCU_DEVICE_TYPES
from .entity import HcuBaseEntity, HcuHomeBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = coordinator.client
    
    new_entities = []
    created_entity_ids = set()

    # Discover device-specific sensors
    for device_data in client.state.get("devices", {}).values():
        if device_data.get("PARENT"):
            continue
            
        oem = device_data.get("oem")
        if oem and oem != "eQ-3":
            option_key = f"import_{oem.lower().replace(' ', '_')}"
            if not config_entry.options.get(option_key, True):
                continue
        
        maintenance_channel = device_data.get("functionalChannels", {}).get("0", {})
        is_mains_powered = maintenance_channel.get("lowBat") is None

        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
                if feature in channel_data and mapping.get("class", "").endswith("Sensor"):
                    
                    if isinstance(channel_data.get(feature), bool):
                        continue

                    # Suppress signal strength sensor for the HCU itself.
                    if feature == "rssiDeviceValue" and device_data.get("type") in HCU_DEVICE_TYPES:
                        continue
                        
                    if feature == "batteryLevel" and is_mains_powered:
                        continue
                    
                    if feature in ("actualTemperature", "valveActualTemperature"):
                        unique_id = f"{device_data['id']}_{channel_index}_temperature"
                        entity_class = HcuTemperatureSensor
                    else:
                        unique_id = f"{device_data['id']}_{channel_index}_{feature}"
                        entity_class = HcuGenericSensor

                    if unique_id not in created_entity_ids:
                        new_entities.append(entity_class(client, device_data, channel_index, feature, mapping))
                        created_entity_ids.add(unique_id)

    # Discover home-level sensors
    home_data = client.state.get("home", {})
    if home_data:
        for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
            if feature in home_data and mapping.get("class") == "HcuHomeSensor":
                unique_id = f"{client.hcu_device_id}_{feature}"
                if unique_id not in created_entity_ids:
                    new_entities.append(HcuHomeSensor(client, feature, mapping))
                    created_entity_ids.add(unique_id)
    
    if new_entities:
        async_add_entities(new_entities)

class HcuHomeSensor(HcuHomeBaseEntity, SensorEntity):
    """Representation of a sensor tied to the HCU 'home' object."""

    def __init__(self, client: HcuApiClient, feature: str, mapping: dict):
        """Initialize the home sensor."""
        super().__init__(client)
        self._feature = feature

        self._attr_name = f"Homematic IP HCU {mapping['name']}"
        self._attr_unique_id = f"{self._hcu_device_id}_{self._feature}"
        self._attr_device_class = mapping.get("device_class")
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_state_class = mapping.get("state_class")
        self._attr_icon = mapping.get("icon")
        
        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping["entity_registry_enabled_default"]

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        value = self._home.get(self._feature)
        if value is None:
            return None
        
        if self._feature == "carrierSense":
            return round(value * 100.0, 1)

        return value

class HcuGenericSensor(HcuBaseEntity, SensorEntity):
    """Representation of a generic HCU sensor for a physical device."""

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str, feature: str, mapping: dict):
        """Initialize the sensor."""
        super().__init__(client, device_data, channel_index)
        self._feature = feature
        
        device_label = self._device.get("label", "Unknown Device")
        self._attr_name = f"{device_label} {mapping['name']}"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_{self._feature}"
        self._attr_device_class = mapping.get("device_class")
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_state_class = mapping.get("state_class")
        self._attr_icon = mapping.get("icon")
        
        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping["entity_registry_enabled_default"]

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor, applying transformations if necessary."""
        value = self._channel.get(self._feature)
        if value is None:
            return None
        
        if self._feature == "valvePosition":
            return round(value * 100.0, 1)
        if self._feature == "vaporAmount":
            return round(value, 2)
            
        return value

class HcuTemperatureSensor(HcuBaseEntity, SensorEntity):
    """A dedicated sensor for temperature to handle multiple temp features per channel."""

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str, feature: str, mapping: dict):
        """Initialize the temperature sensor."""
        super().__init__(client, device_data, channel_index)
        device_label = self._device.get("label", "Unknown Device")
        self._attr_name = f"{device_label} Temperature"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_temperature"
        
        self._attr_device_class = mapping.get("device_class")
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_state_class = mapping.get("state_class")

    @property
    def native_value(self) -> float | None:
        """
        Return the temperature value, prioritizing 'actualTemperature'.
        """
        return self._channel.get("actualTemperature") or self._channel.get("valveActualTemperature")