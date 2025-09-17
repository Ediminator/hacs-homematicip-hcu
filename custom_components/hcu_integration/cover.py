# custom_components/hcu_integration/cover.py
"""Cover platform for the Homematic IP HCU integration."""
from homeassistant.components.cover import CoverEntity, CoverEntityFeature, CoverDeviceClass, ATTR_POSITION, ATTR_TILT_POSITION
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_DEVICE_PLATFORM_MAP, HMIP_DEVICE_TO_DEVICE_CLASS
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    coordinator = data["coordinator"]
    devices = coordinator.data.get("devices", {})
    
    new_covers = []
    for device_data in devices.values():
        if HMIP_DEVICE_PLATFORM_MAP.get(device_data.get("type")) == "cover":
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                if "shutterLevel" in channel_data:
                    new_covers.append(HcuCover(client, coordinator, device_data, channel_index))
    if new_covers: async_add_entities(new_covers)

class HcuCover(HcuBaseEntity, CoverEntity):
    """Representation of an HCU Cover."""
    def __init__(self, client, coordinator, device_data, channel_index):
        """Initialize the cover."""
        super().__init__(coordinator, device_data, channel_index)
        self._client = client
        self._attr_name = self._device.get("label") or "Unknown Cover"
        self._attr_unique_id = f"{self._device.get('id')}_{self._channel_index}_cover"
        # Set device class for correct icon
        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TO_DEVICE_CLASS.get(device_type)

        self._attr_supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
            CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION
        )
        if "slatsLevel" in self._channel:
            self._attr_supported_features |= (
                CoverEntityFeature.SET_TILT_POSITION | CoverEntityFeature.OPEN_TILT |
                CoverEntityFeature.CLOSE_TILT | CoverEntityFeature.STOP_TILT
            )

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover. 0 is open, 100 is closed."""
        level = self._updated_channel.get("shutterLevel")
        return int(level * 100) if level is not None else None

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return current position of cover tilt. 0 is open, 100 is closed."""
        if "slatsLevel" not in self._updated_channel:
            return None
        level = self._updated_channel.get("slatsLevel")
        return int(level * 100) if level is not None else None

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        pos = self.current_cover_position
        return pos == 100 if pos is not None else None

    async def async_open_cover(self, **kwargs) -> None:
        await self._client.async_set_shutter_level(self._device.get("id"), self._channel.get("index"), 0.0)

    async def async_close_cover(self, **kwargs) -> None:
        await self._client.async_set_shutter_level(self._device.get("id"), self._channel.get("index"), 1.0)

    async def async_stop_cover(self, **kwargs) -> None:
        await self._client.async_stop_cover(self._device.get("id"), self._channel.get("index"))

    async def async_set_cover_position(self, **kwargs) -> None:
        await self._client.async_set_shutter_level(self._device.get("id"), self._channel.get("index"), kwargs[ATTR_POSITION] / 100.0)

    async def async_set_cover_tilt_position(self, **kwargs) -> None:
        """Set new tilt position."""
        current_shutter_level = self.current_cover_position / 100.0 if self.current_cover_position is not None else 0.0
        new_slats_level = kwargs[ATTR_TILT_POSITION] / 100.0
        await self._client.async_set_slats_level(self._device.get("id"), self._channel.get("index"), shutter_level=current_shutter_level, slats_level=new_slats_level)