# custom_components/hcu_integration/__init__.py
"""The Homematic IP Local (HCU) integration."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import HcuApiClient, HcuApiError
from .const import (
    CONF_AUTH_PORT,
    CONF_WEBSOCKET_PORT,
    CHANNEL_TYPE_MULTI_MODE_INPUT_TRANSMITTER,
    DEFAULT_HCU_AUTH_PORT,
    DEFAULT_HCU_WEBSOCKET_PORT,
    DEVICE_CHANNEL_EVENT_ONLY_TYPES,
    DEVICE_CHANNEL_EVENT_TYPES,
    DOMAIN,
    EVENT_CHANNEL_TYPES,
    MULTI_FUNCTION_CHANNEL_DEVICES,
    PLATFORMS,
    WEBSOCKET_CONNECT_TIMEOUT,
    WEBSOCKET_RECONNECT_INITIAL_DELAY,
    WEBSOCKET_RECONNECT_JITTER_MAX,
    WEBSOCKET_RECONNECT_MAX_DELAY,
)
from .discovery import async_discover_entities
from .services import (
    INTEGRATION_SERVICES,
    async_register_services,
    async_unregister_services,
)
from . import event

_LOGGER = logging.getLogger(__name__)

type HcuData = dict[str, "HcuCoordinator"]

SERVICE_ENTRIES_KEY = f"{DOMAIN}_service_entries"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homematic IP Local (HCU) from a config entry."""
    auth_port = entry.data.get(CONF_AUTH_PORT, DEFAULT_HCU_AUTH_PORT)
    websocket_port = entry.data.get(CONF_WEBSOCKET_PORT, DEFAULT_HCU_WEBSOCKET_PORT)

    client = HcuApiClient(
        hass,
        entry.data[CONF_HOST],
        entry.data[CONF_TOKEN],
        async_get_clientsession(hass),
        auth_port,
        websocket_port,
    )

    coordinator = HcuCoordinator(hass, client, entry)

    domain_data = cast(HcuData, hass.data.setdefault(DOMAIN, {}))
    domain_data[entry.entry_id] = coordinator

    if not await coordinator.async_setup():
        return False

    coordinator.entities = await async_discover_entities(hass, client, entry, coordinator)

    coordinator._event_entities = {
        (e._device_id, e._channel_index_str): e
        for e in coordinator.entities.get(Platform.EVENT, [])
        if hasattr(e, "handle_trigger")
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services (only once for first config entry)
    service_entries: set[str] = hass.data.setdefault(SERVICE_ENTRIES_KEY, set())
    if not service_entries:
        async_register_services(hass)
    service_entries.add(entry.entry_id)

    entry.add_update_listener(async_reload_entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: HcuCoordinator = hass.data[DOMAIN][entry.entry_id]

    if SERVICE_ENTRIES_KEY in hass.data:
        service_entries: set[str] = hass.data[SERVICE_ENTRIES_KEY]
        service_entries.discard(entry.entry_id)

        if not service_entries:
            async_unregister_services(hass)
            hass.data.pop(SERVICE_ENTRIES_KEY, None)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await coordinator.client.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


class HcuCoordinator(DataUpdateCoordinator[set[str]]):
    """Manages the HCU API client and data updates."""

    def __init__(
        self, hass: HomeAssistant, client: HcuApiClient, entry: ConfigEntry
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.client = client
        self.entities: dict[Platform, list[Entity]] = {}
        self._event_entities: dict[tuple[str, str], event.TriggerableEvent] = {}
        self._connected_event = asyncio.Event()

    async def async_setup(self) -> bool:
        """Initialize the coordinator and establish the initial connection."""
        self.config_entry.async_create_background_task(
            self.hass, self._listen_for_events(), name="HCU WebSocket Listener"
        )

        _LOGGER.debug("Waiting for WebSocket connection...")
        try:
            await asyncio.wait_for(
                self._connected_event.wait(), timeout=WEBSOCKET_CONNECT_TIMEOUT
            )
        except asyncio.TimeoutError:
            _LOGGER.error(
                "WebSocket connection timeout after %ds", WEBSOCKET_CONNECT_TIMEOUT
            )
            return False

        try:
            initial_state = await self.client.get_system_state()
            if not initial_state or "devices" not in initial_state:
                _LOGGER.error("Connected but failed to get valid initial state")
                return False
        except (HcuApiError, ConnectionError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to get initial state: %s", err)
            return False

        self._register_hcu_device()

        state = self.client.state
        all_ids = set(state.get("devices", {}).keys()) | set(state.get("groups", {}).keys())
        if home_id := state.get("home", {}).get("id"):
            all_ids.add(home_id)
        self.async_set_updated_data(all_ids)

        return True

    def _register_hcu_device(self) -> None:
        """Register the HCU as a device in Home Assistant."""
        device_registry = dr.async_get(self.hass)
        hcu_device_id = self.client.hcu_device_id

        if not hcu_device_id:
            _LOGGER.warning("Could not determine HCU device ID from state")
            return

        hcu_device = self.client.state.get("devices", {}).get(hcu_device_id, {})
        device_registry.async_get_or_create(
            config_entry_id=self.config_entry.entry_id,
            identifiers={(DOMAIN, hcu_device_id)},
            manufacturer=hcu_device.get("oem", "eQ-3"),
            model=hcu_device.get("modelType", "HCU"),
            name=hcu_device.get("label", "Homematic IP HCU"),
            sw_version=hcu_device.get("firmwareVersion", ""),
        )

    def _handle_event_message(self, msg: dict[str, Any]) -> None:
        """Process incoming event messages from the HCU."""
        if msg.get("type") != "HMIP_SYSTEM_EVENT":
            return

        body = msg.get("body", {})
        events = body.get("eventTransaction", {}).get("events", {})
        if not events:
            return

        device_channel_event_ids = self._handle_device_channel_events(events)

        # Capture old timestamps BEFORE state is updated by process_events
        old_timestamps: dict[tuple[str, str], Any] = {
            (dev_id, ch_idx): ch.get("lastStatusUpdate")
            for dev_id, dev in self.client.state.get("devices", {}).items()
            for ch_idx, ch in dev.get("functionalChannels", {}).items()
        }

        updated_ids = self.client.process_events(events)

        event_channels = self._extract_event_channels(events)
        self._detect_timestamp_based_button_presses(updated_ids, event_channels, old_timestamps)

        all_updated = updated_ids | device_channel_event_ids
        if all_updated:
            self.async_set_updated_data(all_updated)

    def _handle_device_channel_events(self, events: dict[str, Any]) -> set[str]:
        """Handle DEVICE_CHANNEL_EVENT type events (stateless buttons)."""
        updated_device_ids: set[str] = set()

        for event_data in events.values():
            if not isinstance(event_data, dict):
                continue

            if event_data.get("pushEventType") != "DEVICE_CHANNEL_EVENT":
                continue

            device_id = event_data.get("deviceId")
            channel_idx = str(event_data.get("channelIndex", ""))
            event_type = event_data.get("channelEventType")

            if not all([device_id, channel_idx, event_type]):
                continue

            if event_type not in DEVICE_CHANNEL_EVENT_TYPES:
                _LOGGER.debug("Unknown channel event type: %s", event_type)
                continue

            _LOGGER.debug(
                "Button event: device=%s, channel=%s, type=%s",
                device_id, channel_idx, event_type,
            )

            self._fire_button_event(device_id, channel_idx, event_type)
            self._trigger_event_entity(device_id, channel_idx, event_type)
            updated_device_ids.add(device_id)

        return updated_device_ids

    def _extract_event_channels(self, events: dict[str, Any]) -> set[tuple[str, str]]:
        """Extract channels that support button events from DEVICE_CHANGED events."""
        event_channels: set[tuple[str, str]] = set()

        for event_data in events.values():
            if not isinstance(event_data, dict):
                continue

            if event_data.get("pushEventType") != "DEVICE_CHANGED":
                continue

            device = event_data.get("device", {})
            device_id = device.get("id")
            device_type = device.get("type", "")

            if not device_id:
                continue

            channels = device.get("functionalChannels", {})
            for ch_idx, ch_data in channels.items():
                channel_type = ch_data.get("functionalChannelType", "")

                if channel_type in DEVICE_CHANNEL_EVENT_ONLY_TYPES:
                    # HmIP-WKP (Keypad) does not send DEVICE_CHANNEL_EVENT when in a group.
                    # We must allow timestamp-based detection for this device type.
                    if device_type != "HmIP-WKP":
                        continue

                if channel_type == CHANNEL_TYPE_MULTI_MODE_INPUT_TRANSMITTER:
                    if device_type in MULTI_FUNCTION_CHANNEL_DEVICES:
                        continue

                if channel_type in EVENT_CHANNEL_TYPES:
                    event_channels.add((device_id, ch_idx))
                elif device_type == "HmIP-WKP" and channel_type == "KEY_CHANNEL":
                    event_channels.add((device_id, ch_idx))

        return event_channels

    def _detect_timestamp_based_button_presses(
        self, updated_ids: set[str], event_channels: set[tuple[str, str]], old_timestamps: dict[tuple[str, str], Any]
    ) -> None:
        """Detect button presses via timestamp changes (legacy devices).
        
        Handles three cases:
        1. Timestamp changed: new_timestamp != old_timestamp
        2. Timestamp missing in new state but existed before -> legacy device button press
        3. Both timestamps missing but channel is in event_channels -> possible button press
        """
        for device_id in updated_ids:
            device = self.client.state.get("devices", {}).get(device_id)
            if not device:
                continue

            channels = device.get("functionalChannels", {})
            for ch_idx, ch_data in channels.items():
                if (device_id, ch_idx) not in event_channels:
                    continue

                new_timestamp = ch_data.get("lastStatusUpdate")
                old_timestamp = old_timestamps.get((device_id, ch_idx))

                # Fire button event if:
                # 1. Timestamp changed (new != old)
                # 2. New timestamp appeared (old was None)
                # 3. Timestamp missing but channel in event (legacy device)
                should_fire = (
                    new_timestamp != old_timestamp  # Covers cases 1 & 2
                    or (new_timestamp is None and old_timestamp is None)  # Case 3: legacy device
                )

                if should_fire:
                    _LOGGER.debug(
                        "Timestamp button press: device=%s, channel=%s (new_ts=%s, old_ts=%s)",
                        device_id, ch_idx, new_timestamp, old_timestamp,
                    )
                    self._fire_button_event(device_id, ch_idx, "PRESS_SHORT")
                    self._trigger_event_entity(device_id, ch_idx, "PRESS_SHORT")

    def _fire_button_event(
        self, device_id: str, channel_idx: str, event_type: str
    ) -> None:
        """Fire a button event to Home Assistant event bus."""
        self.hass.bus.async_fire(
            f"{DOMAIN}_event",
            {"device_id": device_id, "channel": channel_idx, "type": event_type},
        )

    def _trigger_event_entity(
        self, device_id: str, channel_idx: str, event_type: str | None = None
    ) -> None:
        """Trigger an event entity for a device/channel."""
        key = (device_id, channel_idx)
        entity = self._event_entities.get(key)

        if not entity:
            entity = next(
                (
                    e
                    for e in self.entities.get(Platform.EVENT, [])
                    if hasattr(e, "handle_trigger")
                    and e._device_id == device_id
                    and e._channel_index_str == channel_idx
                ),
                None,
            )
            if entity:
                self._event_entities[key] = entity
            else:
                _LOGGER.warning(
                    "Event entity not found: device=%s, channel=%s", device_id, channel_idx
                )
                return

        if event_type and isinstance(entity, event.HcuButtonEvent):
            entity.handle_trigger(event_type)
        else:
            entity.handle_trigger()

    async def _listen_for_events(self) -> None:
        """WebSocket listener with auto-reconnection."""
        reconnect_delay = WEBSOCKET_RECONNECT_INITIAL_DELAY

        while True:
            try:
                await self.client.connect()
                self.client.register_event_callback(self._handle_event_message)
                self._connected_event.set()
                reconnect_delay = WEBSOCKET_RECONNECT_INITIAL_DELAY

                _LOGGER.info("WebSocket connected to HCU")
                await self.client.listen()

            except (ConnectionError, asyncio.TimeoutError) as e:
                _LOGGER.warning("WebSocket disconnected: %s. Reconnecting in %ds", e, reconnect_delay)
            except asyncio.CancelledError:
                _LOGGER.info("WebSocket listener cancelled")
                break
            except Exception:
                _LOGGER.exception("WebSocket error. Reconnecting in %ds", reconnect_delay)

            if self.client.is_connected:
                await self.client.disconnect()

            self._connected_event.clear()

            jitter = random.uniform(0, WEBSOCKET_RECONNECT_JITTER_MAX)
            await asyncio.sleep(reconnect_delay + jitter)
            reconnect_delay = min(reconnect_delay * 2, WEBSOCKET_RECONNECT_MAX_DELAY)
