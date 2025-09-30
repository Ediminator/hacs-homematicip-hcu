# custom_components/hcu_integration/__init__.py
"""
The Homematic IP Local (HCU) integration.

This component connects to a Homematic IP Home Control Unit (HCU) via its local
WebSocket API, allowing for real-time control and monitoring of Homematic IP devices.
"""
import logging
import asyncio
import aiohttp  # Linter Fix: Import the aiohttp library
import voluptuous as vol
from typing import cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN, ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api import HcuApiClient, HcuApiError
from .const import DOMAIN, PLATFORMS, API_PATHS

_LOGGER = logging.getLogger(__name__)

# Define a type hint for the data stored in hass.data[DOMAIN] for better type safety.
type HcuData = dict[str, "HcuCoordinator"]

# Define service constants and schemas
SERVICE_PLAY_SOUND = "play_sound"
ATTR_SOUND_FILE = "sound_file"
ATTR_DURATION = "duration"
ATTR_VOLUME = "volume"

PLAY_SOUND_SERVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
    vol.Required(ATTR_SOUND_FILE): cv.string,
    vol.Optional(ATTR_VOLUME, default=1.0): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=1.0)),
    vol.Optional(ATTR_DURATION, default=5.0): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=16383)),
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homematic IP Local (HCU) from a config entry."""
    client = HcuApiClient(
        entry.data[CONF_HOST], 
        entry.data[CONF_TOKEN],
        async_get_clientsession(hass)
    )
    
    coordinator = HcuCoordinator(hass, client, entry)
    
    # Store the coordinator instance in hass.data.
    domain_data = cast(HcuData, hass.data.setdefault(DOMAIN, {}))
    domain_data[entry.entry_id] = coordinator

    if not await coordinator.async_setup():
        return False
        
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register the custom 'play_sound' service
    async def handle_play_sound(call: ServiceCall) -> None:
        """Handle the play_sound service call."""
        entity_registry_instance = er.async_get(hass)
        for entity_id in call.data[ATTR_ENTITY_ID]:
            entity_entry = entity_registry_instance.async_get(entity_id)
            if entity_entry and entity_entry.platform == DOMAIN:
                # The unique_id is expected to be in the format: {device_id}_{channel_index}_...
                unique_id_parts = entity_entry.unique_id.split("_")
                if len(unique_id_parts) >= 2:
                    device_id, channel_index_str = unique_id_parts[0], unique_id_parts[1]
                    try:
                        await client.async_device_control(
                            path=API_PATHS.SET_SOUND_FILE,
                            device_id=device_id,
                            channel_index=int(channel_index_str),
                            body={
                                "onTime": call.data[ATTR_DURATION],
                                "soundFile": call.data[ATTR_SOUND_FILE],
                                "volumeLevel": call.data[ATTR_VOLUME],
                            },
                        )
                    except (HcuApiError, ConnectionError) as err:
                        _LOGGER.error("Error calling play_sound for %s: %s", entity_id, err)

    hass.services.async_register(DOMAIN, SERVICE_PLAY_SOUND, handle_play_sound, schema=PLAY_SOUND_SERVICE_SCHEMA)

    entry.add_update_listener(async_reload_entry)

    return True

class HcuCoordinator:
    """Manages the HCU API client, WebSocket connection, and data updates."""

    def __init__(self, hass: HomeAssistant, client: HcuApiClient, entry: ConfigEntry):
        """Initialize the data coordinator."""
        self.hass = hass
        self.client = client
        self.entry = entry

    async def async_setup(self) -> bool:
        """Set up the coordinator, connect, and fetch initial system state."""
        # Start a background task to maintain the WebSocket connection.
        self.entry.async_create_background_task(
            self.hass, self._listen_for_events(), name="HCU WebSocket Listener"
        )

        _LOGGER.debug("Waiting for connection to establish before fetching initial state...")
        await asyncio.sleep(1) # Brief delay to allow initial connection.

        try:
            initial_state = await self.client.get_system_state()
            if not initial_state or "devices" not in initial_state:
                _LOGGER.error("HCU is connected, but failed to get a valid initial state.")
                return False
        except (HcuApiError, ConnectionError, asyncio.TimeoutError) as err:
            _LOGGER.error("Failed to get initial state from HCU after connecting: %s", err)
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
        
    @callback
    def _handle_event_message(self, message: dict) -> None:
        """Handle incoming push event messages from the WebSocket."""
        if message.get("type") != "HMIP_SYSTEM_EVENT":
            return
        
        events = message.get("body", {}).get("eventTransaction", {}).get("events", {})
        # The client processes the events and returns a set of changed device/group IDs.
        updated_ids = self.client.process_events(events)
        
        # Dispatch a signal to notify entities that their data may have changed.
        if updated_ids:
            async_dispatcher_send(self.hass, f"{DOMAIN}_update", updated_ids)

    async def _listen_for_events(self) -> None:
        """Maintain a persistent WebSocket connection and handle reconnections."""
        reconnect_delay = 1
        while True:
            try:
                if not self.client.is_connected:
                    _LOGGER.info("Connecting to HCU WebSocket...")
                    await self.client.connect()
                    self.client.register_event_callback(self._handle_event_message)
                    reconnect_delay = 1
                
                # This call will block until the connection is lost.
                await self.client.listen()
            except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionAbortedError) as e:
                 _LOGGER.error(
                    "WebSocket listener disconnected: %s. Reconnecting in %d seconds.", 
                    e, reconnect_delay
                )
            except asyncio.CancelledError:
                _LOGGER.info("WebSocket listener task cancelled.")
                break
            except Exception as _: # Linter Fix: Use '_' for unused exception variable
                _LOGGER.exception(
                    "Unexpected error in WebSocket listener. Reconnecting in %d seconds.", 
                    reconnect_delay
                )

            if self.client.is_connected:
                await self.client.disconnect()
            await asyncio.sleep(reconnect_delay)
            # Implement exponential backoff for reconnection attempts.
            reconnect_delay = min(reconnect_delay * 2, 60)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: HcuCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Unregister the service when the integration is unloaded.
    hass.services.async_remove(DOMAIN, SERVICE_PLAY_SOUND)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        await coordinator.client.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)