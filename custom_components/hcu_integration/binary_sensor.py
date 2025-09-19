# custom_components/hcu_integration/binary_sensor.py
"""Binary sensor platform for the Homematic IP HCU integration."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_FEATURE_MAP
from .entity import HcuBaseEntity
from .api import HcuApiClient

# Map specific channel types to the feature they primarily represent
CHANNEL_TYPE_TO_FEATURE = {
    "MOTION_DETECTION_CHANNEL": "presenceDetected",
    "SHUTTER_CONTACT_CHANNEL": "windowState",
    "SMOKE_DETECTOR_CHANNEL": "smokeAlarm",
    "WATER_SENSOR_CHANNEL": "waterlevelDetected",
    "TILT_VIBRATION_SENSOR_CHANNEL": "presenceDetected", # Often used for vibration
}

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the binary_sensor platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    devices = data["initial_state"].get("devices", {})
    
    new_entities = []
    for device_data in devices.values():
        if not device_data.get("PARENT"):  # This is a main device
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                
                # 1. Create entities based on the primary function of the channel
                channel_type = channel_data.get("functionalChannelType")
                if feature := CHANNEL_TYPE_TO_FEATURE.get(channel_type):
                    if feature in channel_data:
                        mapping = HMIP_FEATURE_MAP[feature]
                        new_entities.append(HcuBinarySensor(client, device_data, channel_index, feature, mapping))

                # 2. Create generic diagnostic entities from the maintenance channel (channel 0)
                if channel_index == "0":
                    for feature in ("lowBat", "unreach"):
                        if feature in channel_data and channel_data.get(feature) is not None:
                            mapping = HMIP_FEATURE_MAP.get(feature, {})
                            # Ensure we don't add lowBat sensor for devices without batteries
                            if mapping:
                                new_entities.append(HcuBinarySensor(client, device_data, channel_index, feature, mapping))
    
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

        # Disable diagnostic sensors by default
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