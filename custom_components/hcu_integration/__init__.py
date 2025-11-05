"""The Homematic IP Local (HCU) integration."""
from __future__ import annotations

import aiohttp
import asyncio
import logging
from typing import cast
import random

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_TOKEN,
    ATTR_ENTITY_ID,
    Platform,
    ATTR_TEMPERATURE,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
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
)
from .discovery import async_discover_entities

_LOGGER = logging.getLogger(__name__)

type HcuData = dict[str, "HcuCoordinator"]


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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_play_sound(call: ServiceCall) -> None:
        """Handle the play_sound service call by delegating to the entity."""
        for entity_id in call.data[ATTR_ENTITY_ID]:
            hcu_entity = None
            entity_domain = entity_id.split(".")[0]
            
            if entity_domain == "switch":
                hcu_entity = (
                    hass.data["entity_components"]
                    .get(Platform.SWITCH)
                    .get_entity(entity_id)
                )
            elif entity_domain == "light":
                hcu_entity = (
                    hass.data["entity_components"]
                    .get(Platform.LIGHT)
                    .get_entity(entity_id)
                )

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
            await client.async_enable_simple_rule(rule_id=rule_id, enabled=enabled)
            _LOGGER.info("Successfully set state for rule %s to %s", rule_id, enabled)
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Error setting state for rule %s: %s", rule_id, err)

    async def handle_activate_party_mode(call: ServiceCall) -> None:
        """Handle the activate_party_mode service call."""
        for entity_id in call.data[ATTR_ENTITY_ID]:
            hcu_entity = (
                hass.data["entity_components"]
                .get(Platform.CLIMATE)
                .get_entity(entity_id)
            )

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
            _LOGGER.error("Invalid end_time for vacation mode: %s", err)
        except Exception:
            _LOGGER.exception("Unexpected error during vacation mode activation.")

    async def handle_activate_eco_mode(call: ServiceCall) -> None:
        """Handle the activate_eco_mode service call."""
        try:
            await client.async_activate_absence_permanent()
            _LOGGER.info("Successfully activated permanent absence (Eco mode).")
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Error activating permanent absence (Eco mode): %s", err)

    async def handle_deactivate_absence_mode(call: ServiceCall) -> None:
        """Handle the deactivate_absence_mode service call."""
        try:
            await client.async_deactivate_absence()
            _LOGGER.info("Successfully deactivated absence mode.")
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Error deactivating absence mode: %s", err)

    hass.services.async_register(DOMAIN, SERVICE_PLAY_SOUND, handle_play_sound)
    hass.services.async_register(DOMAIN, SERVICE_SET_RULE_STATE, handle_set_rule_state)
    hass.services.async_register(
        DOMAIN, SERVICE_ACTIVATE_PARTY_MODE, handle_activate_party_mode
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ACTIVATE_VACATION_MODE, handle_activate_vacation_mode
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ACTIVATE_ECO_MODE, handle_activate_eco_mode
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DEACTIVATE_ABSENCE_MODE, handle_deactivate_absence_mode
    )

    entry.add_update_listener(async_reload_entry)

    return True


class HcuCoordinator(DataUpdateCoordinator[set[str]]):
    """Manages the HCU API client and data updates."""

    def __init__(self, hass: HomeAssistant, client: HcuApiClient, entry: ConfigEntry):
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

    def _handle_event_message(self, message: dict) -> None:
        """Process incoming WebSocket event messages from the HCU."""
        if message.get("type") != "HMIP_SYSTEM_EVENT":
            return

        events = message.get("body", {}).get("eventTransaction", {}).get("events", {})
        if not events:
            return

        # Extract which specific button channels were updated in these events
        # Only track EVENT_CHANNEL_TYPES to prevent firing events for all channels
        event_channel_updates = set()  # Set of (device_id, channel_idx) tuples
        for event in events.values():
            if event.get("pushEventType") == "DEVICE_CHANGED":
                device_data = event.get("device", {})
                device_id = device_data.get("id")
                if device_id:
                    for ch_idx, ch_data in device_data.get("functionalChannels", {}).items():
                        # Only add channels that are actually event channels (buttons)
                        if ch_data.get("functionalChannelType") in EVENT_CHANNEL_TYPES:
                            event_channel_updates.add((device_id, ch_idx))
            elif event.get("pushEventType") == "DEVICE_CHANNEL_EVENT":
                # Stateless buttons trigger DEVICE_CHANNEL_EVENT with no state/timestamp
                if event.get("channelEventType") in DEVICE_CHANNEL_EVENT_TYPES:
                    self.hass.bus.async_fire(
                        f"{DOMAIN}_event",
                        {
                            "device_id": event.get("deviceId"),
                            "channel": event.get("functionalChannelIndex"),
                            "type": event.get("channelEventType"),
                        },
                    )
                    _LOGGER.debug(                                               
                        "Button press detected via device channel event: device=%s, channel=%s",
                        event.get("deviceId"), event.get("functionalChannelIndex")
                    )

        # Store old timestamps to detect stateless button presses
        old_state = {
            dev_id: {
                ch_idx: ch.get("lastStatusUpdate")
                for ch_idx, ch in dev.get("functionalChannels", {}).items()
            }
            for dev_id, dev in self.client.state.get("devices", {}).items()
        }

        updated_ids = self.client.process_events(events)

        # After state is updated, check for button presses by comparing timestamps
        for dev_id in updated_ids:
            device = self.client.get_device_by_address(dev_id)
            if not device:
                continue

            for ch_idx, channel in device.get("functionalChannels", {}).items():
                channel_type = channel.get("functionalChannelType")
                if channel_type not in EVENT_CHANNEL_TYPES:
                    continue

                # Check if this specific channel was in the raw events
                # This prevents firing events for unrelated channels on the same device
                if (dev_id, ch_idx) not in event_channel_updates:
                    continue

                # Try timestamp-based detection first (for devices with timestamps)
                new_ts = channel.get("lastStatusUpdate")
                old_ts = old_state.get(dev_id, {}).get(ch_idx)
                
                # Fire event if:
                # 1. Timestamp exists and changed (existing behavior - safe)
                # 2. No timestamp exists but channel was in the event (new fix for HmIP-WGS)
                should_fire = False
                
                if new_ts is not None and old_ts is not None and new_ts != old_ts:
                    # Timestamp-based detection (existing logic for devices with timestamps)
                    should_fire = True
                    _LOGGER.debug(
                        "Button press detected via timestamp change: device=%s, channel=%s",
                        dev_id, ch_idx
                    )
                elif new_ts is None:
                    # No timestamp available, but channel was in event
                    # This handles stateless buttons like HmIP-WGS
                    should_fire = True
                    _LOGGER.debug(
                        "Button press detected for stateless channel: device=%s, channel=%s",
                        dev_id, ch_idx
                    )
                
                if should_fire:
                    self.hass.bus.async_fire(
                        f"{DOMAIN}_event",
                        {
                            "device_id": dev_id,
                            "channel": ch_idx,
                            "type": "press",
                        },
                    )

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

    hass.services.async_remove(DOMAIN, SERVICE_PLAY_SOUND)
    hass.services.async_remove(DOMAIN, SERVICE_SET_RULE_STATE)
    hass.services.async_remove(DOMAIN, SERVICE_ACTIVATE_PARTY_MODE)
    hass.services.async_remove(DOMAIN, SERVICE_ACTIVATE_VACATION_MODE)
    hass.services.async_remove(DOMAIN, SERVICE_ACTIVATE_ECO_MODE)
    hass.services.async_remove(DOMAIN, SERVICE_DEACTIVATE_ABSENCE_MODE)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await coordinator.client.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)
