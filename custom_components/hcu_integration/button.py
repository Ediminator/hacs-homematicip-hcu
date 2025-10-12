# custom_components/hcu_integration/button.py
"""
Support for Homematic IP HCU stateless buttons.
These entities are event-based and do not have a persistent state.
"""
import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HcuBaseEntity
from .api import HcuApiClient

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the button platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][config_entry.entry_id]
    if entities := coordinator.entities.get(Platform.BUTTON):
        async_add_entities(entities)


class HcuButton(HcuBaseEntity, ButtonEntity):
    """
    Representation of a stateless button entity for HCU devices.

    This entity listens for `lastStatusUpdate` changes on its channel
    and fires a Home Assistant event when a press is detected. It does not
    hold a state itself.
    """
    PLATFORM = Platform.BUTTON
    _attr_has_entity_name = False

    def __init__(self, coordinator: "HcuCoordinator", client: HcuApiClient, device_data: dict, channel_index: str):
        super().__init__(coordinator, client, device_data, channel_index)
        
        channel_label = self._channel.get("label")
        device_label = self._device.get("label", "Unknown")
        
        self._attr_name = f"{device_label} {channel_label or f'Button {self._channel_index}'}"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_button_press"
        
        # Store the initial timestamp to detect the first press.
        self._last_update_ts = self._channel.get("lastStatusUpdate")

    @callback
    def _handle_coordinator_update(self) -> None:
        """
        Handle updates from the coordinator to detect a button press.

        This method overrides the default behavior to implement event-like
        functionality. A press is detected when the `lastStatusUpdate` timestamp
        for the specific channel changes.
        """
        if self._device_id not in self.coordinator.data:
            return

        new_ts = self._channel.get("lastStatusUpdate")

        # A new, different timestamp indicates a physical event occurred.
        if new_ts and new_ts != self._last_update_ts:
            _LOGGER.debug("Button press detected for %s", self.entity_id)
            self._last_update_ts = new_ts
            # The ButtonEntity's press method handles logging the event for HA.
            # This is a stateless action, so we don't call async_write_ha_state.
            self._press()
            self.async_write_ha_state() # Required to let HA know about the press event for logs

    async def async_press(self) -> None:
        """
        Handle the button press. This is a virtual action.
        The actual press is detected from device events.
        """
        _LOGGER.debug(
            "async_press called for %s, but this is an event-only entity.", self.entity_id
        )
