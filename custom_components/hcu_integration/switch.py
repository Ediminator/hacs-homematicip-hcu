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
        if not device_data.get("PARENT"):
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                channel_type = channel_data.get("functionalChannelType")
                
                if channel_type == "SWITCH_CHANNEL":
                    new_switches.append(HcuSwitch(client, device_data, channel_index))
                elif channel_type == "ACOUSTIC_SIGNAL_VIRTUAL_RECEIVER":
                    new_switches.append(HcuSoundSwitch(client, device_data, channel_index))
                elif channel_type == "WATERING_SYSTEM_CHANNEL":
                    new_switches.append(HcuWateringSwitch(client, device_data, channel_index))

    if new_switches:
        async_add_entities(new_switches)

class HcuSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of a standard Homematic IP HCU switch."""
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
    """
    Representation of an HCU sound switch (e.g., for an MP3 doorbell).
    This switch is "write-only"; turning it on plays a sound, but it immediately
    returns to an 'off' state in Home Assistant.
    """
    _attr_icon = "mdi:volume-high"

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the sound switch."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = f"{self._device.get('label')} Sound {self._channel_index}"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_sound_switch"

    @property
    def is_on(self) -> bool:
        """This entity is stateless and will always appear as 'off'."""
        return False

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on, which triggers the sound to play for a fixed duration."""
        await self._client.async_send_hmip_request(
            path="/hmip/device/control/setSoundFileVolumeLevelWithTime",
            body={
                "deviceId": self._device_id,
                "channelIndex": self._channel_index,
                "onTime": 5,
                "soundFile": "SOUNDFILE_001",
                "volumeLevel": 1.0,
            },
        )

    async def async_turn_off(self, **kwargs) -> None:
        """This action does nothing as the sound plays for a fixed duration."""
        pass

class HcuWateringSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of a Homematic IP HCU watering controller."""
    _attr_icon = "mdi:water"

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the watering switch."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = self._device.get("label") or "Watering"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_watering_switch"

    @property
    def is_on(self) -> bool:
        """Return true if the watering is active."""
        return self._channel.get("wateringActive", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the watering on."""
        await self._client.async_send_hmip_request(
            path="/hmip/device/control/setWateringSwitchState",
            body={ "deviceId": self._device_id, "channelIndex": self._channel_index, "wateringActive": True, },
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the watering off."""
        await self._client.async_send_hmip_request(
            path="/hmip/device/control/setWateringSwitchState",
            body={ "deviceId": self._device_id, "channelIndex": self._channel_index, "wateringActive": False, },
        )