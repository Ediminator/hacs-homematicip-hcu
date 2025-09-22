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
        if device_data.get("PARENT"):
            continue

        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            for feature, mapping in HMIP_FEATURE_MAP.items():
                # Create entity only if it's a binary_sensor and the feature value is not null.
                if mapping.get("platform") == "binary_sensor" and channel_data.get(feature) is not None:
                    unique_id = f"{device_data['id']}_{channel_index}_{feature}"
                    if unique_id not in created_entity_ids:
                        new_entities.append(HcuBinarySensor(client, device_data, channel_index, feature, mapping))
                        created_entity_ids.add(unique_id)

        # Create stateless button sensors for SWITCH_INPUT devices.
        if device_data.get("type") == "SWITCH_INPUT":
            for channel_index in device_data.get("functionalChannels", {}):
                if int(channel_index) > 0:
                    unique_id = f"{device_data['id']}_{channel_index}_button"
                    if unique_id not in created_entity_ids:
                        new_entities.append(HcuButtonSensor(client, device_data, channel_index))
                        created_entity_ids.add(unique_id)

    if new_entities:
        async_add_entities(new_entities)

class HcuBinarySensor(HcuBaseEntity, BinarySensorEntity):
    """Representation of an HCU binary sensor with a persistent state."""
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
        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping["entity_registry_enabled_default"]

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        value = self._channel.get(self._feature)
        if value is None:
            return None
        
        if self._feature == "rotaryHandleState":
            return value in ("TILTED", "OPEN")
            
        is_on_state = (value == self._on_state)
        return not is_on_state if self._invert_state else is_on_state

class HcuButtonSensor(HcuBaseEntity, BinarySensorEntity):
    """Representation of a stateless button (e.g., a wall switch press)."""
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
        """Return the temporary state of the sensor. It's 'on' for a brief moment."""
        return self._is_on

    @callback
    def _handle_update(self, updated_ids: set) -> None:
        """Handle a state update signal to detect a button press."""
        channel_address = f"{self._device_id}:{self._channel_index}"
        if channel_address in updated_ids:
            new_ts = self._channel.get("lastStatusUpdate")
            if new_ts and new_ts != self._last_update_ts:
                self._last_update_ts = new_ts
                self.hass.async_create_task(self._async_trigger())

    async def _async_trigger(self):
        """Handle the stateless button press by turning the sensor on and then off."""
        self._is_on = True
        self.async_write_ha_state()
        await asyncio.sleep(1)
        self._is_on = False
        self.async_write_ha_state()