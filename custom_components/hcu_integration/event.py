# custom_components/hcu_integration/event.py
from typing import TYPE_CHECKING

from homeassistant.components.event import (
    EventDeviceClass,
    EventEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HcuBaseEntity
from .api import HcuApiClient

if TYPE_CHECKING:
    from . import HcuCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the event platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.EVENT):
        async_add_entities(entities)


class HcuDoorbellEvent(HcuBaseEntity, EventEntity):
    """Representation of a Homematic IP HCU doorbell event entity."""

    PLATFORM = Platform.EVENT

    _attr_device_class = EventDeviceClass.DOORBELL
    _attr_event_types = ["press"]

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        # Set entity name using the centralized naming helper
        self._set_entity_name(
            channel_label=self._channel.get("label"),
            feature_name="Doorbell"
        )

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_doorbell_event"

    @callback
    def _handle_doorbell_press(self) -> None:
        """Handle a doorbell press event."""
        self._trigger_event("press")
