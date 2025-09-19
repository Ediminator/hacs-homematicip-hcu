# custom_components/hcu_integration/switch.py
"""Switch platform for the Homematic IP HCU integration."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_DEVICE_TO_DEVICE_CLASS
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    devices = data["initial_state"].get("devices", {})
    
    new_switches = []
    for device_data in devices.values():
        if not device_data.get("PARENT"):  # This is a main device
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                # Create standard switches
                if channel_data.get("functionalChannelType") == "SWITCH_CHANNEL":
                    new_switches.append(HcuSwitch(client, device_data, channel_index))
                # Create switches for the sound channels of the MP3P doorbell/siren
                elif channel_data.get("functionalChannelType") == "ACOUSTIC_SIGNAL_VIRTUAL_RECEIVER":
                    new_switches.append(HcuSoundSwitch(client, device_data, channel_index))

    if new_switches:
        async_add_entities(new_switches)

class HcuSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of a standard HCU Switch."""
    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the switch."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = self._device.get("label") or "Unknown Switch"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_switch"
        
        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TO_DEVICE_CLASS.get(device_type)

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._channel.get("on", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._client.async_set_switch_state(self._device_id, self._channel_index, True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._client.async_set_switch_state(self._device_id, self._channel_index, False)


class HcuSoundSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of an HCU sound switch (like on the MP3P)."""
    _attr_icon = "mdi:volume-high"

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the sound switch."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = f"{self._device.get('label')} Sound {self._channel_index}"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_sound_switch"

    @property
    def is_on(self) -> bool:
        """This entity is 'write-only' to trigger a sound, it doesn't have a persistent on-state."""
        return False

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on, which plays a sound."""
        await self._client.async_send_hmip_request(
            path="/hmip/device/control/setSoundFileVolumeLevelWithTime",
            body={
                "deviceId": self._device_id,
                "channelIndex": self._channel_index,
                "onTime": 5,  # Play sound for 5 seconds
                "soundFile": "SOUNDFILE_001",  # Example sound, can be configured later
                "volumeLevel": 1.0,
            },
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off (does nothing)."""
        pass