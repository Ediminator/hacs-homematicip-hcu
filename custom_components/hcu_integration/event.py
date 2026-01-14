from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol
import asyncio
import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HcuBaseEntity
from .api import HcuApiClient

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


class TriggerableEvent(Protocol):
    """Protocol for event entities that can be triggered by the coordinator."""

    _device_id: str
    _channel_index_str: str

    def handle_trigger(self, event_type: str | None = None) -> None:
        ...


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the event platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][config_entry.entry_id]
    if entities := coordinator.entities.get(Platform.EVENT):
        async_add_entities(entities)


class _HcuEventBase(HcuBaseEntity, EventEntity):
    """Base for HCU EventEntities with startup/reload suppression and no restore."""

    _suppress_triggers: bool = True

    async def async_get_last_state(self) -> State | None:  # type: ignore[override]
        """Disable restoring the last event timestamp/state on restart."""
        return None

    async def async_get_last_extra_data(self) -> dict[str, Any] | None:  # type: ignore[override]
        """Disable restoring last event extra data (e.g., event_type/attrs) on restart."""
        return None

    async def async_added_to_hass(self) -> None:
        """Enable triggers only after HA is started / after entity is fully added."""
        await super().async_added_to_hass()

        hass = self.hass
        if hass is None:
            self._suppress_triggers = False
            return

        if not hass.is_running:
            # During HA startup: wait until HA is fully started
            self._suppress_triggers = True

            @callback
            def _on_started(_: Any) -> None:
                self._suppress_triggers = False

            self.async_on_remove(
                hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)
            )
        else:
            # During integration reload while HA is already running:
            # suppress only for the initial add/snapshot phase
            self._suppress_triggers = True
            asyncio.get_running_loop().call_soon(self._enable_triggers)

    @callback
    def _enable_triggers(self) -> None:
        self._suppress_triggers = False

    @callback
    def _maybe_fire(self, event_type: str, event_attributes: dict[str, Any] | None = None) -> None:
        """Fire an event if not suppressed and write state."""
        if self._suppress_triggers:
            _LOGGER.debug(
                "Suppressing event during startup/reload: %s %s type=%s",
                getattr(self, "_device_id", "?"),
                getattr(self, "_channel_index_str", "?"),
                event_type,
            )
            return

        self._trigger_event(event_type, event_attributes)
        self.async_write_ha_state()


class HcuDoorbellEvent(_HcuEventBase):
    """Representation of a Homematic IP HCU doorbell event entity."""

    PLATFORM = Platform.EVENT

    _attr_device_class = EventDeviceClass.DOORBELL
    _attr_event_types = ["press"]

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict[str, Any],
        channel_index: str,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        self._set_entity_name(channel_label=self._channel.get("label"))
        self._attr_unique_id = f"{self._device_id}_{self._channel_index_str}_doorbell_event"

    @callback
    def handle_trigger(self, event_type: str | None = None) -> None:
        """Handle a doorbell trigger."""
        # Doorbell has only one event type
        self._maybe_fire("press")


class HcuButtonEvent(_HcuEventBase):
    """Representation of a Homematic IP HCU button event entity."""

    PLATFORM = Platform.EVENT

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = [
        "press",
        "press_short",
        "press_long",
        "press_long_start",
        "press_long_stop",
    ]

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict[str, Any],
        channel_index: str,
    ):
        super().__init__(coordinator, client, device_data, channel_index)
        self._set_entity_name(channel_label=self._channel.get("label"))
        self._attr_unique_id = f"{self._device_id}_{self._channel_index_str}_button_event"

    @callback
    def handle_trigger(self, event_type: str | None = None) -> None:
        """Handle a button trigger from the coordinator."""
        # IMPORTANT: ignore "None" to avoid ghost presses from timestamp/status updates
        if event_type is None:
            _LOGGER.debug(
                "Ignoring button trigger with event_type=None: %s %s",
                self._device_id,
                self._channel_index_str,
            )
            return

        normalized_event = event_type.lower().replace("key_", "")
        if normalized_event not in self._attr_event_types:
            normalized_event = "press"

        self._maybe_fire(normalized_event)