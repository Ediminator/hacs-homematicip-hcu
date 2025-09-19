# custom_components/hcu_integration/cover.py
"""Cover platform for the Homematic IP HCU integration."""
from homeassistant.components.cover import (
    ATTR_POSITION, ATTR_TILT_POSITION, CoverDeviceClass, CoverEntity, CoverEntityFeature
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    devices = data["initial_state"].get("devices", {})
    
    new_covers = []
    for device_data in devices.values():
        if not device_data.get("PARENT"):
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                if channel_data.get("functionalChannelType") in ("SHUTTER_CHANNEL", "BLIND_CHANNEL"):
                    new_covers.append(HcuCover(client, device_data, channel_index))
    if new_covers:
        async_add_entities(new_covers)

class HcuCover(HcuBaseEntity, CoverEntity):
    """Representation of an HCU Cover (shutter or blind)."""
    _attr_device_class = CoverDeviceClass.SHUTTER

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the cover."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = self._device.get("label") or "Unknown Cover"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_cover"

        # Base features for all covers
        self._attr_supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
            CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION
        )
        # Add tilt support only if the device has a 'slatsLevel' feature (i.e., it's a blind)
        if "slatsLevel" in self._channel:
            self._attr_supported_features |= CoverEntityFeature.SET_TILT_POSITION

    @property
    def current_cover_position(self) -> int | None:
        """
        Return current position of cover.
        Homematic: 0.0 is open, 1.0 is closed.
        Home Assistant: 0 is closed, 100 is open.
        We invert the value to match HA's standard.
        """
        level = self._channel.get("shutterLevel")
        return int((1 - level) * 100) if level is not None else None

    @property
    def current_cover_tilt_position(self) -> int | None:
        """
        Return current position of cover tilt.
        Inverts the value to match HA's standard (0=closed, 100=open).
        """
        if "slatsLevel" not in self._channel:
            return None
        level = self._channel.get("slatsLevel")
        return int((1 - level) * 100) if level is not None else None

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        pos = self.current_cover_position
        return pos == 0 if pos is not None else None

    async def async_open_cover(self, **kwargs) -> None:
        """Open the cover by setting shutterLevel to 0.0."""
        await self._client.async_set_shutter_level(self._device_id, self._channel_index, 0.0)

    async def async_close_cover(self, **kwargs) -> None:
        """Close the cover by setting shutterLevel to 1.0."""
        await self._client.async_set_shutter_level(self._device_id, self._channel_index, 1.0)

    async def async_stop_cover(self, **kwargs) -> None:
        """Stop the cover's movement."""
        await self._client.async_stop_cover(self._device_id, self._channel_index)

    async def async_set_cover_position(self, **kwargs) -> None:
        """Set a new cover position."""
        position = kwargs[ATTR_POSITION]
        # Invert from HA's percentage to HCU's level
        await self._client.async_set_shutter_level(self._device_id, self._channel_index, (100 - position) / 100.0)

    async def async_set_cover_tilt_position(self, **kwargs) -> None:
        """Set new tilt position."""
        position = kwargs[ATTR_TILT_POSITION]
        # Invert from HA's percentage to HCU's level
        await self._client.async_set_slats_level(self._device_id, self._channel_index, (100 - position) / 100.0)