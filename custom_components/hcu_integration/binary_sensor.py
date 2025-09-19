# custom_components/hcu_integration/binary_sensor.py
"""Binary sensor platform for the Homematic IP HCU integration."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_FEATURE_MAP
from .entity import HcuBaseEntity
from .api import HcuApiClient

# Map specific functional channel types to the feature that represents their primary state.
# This is the primary, most reliable way to identify an entity's purpose.
CHANNEL_TYPE_TO_FEATURE = {
    "MOTION_DETECTION_CHANNEL": "presenceDetected",
    "SHUTTER_CONTACT_CHANNEL": "windowState",
    "SMOKE_DETECTOR_CHANNEL": "smokeAlarm",
    "WATER_SENSOR_CHANNEL": "waterlevelDetected",
    "TILT_VIBRATION_SENSOR_CHANNEL": "presenceDetected",
}

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the binary_sensor platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    devices = data["initial_state"].get("devices", {})
    
    new_entities = []
    created_entity_ids = set()

    for device_data in devices.values():
        if not device_data.get("PARENT"):  # Process only main devices
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                
                # --- NEW ROBUST DISCOVERY LOGIC ---
                
                # 1. First, try to identify the entity by its specific functionalChannelType.
                channel_type = channel_data.get("functionalChannelType")
                primary_feature = CHANNEL_TYPE_TO_FEATURE.get(channel_type)
                
                if primary_feature and primary_feature in channel_data:
                    unique_id = f"{device_data['id']}_{channel_index}_{primary_feature}"
                    if unique_id not in created_entity_ids:
                        mapping = HMIP_FEATURE_MAP[primary_feature]
                        new_entities.append(HcuBinarySensor(client, device_data, channel_index, primary_feature, mapping))
                        created_entity_ids.add(unique_id)

                # 2. Second, create generic diagnostic sensors from the maintenance channel.
                if channel_index == "0":
                    for feature in ("lowBat", "unreach"):
                        if feature in channel_data and channel_data.get(feature) is not None:
                            unique_id = f"{device_data['id']}_{channel_index}_{feature}"
                            if unique_id not in created_entity_ids:
                                if mapping := HMIP_FEATURE_MAP.get(feature):
                                    new_entities.append(HcuBinarySensor(client, device_data, channel_index, feature, mapping))
                                    created_entity_ids.add(unique_id)

    if new_entities:
        async_add_entities(new_entities)

class HcuBinarySensor(HcuBaseEntity, BinarySensorEntity):
    """Representation of an HCU binary sensor."""
    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str, feature: str, mapping: dict):
        """Initialize the binary sensor."""
        super().__init__(client, device_data, channel_index)
        self._feature = feature
        self._on_state = mapping.get("on_state", True)
        self._invert_state = mapping.get("invert_state", False)
        
        device_label = self._device.get("label", "Unknown Device")
        self._attr_name = f"{device_label} {mapping.get('name')}"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_{feature}"
        self._attr_device_class = mapping.get("device_class")

        # Diagnostic sensors are useful for automations but can clutter the UI, so they are disabled by default.
        if self._feature in ("lowBat", "unreach"):
            self._attr_entity_registry_enabled_default = False

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        value = self._channel.get(self._feature)
        if value is None:
            return None
            
        is_on_state = (value == self._on_state)
        return not is_on_state if self._invert_state else is_on_state