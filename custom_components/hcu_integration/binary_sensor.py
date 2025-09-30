# custom_components/hcu_integration/binary_sensor.py
"""
Binary sensor platform for the Homematic IP HCU integration.

This platform creates two types of binary sensors:
1. Stateful sensors like window/door contacts.
2. Stateless sensors that act as event triggers for devices like push-buttons.
"""
import asyncio
import logging
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_FEATURE_TO_ENTITY, HMIP_CHANNEL_TYPE_TO_ENTITY, SIGNAL_UPDATE_ENTITY
from .entity import HcuBaseEntity, HcuHomeBaseEntity
from .api import HcuApiClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the binary_sensor platform from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = coordinator.client
    
    new_entities = []
    created_entity_ids = set()

    # Discover device-specific binary sensors
    for device_data in client.state.get("devices", {}).values():
        if device_data.get("PARENT"):
            continue # Skip child devices as they are handled by their parent.
            
        oem = device_data.get("oem")
        if oem and oem != "eQ-3":
            # Check if importing devices from this third-party manufacturer is enabled.
            option_key = f"import_{oem.lower().replace(' ', '_')}"
            if not config_entry.options.get(option_key, True):
                continue

        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
                if feature in channel_data and mapping.get("class") == "HcuBinarySensor":
                    
                    if feature == "lowBat" and channel_data.get("lowBat") is None:
                        continue

                    unique_id = f"{device_data['id']}_{channel_index}_{feature}"
                    if unique_id not in created_entity_ids:
                        new_entities.append(HcuBinarySensor(client, device_data, channel_index, feature, mapping))
                        created_entity_ids.add(unique_id)
            
            channel_type = channel_data.get("functionalChannelType")
            if mapping := HMIP_CHANNEL_TYPE_TO_ENTITY.get(channel_type):
                if mapping.get("class") == "HcuButtonPressSensor":
                    unique_id = f"{device_data['id']}_{channel_index}_button_press"
                    if unique_id not in created_entity_ids:
                        new_entities.append(HcuButtonPressSensor(client, device_data, channel_index))
                        created_entity_ids.add(unique_id)

    # Discover home-level binary sensors (e.g., Vacation Mode)
    if client.state.get("home"):
        unique_id = f"{client.hcu_device_id}_vacation_mode"
        if unique_id not in created_entity_ids:
            new_entities.append(HcuHomeBinarySensor(client))
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
        
        device_label = self._device.get("label", "Unknown Device")
        self._attr_name = f"{device_label} {mapping.get('name')}"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_{self._feature}"
        self._attr_device_class = mapping.get("device_class")
        
        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping["entity_registry_enabled_default"]

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        value = self._channel.get(self._feature)
        if value is None:
            return None
        
        if self.device_class == BinarySensorDeviceClass.LOCK:
            return not value
            
        if self.device_class == BinarySensorDeviceClass.CONNECTIVITY:
            return not value

        if self._feature == "windowState":
            return value in ("OPEN", "TILTED")
            
        return value == self._on_state

class HcuButtonPressSensor(HcuBaseEntity, BinarySensorEntity):
    """
    Representation of a stateless button press.
    This entity acts as an event trigger by turning on momentarily when a press is detected.
    """

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the button press sensor."""
        super().__init__(client, device_data, channel_index)
        device_label = self._device.get("label", "Unknown Device")
        # Use the channel's label if it exists, otherwise create a generic name.
        channel_label = self._channel.get("label")
        if channel_label:
            self._attr_name = f"{device_label} {channel_label}"
        else:
            self._attr_name = f"{device_label} Button {self._channel_index}"
            
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_button_press"
        self._is_on = False
        self._last_update_ts = self._channel.get("lastStatusUpdate")

    @property
    def is_on(self) -> bool:
        """Return the temporary 'on' state of the sensor."""
        return self._is_on

    async def async_added_to_hass(self) -> None:
        """Register a custom listener for press updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPDATE_ENTITY, self._handle_press_update
            )
        )

    @callback
    def _handle_press_update(self, updated_ids: set) -> None:
        """
        Detect a button press by checking if the 'lastStatusUpdate' timestamp has changed.
        """
        if self._device_id not in updated_ids:
            return

        new_ts = self._channel.get("lastStatusUpdate")
        if new_ts and new_ts != self._last_update_ts:
            self._last_update_ts = new_ts
            self.hass.async_create_task(self._async_trigger_pulse())

    async def _async_trigger_pulse(self) -> None:
        """Turn the sensor on for a short period to act as an event trigger."""
        self._is_on = True
        self.async_write_ha_state()
        await asyncio.sleep(1)
        self._is_on = False
        self.async_write_ha_state()

class HcuHomeBinarySensor(HcuHomeBaseEntity, BinarySensorEntity):
    """Representation of a binary sensor tied to the HCU 'home' object."""

    def __init__(self, client: HcuApiClient):
        """Initialize the home binary sensor."""
        super().__init__(client)
        self._attr_name = "Vacation Mode"
        self._attr_unique_id = f"{self._hcu_device_id}_vacation_mode"
        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:palm-tree"

    @property
    def is_on(self) -> bool:
        """Return true if vacation mode is active."""
        heating_home = self._home.get("functionalHomes", {}).get("HEATING", {})
        return heating_home.get("vacationMode", False)