"""The Homematic IP Local (HCU) integration."""
from __future__ import annotations

import aiohttp
import asyncio
import logging
from typing import Any, cast
import random

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_TOKEN,
    ATTR_ENTITY_ID,
    Platform,
    ATTR_TEMPERATURE,
)
from homeassistant.core import HomeAssistant, ServiceCall, split_entity_id
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import HcuApiClient, HcuApiError
from .const import (
    DOMAIN,
    PLATFORMS,
    WEBSOCKET_CONNECT_TIMEOUT,
    WEBSOCKET_RECONNECT_INITIAL_DELAY,
    WEBSOCKET_RECONNECT_MAX_DELAY,
    WEBSOCKET_RECONNECT_JITTER_MAX,
    CONF_AUTH_PORT,
    CONF_WEBSOCKET_PORT,
    DEFAULT_HCU_AUTH_PORT,
    DEFAULT_HCU_WEBSOCKET_PORT,
    SERVICE_PLAY_SOUND,
    SERVICE_SET_RULE_STATE,
    SERVICE_ACTIVATE_PARTY_MODE,
    SERVICE_ACTIVATE_VACATION_MODE,
    SERVICE_ACTIVATE_ECO_MODE,
    SERVICE_DEACTIVATE_ABSENCE_MODE,
    ATTR_SOUND_FILE,
    ATTR_DURATION,
    ATTR_VOLUME,
    ATTR_RULE_ID,
    ATTR_ENABLED,
    ATTR_END_TIME,
    EVENT_CHANNEL_TYPES,
    DEVICE_CHANNEL_EVENT_TYPES,
    CHANNEL_TYPE_MULTI_MODE_INPUT_TRANSMITTER,
)
from .discovery import async_discover_entities
from . import event

_LOGGER = logging.getLogger(__name__)

type HcuData = dict[str, "HcuCoordinator"]

# Track service registration across multiple config entries using entry IDs
SERVICE_ENTRIES_KEY = f"{DOMAIN}_service_entries"

# Platform mapping for entity lookup (defined once at module level)
PLATFORM_MAP = {
    "switch": Platform.SWITCH,
    "light": Platform.LIGHT,
    "climate": Platform.CLIMATE,
    "button": Platform.BUTTON,
}

# List of integration services (single source of truth for registration/removal)
_INTEGRATION_SERVICES = [
    SERVICE_PLAY_SOUND,
    SERVICE_SET_RULE_STATE,
    SERVICE_ACTIVATE_PARTY_MODE,
    SERVICE_ACTIVATE_VACATION_MODE,
    SERVICE_ACTIVATE_ECO_MODE,
    SERVICE_DEACTIVATE_ABSENCE_MODE,
]


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

    coordinator.entities = await async_discover_entities(
        hass, client, entry, coordinator
    )

    # Build event entity lookup dictionary for efficient O(1) access
    # Register all event entities that implement the TriggerableEvent protocol
    coordinator._event_entities = {
        (event_entity._device_id, event_entity._channel_index_str): event_entity
        for event_entity in coordinator.entities.get(Platform.EVENT, [])
        if hasattr(event_entity, "handle_trigger")
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    def _get_entity_from_entity_id(entity_id: str) -> Entity | None:
        """Get entity object from entity_id across all coordinators.

        Args:
            entity_id: The entity ID to search for (e.g., "switch.my_switch")

        Returns:
            The Entity object if found, None otherwise
        """
        entity_domain, _ = split_entity_id(entity_id)
        platform = PLATFORM_MAP.get(entity_domain)

        # Return early if platform not supported
        if not platform:
            return None

        # Search through all coordinators for this entity using generator expression
        return next(
            (
                entity
                for coordinator in hass.data[DOMAIN].values()
                for entity in coordinator.entities.get(platform, [])
                if hasattr(entity, "entity_id") and entity.entity_id == entity_id
            ),
            None,
        )

    def _get_client_for_service() -> HcuApiClient:
        """Get the API client for service calls.

        For services not tied to specific entities, we use the first available client.
        All HCUs share the same home/rule/vacation settings.
        """
        for coordinator in hass.data[DOMAIN].values():
            return coordinator.client
        raise ValueError("No HCU client available")

    async def handle_play_sound(call: ServiceCall) -> None:
        """Handle the play_sound service call by delegating to the entity."""
        for entity_id in call.data[ATTR_ENTITY_ID]:
            hcu_entity = _get_entity_from_entity_id(entity_id)

            if not hcu_entity or not hasattr(hcu_entity, "async_play_sound"):
                _LOGGER.warning(
                    "Cannot play sound on %s, as it is not a compatible Homematic IP Local (HCU) device with sound capability.",
                    entity_id,
                )
                continue

            try:
                await hcu_entity.async_play_sound(
                    sound_file=call.data[ATTR_SOUND_FILE],
                    volume=call.data[ATTR_VOLUME],
                    duration=call.data[ATTR_DURATION],
                )
            except (HcuApiError, ConnectionError) as err:
                _LOGGER.error("Error calling play_sound for %s: %s", entity_id, err)

    async def handle_set_rule_state(call: ServiceCall) -> None:
        """Handle the set_rule_state service call."""
        rule_id = call.data[ATTR_RULE_ID]
        enabled = call.data[ATTR_ENABLED]
        try:
            client = _get_client_for_service()
            await client.async_enable_simple_rule(rule_id=rule_id, enabled=enabled)
            _LOGGER.info("Successfully set state for rule %s to %s", rule_id, enabled)
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Error setting state for rule %s: %s", rule_id, err)
        except ValueError as err:
            _LOGGER.error("No HCU available for service call: %s", err)

    async def handle_activate_party_mode(call: ServiceCall) -> None:
        """Handle the activate_party_mode service call."""
        for entity_id in call.data[ATTR_ENTITY_ID]:
            hcu_entity = _get_entity_from_entity_id(entity_id)

            if not hcu_entity or not hasattr(hcu_entity, "async_activate_party_mode"):
                _LOGGER.warning(
                    "Cannot activate party mode on %s, as it is not a compatible Homematic IP Local (HCU) climate entity.",
                    entity_id,
                )
                continue

            temperature = call.data[ATTR_TEMPERATURE]
            end_time_str = call.data.get(ATTR_END_TIME)
            duration = call.data.get(ATTR_DURATION)

            try:
                await hcu_entity.async_activate_party_mode(
                    temperature=temperature,
                    end_time_str=end_time_str,
                    duration=duration,
                )
            except (HcuApiError, ConnectionError) as err:
                _LOGGER.error(
                    "Error calling activate_party_mode for %s: %s", entity_id, err
                )
            except ValueError as err:
                _LOGGER.error(
                    "Invalid parameter for activate_party_mode for %s: %s",
                    entity_id,
                    err,
                )

    async def handle_activate_vacation_mode(call: ServiceCall) -> None:
        """Handle the activate_vacation_mode service call."""
        temperature = call.data[ATTR_TEMPERATURE]
        end_time_str = call.data.get(ATTR_END_TIME)

        try:
            dt_obj = dt_util.parse_datetime(end_time_str)
            if dt_obj is None:
                raise ValueError(f"Invalid datetime string received: {end_time_str}")

            formatted_end_time = dt_obj.strftime("%Y_%m_%d %H:%M")

            client = _get_client_for_service()
            await client.async_activate_vacation(
                temperature=temperature, end_time=formatted_end_time
            )
            _LOGGER.info(
                "Successfully activated vacation mode with temp %s until %s",
                temperature,
                end_time_str,
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Error activating vacation mode: %s", err)
        except ValueError as err:
            _LOGGER.error("Invalid parameter for vacation mode: %s", err)
        except Exception:
            _LOGGER.exception("Unexpected error during vacation mode activation.")

    async def handle_activate_eco_mode(call: ServiceCall) -> None:
        """Handle the activate_eco_mode service call."""
        try:
            client = _get_client_for_service()
            await client.async_activate_absence_permanent()
            _LOGGER.info("Successfully activated permanent absence (Eco mode).")
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Error activating permanent absence (Eco mode): %s", err)
        except ValueError as err:
            _LOGGER.error("No HCU available for service call: %s", err)

    async def handle_deactivate_absence_mode(call: ServiceCall) -> None:
        """Handle the deactivate_absence_mode service call."""
        try:
            client = _get_client_for_service()
            await client.async_deactivate_absence()
            _LOGGER.info("Successfully deactivated absence mode.")
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Error deactivating absence mode: %s", err)
        except ValueError as err:
            _LOGGER.error("No HCU available for service call: %s", err)

    # Define services and their handlers
    SERVICES = {
        SERVICE_PLAY_SOUND: handle_play_sound,
        SERVICE_SET_RULE_STATE: handle_set_rule_state,
        SERVICE_ACTIVATE_PARTY_MODE: handle_activate_party_mode,
        SERVICE_ACTIVATE_VACATION_MODE: handle_activate_vacation_mode,
        SERVICE_ACTIVATE_ECO_MODE: handle_activate_eco_mode,
        SERVICE_DEACTIVATE_ABSENCE_MODE: handle_deactivate_absence_mode,
    }

    # Register services only once, even with multiple config entries
    # Use a set to track active entry IDs (more robust than counter)
    service_entries: set[str] = hass.data.setdefault(SERVICE_ENTRIES_KEY, set())

    if not service_entries:
        # First config entry - register all services
        _LOGGER.debug("Registering HCU services for the first time")
        # Ensure service registration and removal lists are consistent
        assert set(SERVICES.keys()) == set(_INTEGRATION_SERVICES), (
            "SERVICES and _INTEGRATION_SERVICES must contain the same service names"
        )
        for service_name, handler in SERVICES.items():
            hass.services.async_register(DOMAIN, service_name, handler)
    else:
        _LOGGER.debug(
            "HCU services already registered, skipping registration (active entries: %d)",
            len(service_entries)
        )

    # Add this entry to the set of active entries
    service_entries.add(entry.entry_id)

    entry.add_update_listener(async_reload_entry)

    return True


class HcuCoordinator(DataUpdateCoordinator[set[str]]):
    """Manages the HCU API client and data updates."""

    def __init__(self, hass: HomeAssistant, client: HcuApiClient, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self.client = client
        self.entry = entry
        self.entities: dict[Platform, list] = {}
        self._event_entities: dict[tuple[str, str], event.TriggerableEvent] = {}  # Maps (device_id, channel_idx) to triggerable event entity
        self._connected_event = asyncio.Event()

    async def async_setup(self) -> bool:
        """Initialize the coordinator and establish the initial connection."""
        self.entry.async_create_background_task(
            self.hass, self._listen_for_events(), name="HCU WebSocket Listener"
        )

        _LOGGER.debug("Waiting for WebSocket connection to establish...")
        try:
            await asyncio.wait_for(
                self._connected_event.wait(), timeout=WEBSOCKET_CONNECT_TIMEOUT
            )
        except asyncio.TimeoutError:
            _LOGGER.error(
                "Failed to establish WebSocket connection within %d seconds",
                WEBSOCKET_CONNECT_TIMEOUT,
            )
            return False

        try:
            initial_state = await self.client.get_system_state()
            if not initial_state or "devices" not in initial_state:
                _LOGGER.error(
                    "HCU is connected, but failed to get a valid initial state."
                )
                return False
        except (HcuApiError, ConnectionError, asyncio.TimeoutError) as err:
            _LOGGER.error(
                "Failed to get initial state from HCU after connecting: %s", err
            )
            return False

        self._register_hcu_device()

        # Force an initial update for all devices, groups, and the home object
        # This ensures entities are marked available and not stuck in "restored" state
        _LOGGER.debug("Forcing initial state refresh for all entities")
        state = self.client.state
        all_ids = set(state.get("devices", {}).keys()) | set(state.get("groups", {}).keys())
        if home_id := state.get("home", {}).get("id"):
            all_ids.add(home_id)
        self.async_set_updated_data(all_ids)

        return True

    def _register_hcu_device(self) -> None:
        """Register the HCU itself as a device in Home Assistant."""
        device_registry = dr.async_get(self.hass)

        hcu_device_id = self.client.hcu_device_id
        if not hcu_device_id:
            _LOGGER.warning("Could not determine HCU device ID (SGTIN) from state.")
            return

        hcu_device_data = self.client.state.get("devices", {}).get(hcu_device_id, {})
        home_data = self.client.state.get("home", {})

        device_registry.async_get_or_create(
            config_entry_id=self.entry.entry_id,
            identifiers={(DOMAIN, hcu_device_id)},
            name=hcu_device_data.get("label") or "Homematic IP HCU",
            manufacturer="eQ-3",
            model=hcu_device_data.get("modelType") or "HCU",
            sw_version=home_data.get("currentAPVersion"),
        )

    def _extract_event_channels(self, events: dict) -> set[tuple[str, str]]:
        """Extract button channels that were updated in the events.

        Returns a set of (device_id, channel_index) tuples for channels that
        are of EVENT_CHANNEL_TYPES and were updated in the events, or channels
        that have button input capabilities (e.g., SWITCH_CHANNEL with DOUBLE_INPUT_SWITCH).

        Note: DEVICE_CHANNEL_EVENT type events are handled separately in
        _handle_device_channel_events and should not be added here to avoid
        duplicate event firing.
        """
        event_channels = set()
        for event in events.values():
            # Only process DEVICE_CHANGED events here
            # DEVICE_CHANNEL_EVENT events are handled separately in _handle_device_channel_events
            if event.get("pushEventType") != "DEVICE_CHANGED":
                continue

            device_data = event.get("device", {})
            device_id = device_data.get("id")
            if not device_id:
                continue

            for ch_idx, ch_data in device_data.get("functionalChannels", {}).items():
                channel_type = ch_data.get("functionalChannelType")

                # Check if this is a SWITCH_CHANNEL with DOUBLE_INPUT_SWITCH configuration
                # These are switches like HmIP-BSL that have physical button inputs
                is_double_input_switch = (
                    channel_type == "SWITCH_CHANNEL" and
                    ch_data.get("internalLinkConfiguration", {}).get("internalLinkConfigurationType") == "DOUBLE_INPUT_SWITCH"
                )

                # Standard event channel types or special SWITCH_CHANNEL with button inputs
                if channel_type in EVENT_CHANNEL_TYPES or is_double_input_switch:
                    event_channels.add((device_id, ch_idx))

        return event_channels

    def _fire_button_event(self, device_id: str, channel_idx: str, event_type: str) -> None:
        """Fire a button event to Home Assistant."""
        self.hass.bus.async_fire(
            f"{DOMAIN}_event",
            {
                "device_id": device_id,
                "channel": channel_idx,
                "type": event_type,
            },
        )

    def _trigger_event_entity(self, device_id: str, channel_idx: str) -> None:
        """Trigger an event entity for a specific device/channel.

        Uses the TriggerableEvent protocol to support any event entity type
        without coordinator needing to know specific implementation details.
        """
        # Use O(1) dictionary lookup
        key = (device_id, channel_idx)
        entity = self._event_entities.get(key)

        # Fallback: search entity list if not in dictionary (race condition during startup)
        if not entity:
            entity = next(
                (
                    event_entity
                    for event_entity in self.entities.get(Platform.EVENT, [])
                    if hasattr(event_entity, "handle_trigger")
                    and event_entity._device_id == device_id
                    and event_entity._channel_index_str == channel_idx
                ),
                None,
            )
            if entity:
                # Cache the entity to avoid repeated O(n) lookups
                self._event_entities[key] = entity
            else:
                _LOGGER.warning(
                    "Event entity not found for device=%s, channel=%s",
                    device_id, channel_idx
                )
                return

        entity.handle_trigger()
        _LOGGER.debug(
            "Triggered event entity for device=%s, channel=%s",
            device_id, channel_idx
        )

    def _handle_device_channel_events(self, events: dict) -> None:
        """Handle DEVICE_CHANNEL_EVENT type events (stateless buttons).

        These events are fired by newer button devices that don't maintain state.
        Examples: HmIP-WGS, HmIP-WRC6, HmIP-BSL. The events contain direct button press
        information without requiring timestamp comparison.

        Args:
            events: Dictionary of event data from the HCU WebSocket message
        """
        for event in events.values():
            if event.get("pushEventType") != "DEVICE_CHANNEL_EVENT":
                continue

            if event.get("channelEventType") not in DEVICE_CHANNEL_EVENT_TYPES:
                continue

            device_id = event.get("deviceId")
            channel_idx = event.get("functionalChannelIndex")
            event_type = event.get("channelEventType")

            if not device_id or channel_idx is None or not event_type:
                _LOGGER.debug("Skipping incomplete device channel event: %s", event)
                continue

            # Convert channel index to string for consistency
            channel_idx_str = str(channel_idx)
            self._fire_button_event(device_id, channel_idx_str, event_type)
            _LOGGER.debug(
                "Button press detected via device channel event: device=%s, channel=%s, type=%s",
                device_id, channel_idx_str, event_type
            )

    def _should_fire_button_press(
        self, new_timestamp: int | None, old_timestamp: int | None
    ) -> tuple[bool, str]:
        """Determine if a button press event should be fired based on timestamps.

        Returns:
            tuple: (should_fire, reason) where reason describes the detection method
        """
        if new_timestamp is not None and old_timestamp is not None:
            if new_timestamp != old_timestamp:
                return True, "timestamp change"
        elif new_timestamp is None:
            # No timestamp available, but channel was in event (stateless buttons)
            return True, "stateless channel"

        return False, ""

    def _detect_timestamp_based_button_presses(
        self, updated_ids: set[str], event_channels: set[tuple[str, str]], old_state: dict
    ) -> None:
        """Detect button presses by comparing timestamps after state update.

        Processes channels that were identified as having button capabilities
        (either standard event channels or special cases like SWITCH_CHANNEL
        with DOUBLE_INPUT_SWITCH configuration).
        """
        for dev_id in updated_ids:
            device = self.client.get_device_by_address(dev_id)
            if not device:
                continue

            for ch_idx, channel in device.get("functionalChannels", {}).items():
                # Only process channels that were in the raw events and identified as button-capable
                # event_channels already contains the filtered set from _extract_event_channels
                if (dev_id, ch_idx) not in event_channels:
                    continue

                # Check if button press should be fired based on timestamps
                new_ts = channel.get("lastStatusUpdate")
                old_ts = old_state.get(dev_id, {}).get(ch_idx)
                should_fire, reason = self._should_fire_button_press(new_ts, old_ts)

                if should_fire:
                    channel_type = channel.get("functionalChannelType")

                    # Trigger event entity for doorbell channels, otherwise fire button event
                    if channel_type == CHANNEL_TYPE_MULTI_MODE_INPUT_TRANSMITTER:
                        self._trigger_event_entity(dev_id, ch_idx)
                        event_label = "Doorbell press"
                    else:
                        self._fire_button_event(dev_id, ch_idx, "press")
                        event_label = "Button press"

                    _LOGGER.debug(
                        "%s detected via %s: device=%s, channel=%s",
                        event_label, reason, dev_id, ch_idx
                    )

    def _handle_event_message(self, message: dict) -> None:
        """Process incoming WebSocket event messages from the HCU."""
        if message.get("type") != "HMIP_SYSTEM_EVENT":
            return

        events = message.get("body", {}).get("eventTransaction", {}).get("events", {})
        if not events:
            return

        # Handle immediate stateless button events
        self._handle_device_channel_events(events)

        # Extract which event channels were updated for timestamp-based detection
        event_channels = self._extract_event_channels(events)

        # Store old timestamps before state update
        old_state = {
            dev_id: {
                ch_idx: ch.get("lastStatusUpdate")
                for ch_idx, ch in dev.get("functionalChannels", {}).items()
            }
            for dev_id, dev in self.client.state.get("devices", {}).items()
        }

        # Process events and update state
        updated_ids = self.client.process_events(events)

        # Detect button presses via timestamp changes
        self._detect_timestamp_based_button_presses(updated_ids, event_channels, old_state)

        if updated_ids:
            self.async_set_updated_data(updated_ids)

    async def _listen_for_events(self) -> None:
        """Maintain a persistent WebSocket connection with automatic reconnection."""
        reconnect_delay = WEBSOCKET_RECONNECT_INITIAL_DELAY

        while True:
            try:
                if not self.client.is_connected:
                    _LOGGER.info("Connecting to HCU WebSocket...")
                    await self.client.connect()
                    self.client.register_event_callback(self._handle_event_message)

                    self._connected_event.set()
                    reconnect_delay = WEBSOCKET_RECONNECT_INITIAL_DELAY

                await self.client.listen()

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                ConnectionAbortedError,
            ) as e:
                _LOGGER.warning(
                    "WebSocket listener disconnected: %s. Reconnecting in %d seconds.",
                    e,
                    reconnect_delay,
                )
            except asyncio.CancelledError:
                _LOGGER.info("WebSocket listener task cancelled.")
                break
            except Exception:
                _LOGGER.exception(
                    "Unexpected error in WebSocket listener. Reconnecting in %d seconds.",
                    reconnect_delay,
                )

            if self.client.is_connected:
                await self.client.disconnect()

            self._connected_event.clear()

            jitter = random.uniform(0, WEBSOCKET_RECONNECT_JITTER_MAX)
            await asyncio.sleep(reconnect_delay + jitter)

            reconnect_delay = min(reconnect_delay * 2, WEBSOCKET_RECONNECT_MAX_DELAY)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: HcuCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Handle service cleanup BEFORE removing coordinator to avoid race conditions
    # Check if SERVICE_ENTRIES_KEY exists before manipulating it
    if SERVICE_ENTRIES_KEY in hass.data:
        service_entries: set[str] = hass.data[SERVICE_ENTRIES_KEY]
        service_entries.discard(entry.entry_id)

        # Only remove services when the last config entry is unloaded
        if not service_entries:
            _LOGGER.debug("Unregistering HCU services (last config entry)")
            for service_name in _INTEGRATION_SERVICES:
                hass.services.async_remove(DOMAIN, service_name)
            # Clean up the set
            hass.data.pop(SERVICE_ENTRIES_KEY, None)
        else:
            _LOGGER.debug(
                "Keeping HCU services registered (remaining config entries: %d)",
                len(service_entries)
            )

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await coordinator.client.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
