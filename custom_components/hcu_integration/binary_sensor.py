# custom_components/hcu_integration/binary_sensor.py
"""Binary sensor platform for the Homematic IP HCU integration."""
import asyncio
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_FEATURE_MAP
from .entity import HcuBaseEntity
from .api import HcuApiClient

# Maps specific functional channel types to the feature that represents their primary state.
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
    for device_data in devices.values():
        if not device_data.get("PARENT"):  # Process only main devices
            
            # Create stateless button sensors for SWITCH_INPUT devices.
            if device_data.get("type") == "SWITCH_INPUT":
                for channel_index in device_data.get("functionalChannels", {}):
                    if int(channel_index) > 0: # Skip the maintenance channel 0
                        new_entities.append(HcuButtonSensor(client, device_data, channel_index))
                continue # Move to the next device

            # Create stateful binary sensors for all other devices.
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                channel_type = channel_data.get("functionalChannelType")
                
                # Create entities based on the primary function of the channel.
                if feature := CHANNEL_TYPE_TO_FEATURE.get(channel_type):
                    if feature in channel_data:
                        mapping = HMIP_FEATURE_MAP[feature]
                        new_entities.append(HcuBinarySensor(client, device_data, channel_index, feature, mapping))

                # Create generic diagnostic entities (low battery, unreachable) from the maintenance channel.
                if channel_index == "0":
                    for feature in ("lowBat", "unreach"):
                        if feature in channel_data and channel_data.get(feature) is not None:
                            if mapping := HMIP_FEATURE_MAP.get(feature):
                                new_entities.append(HcuBinarySensor(client, device_data, channel_index, feature, mapping))
    
    if new_entities:
        async_add_entities(new_entities)

class HcuBinarySensor(HcuBaseEntity, BinarySensorEntity):
    """Representation of an HCU binary sensor with a persistent state (e.g., window open/closed)."""
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

class HcuButtonSensor(HcuBaseEntity, BinarySensorEntity):
    """
    Representation of a stateless button (SWITCH_INPUT).
    This sensor turns 'on' for a brief moment when a button press is detected
    by listening for any update event on its channel.
    """
    _attr_should_poll = False

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the button sensor."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = f"{self._device.get('label')} Button {self._channel_index}"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_button"
        self._is_on = False
        self._last_update_ts = self._channel.get("lastStatusUpdate")

    @property
    def is_on(self) -> bool:
        """Return the temporary state of the sensor."""
        return self._is_on

    @callback
    def _handle_update(self, updated_ids: set) -> None:
        """Handle a state update signal to detect a button press."""
        channel_address = f"{self._device_id}:{self._channel_index}"
        if channel_address in updated_ids:
            # A button press is often just a timestamp update.
            # If the timestamp changes, we fire the event.
            new_ts = self._channel.get("lastStatusUpdate")
            if new_ts and new_ts != self._last_update_ts:
                self._last_update_ts = new_ts
                self.hass.async_create_task(self._async_trigger())

    async def _async_trigger(self):
        """Handle the stateless button press event by turning on for 1 second."""
        self._is_on = True
        self.async_write_ha_state()
        await asyncio.sleep(1)
        self._is_on = False
        self.async_write_ha_state()