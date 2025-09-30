# custom_components/hcu_integration/cover.py
"""
Cover platform for the Homematic IP HCU integration.

This platform creates cover entities for shutter and blind actuators.
"""
from homeassistant.components.cover import (
    ATTR_POSITION, ATTR_TILT_POSITION, CoverEntity, CoverEntityFeature
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_DEVICE_TYPE_TO_DEVICE_CLASS, HMIP_FEATURE_TO_ENTITY, API_PATHS
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = coordinator.client
    
    new_entities = []
    created_entity_ids = set()

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
            if "shutterLevel" in channel_data:
                mapping = HMIP_FEATURE_TO_ENTITY.get("shutterLevel", {})
                if mapping.get("class") == "HcuCover":
                    unique_id = f"{device_data['id']}_{channel_index}_cover"
                    if unique_id not in created_entity_ids:
                        new_entities.append(HcuCover(client, device_data, channel_index))
                        created_entity_ids.add(unique_id)

    if new_entities:
        async_add_entities(new_entities)

class HcuCover(HcuBaseEntity, CoverEntity):
    """Representation of an HCU Cover (shutter or blind)."""

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the cover entity."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = self._device.get("label") or "Unknown Cover"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_cover"
        
        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TYPE_TO_DEVICE_CLASS.get(device_type)

        # Base features for all covers.
        self._attr_supported_features = (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
            CoverEntityFeature.STOP | CoverEntityFeature.SET_POSITION
        )
        # Add tilt support only if the device has slats.
        if "slatsLevel" in self._channel:
            self._attr_supported_features |= CoverEntityFeature.SET_TILT_POSITION

    @property
    def current_cover_position(self) -> int | None:
        """
        Return current position of cover.
        Homematic IP API: 0.0 is open, 1.0 is closed.
        Home Assistant: 0 is closed, 100 is open.
        This property inverts and scales the value.
        """
        level = self._channel.get("shutterLevel")
        return int((1 - level) * 100) if level is not None else None

    @property
    def current_cover_tilt_position(self) -> int | None:
        """
        Return current position of cover tilt.
        Inverts and scales the value to match HA's standard (0=closed, 100=open).
        """
        if "slatsLevel" not in self._channel:
            return None
        level = self._channel.get("slatsLevel")
        return int((1 - level) * 100) if level is not None else None

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        position = self.current_cover_position
        return position == 0 if position is not None else None

    async def async_open_cover(self, **kwargs) -> None:
        """Open the cover by setting shutterLevel to 0.0."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_device_control(
            API_PATHS.SET_SHUTTER_LEVEL, self._device_id, self._channel_index, {"shutterLevel": 0.0}
        )

    async def async_close_cover(self, **kwargs) -> None:
        """Close the cover by setting shutterLevel to 1.0."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_device_control(
            API_PATHS.SET_SHUTTER_LEVEL, self._device_id, self._channel_index, {"shutterLevel": 1.0}
        )

    async def async_stop_cover(self, **kwargs) -> None:
        """Stop the cover's movement."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_device_control(
            API_PATHS.STOP_COVER, self._device_id, self._channel_index
        )

    async def async_set_cover_position(self, **kwargs) -> None:
        """Set a new cover position."""
        position = kwargs[ATTR_POSITION]
        self._attr_assumed_state = True
        self.async_write_ha_state()
        # Convert HA's 0-100 (open) to HCU's 0.0-1.0 (closed).
        shutter_level = round((100 - position) / 100.0, 2)
        await self._client.async_device_control(
            API_PATHS.SET_SHUTTER_LEVEL, self._device_id, self._channel_index, {"shutterLevel": shutter_level}
        )

    async def async_set_cover_tilt_position(self, **kwargs) -> None:
        """Set new tilt position for blinds."""
        position = kwargs[ATTR_TILT_POSITION]
        self._attr_assumed_state = True
        self.async_write_ha_state()
        # Convert HA's 0-100 (open) to HCU's 0.0-1.0 (closed).
        slats_level = round((100 - position) / 100.0, 2)
        await self._client.async_device_control(
            API_PATHS.SET_SLATS_LEVEL,
            self._device_id, self._channel_index, 
            {"slatsLevel": slats_level},
        )