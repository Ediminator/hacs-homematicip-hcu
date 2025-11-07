# custom_components/hcu_integration/cover.py
from typing import TYPE_CHECKING, Any
from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import HMIP_DEVICE_TYPE_TO_DEVICE_CLASS, API_PATHS
from .entity import HcuBaseEntity, HcuGroupBaseEntity
from .api import HcuApiClient

if TYPE_CHECKING:
    from . import HcuCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.COVER):
        async_add_entities(entities)


class HcuCover(HcuBaseEntity, CoverEntity):
    """Representation of an HCU Cover (shutter or blind) device channel."""

    PLATFORM = Platform.COVER

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
        **kwargs: Any,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        # REFACTOR: Correctly call the centralized naming helper.
        self._set_entity_name(channel_label=self._channel.get("label"))

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_cover"

        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TYPE_TO_DEVICE_CLASS.get(device_type)

        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        if "slatsLevel" in self._channel:
            self._attr_supported_features |= CoverEntityFeature.SET_TILT_POSITION

    @property
    def current_cover_position(self) -> int | None:
        """
        Return current position of cover.
        Inverts and scales HCU's 0.0(open)-1.0(closed) to HA's 100(open)-0(closed).
        """
        level = self._channel.get("shutterLevel")
        return int((1 - level) * 100) if level is not None else None

    @property
    def current_cover_tilt_position(self) -> int | None:
        if "slatsLevel" not in self._channel:
            return None
        level = self._channel.get("slatsLevel")
        return int((1 - level) * 100) if level is not None else None

    @property
    def is_closed(self) -> bool | None:
        position = self.current_cover_position
        return position == 0 if position is not None else None

    async def async_open_cover(self, **kwargs) -> None:
        self._attr_assumed_state = True
        await self._client.async_set_shutter_level(
            self._device_id, self._channel_index, 0.0
        )

    async def async_close_cover(self, **kwargs) -> None:
        self._attr_assumed_state = True
        await self._client.async_set_shutter_level(
            self._device_id, self._channel_index, 1.0
        )

    async def async_stop_cover(self, **kwargs) -> None:
        self._attr_assumed_state = True
        await self._client.async_stop_cover(self._device_id, self._channel_index)

    async def async_set_cover_position(self, **kwargs) -> None:
        position = kwargs[ATTR_POSITION]
        self._attr_assumed_state = True
        shutter_level = round((100 - position) / 100.0, 2)
        await self._client.async_set_shutter_level(
            self._device_id, self._channel_index, shutter_level
        )

    async def async_set_cover_tilt_position(self, **kwargs) -> None:
        position = kwargs[ATTR_TILT_POSITION]
        self._attr_assumed_state = True
        slats_level = round((100 - position) / 100.0, 2)
        await self._client.async_set_slats_level(
            self._device_id, self._channel_index, slats_level
        )


class HcuGarageDoorCover(HcuBaseEntity, CoverEntity):
    """Representation of an HCU Garage Door Cover."""

    PLATFORM = Platform.COVER

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
        **kwargs,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        # REFACTOR: Correctly call the centralized naming helper.
        self._set_entity_name(channel_label=self._channel.get("label"))

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_cover"

        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TYPE_TO_DEVICE_CLASS.get(device_type)

        self._is_stateful = "doorState" in self._channel
        if self._is_stateful:
            self._attr_supported_features = (
                CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
            )
        else:
            self._attr_supported_features = (
                CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
            )

    @property
    def is_closed(self) -> bool | None:
        if not self._is_stateful:
            return None
        return self._channel.get("doorState") == "CLOSED"

    @property
    def is_opening(self) -> bool:
        if not self._is_stateful:
            return False
        return self._channel.get("doorMotion") == "OPENING"

    @property
    def is_closing(self) -> bool:
        if not self._is_stateful:
            return False
        return self._channel.get("doorMotion") == "CLOSING"

    async def async_open_cover(self, **kwargs) -> None:
        self._attr_assumed_state = True
        if self._is_stateful:
            await self._client.async_send_door_command(
                self._device_id, self._channel_index, "OPEN"
            )
        else:
            await self._client.async_toggle_garage_door_state(
                self._device_id, self._channel_index
            )

    async def async_close_cover(self, **kwargs) -> None:
        self._attr_assumed_state = True
        if self._is_stateful:
            await self._client.async_send_door_command(
                self._device_id, self._channel_index, "CLOSE"
            )
        else:
            await self._client.async_toggle_garage_door_state(
                self._device_id, self._channel_index
            )

    async def async_stop_cover(self, **kwargs) -> None:
        if not self._is_stateful:
            return
        self._attr_assumed_state = True
        await self._client.async_send_door_command(
            self._device_id, self._channel_index, "STOP"
        )


# ADDED: New class for SHUTTER groups found in diagnostics
class HcuCoverGroup(HcuGroupBaseEntity, CoverEntity):
    """Representation of an HCU Cover (shutter or blind) group."""

    PLATFORM = Platform.COVER
    _attr_has_entity_name = False

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        group_data: dict,
        **kwargs: Any,
    ):
        """Initialize the HCU Cover group."""
        super().__init__(coordinator, client, group_data)
        label = self._group.get("label") or self._group_id
        self._attr_name = self._apply_prefix(label)
        self._attr_unique_id = self._group_id

        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )
        # Check if slatsLevel is a property of the group
        if "slatsLevel" in self._group:
            self._attr_supported_features |= CoverEntityFeature.SET_TILT_POSITION

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover group."""
        level = self._group.get("shutterLevel")
        return int((1 - level) * 100) if level is not None else None

    @property
    def current_cover_tilt_position(self) -> int | None:
        """Return current tilt position of cover group."""
        if "slatsLevel" not in self._group:
            return None
        level = self._group.get("slatsLevel")
        return int((1 - level) * 100) if level is not None else None

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover group is closed."""
        position = self.current_cover_position
        return position == 0 if position is not None else None

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover group."""
        self._attr_assumed_state = True
        await self._client.async_group_control(
            API_PATHS["SET_GROUP_SHUTTER_LEVEL"],
            self._group_id,
            {"primaryShadingLevel": 0.0},
        )

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover group."""
        self._attr_assumed_state = True
        await self._client.async_group_control(
            API_PATHS["SET_GROUP_SHUTTER_LEVEL"],
            self._group_id,
            {"primaryShadingLevel": 1.0},
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover group."""
        self._attr_assumed_state = True
        await self._client.async_group_control(
            API_PATHS["STOP_GROUP_COVER"], self._group_id
        )

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the cover group position."""
        position = kwargs[ATTR_POSITION]
        self._attr_assumed_state = True
        shutter_level = round((100 - position) / 100.0, 2)
        await self._client.async_group_control(
            API_PATHS["SET_GROUP_SHUTTER_LEVEL"],
            self._group_id,
            {"primaryShadingLevel": shutter_level},
        )

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Set the cover group tilt position."""
        position = kwargs[ATTR_TILT_POSITION]
        self._attr_assumed_state = True
        slats_level = round((100 - position) / 100.0, 2)
        await self._client.async_group_control(
            API_PATHS["SET_GROUP_SLATS_LEVEL"],
            self._group_id,
            {"secondaryShadingLevel": slats_level},
        )