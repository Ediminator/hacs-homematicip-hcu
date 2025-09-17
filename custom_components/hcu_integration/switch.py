# custom_components/hcu_integration/switch.py
"""Switch platform for the Homematic IP HCU integration."""
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_DEVICE_PLATFORM_MAP, HMIP_DEVICE_TO_DEVICE_CLASS
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    coordinator = data["coordinator"]
    devices = coordinator.data.get("devices", {})
    
    new_switches = []
    for device_data in devices.values():
        device_platforms = HMIP_DEVICE_PLATFORM_MAP.get(device_data.get("type"), [])
        if "switch" in device_platforms or device_platforms == "switch":
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                if "on" in channel_data and channel_data.get("functionalChannelType") == "SWITCH_CHANNEL":
                    new_switches.append(HcuSwitch(client, coordinator, device_data, channel_index))
    if new_switches: async_add_entities(new_switches)

class HcuSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of an HCU Switch."""
    def __init__(self, client, coordinator, device_data, channel_index):
        """Initialize the switch."""
        super().__init__(coordinator, device_data, channel_index)
        self._client = client
        self._attr_name = self._device.get("label") or "Unknown Switch"
        self._attr_unique_id = f"{self._device.get('id')}_{self._channel_index}_switch"
        # Set device class for correct icon
        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TO_DEVICE_CLASS.get(device_type)

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._updated_channel.get("on", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._client.async_set_switch_state(self._device.get("id"), self._channel.get("index"), True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._client.async_set_switch_state(self._device.get("id"), self._channel.get("index"), False)