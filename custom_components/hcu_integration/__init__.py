# custom_components/hcu_integration/__init__.py
"""The Homematic IP Local (HCU) integration."""
import logging
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .api import HcuApiClient
from .const import DOMAIN, PLATFORMS, SIGNAL_UPDATE_ENTITY

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homematic IP Local (HCU) from a config entry."""
    client = HcuApiClient(entry.data[CONF_HOST], entry.data[CONF_TOKEN], async_get_clientsession(hass))
    
    # Register an update listener for the options flow (e.g., for lock PIN)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = { "client": client }

    @callback
    def _handle_event_message(message: dict):
        """Handle incoming push event messages from the client's listener."""
        if message.get("type") != "HMIP_SYSTEM_EVENT":
            return
        
        _LOGGER.debug("Received HCU WebSocket Event: %s", message)
        
        events = message.get("body", {}).get("eventTransaction", {}).get("events", {})
        updated_ids = client.process_events(events)
        
        if updated_ids:
            # Broadcast a signal to entities that their data has been updated.
            async_dispatcher_send(hass, SIGNAL_UPDATE_ENTITY, updated_ids)

    async def listen_for_events():
        """
        Maintains a persistent WebSocket connection.

        This background task is responsible for listening to events from the HCU
        and handling automatic reconnections if the connection is lost.
        """
        while True:
            try:
                if not client.is_connected:
                    _LOGGER.info("WebSocket disconnected. Reconnecting...")
                    await client.connect()
                
                client.register_event_callback(_handle_event_message)
                await client.listen()

            except Exception as e:
                _LOGGER.error("Error in WebSocket listener: %s. Reconnecting in 30 seconds.", e)
                if client.is_connected:
                    await client.disconnect()
                await asyncio.sleep(30)

    # Start the listener task in the background.
    listener_task = asyncio.create_task(listen_for_events())
    entry.async_on_unload(listener_task.cancel)

    # Give the connection a moment to establish before sending the first command.
    await asyncio.sleep(1)

    try:
        # Now fetch the initial state. The listener is ready for the response.
        initial_state = await client.get_system_state()
        if not initial_state or "devices" not in initial_state:
            _LOGGER.error("HCU connected, but failed to get a valid initial state.")
            listener_task.cancel()
            await client.disconnect()
            return False
            
    except Exception as e:
        _LOGGER.error(f"Failed to get initial state from HCU after connecting: {e}")
        listener_task.cancel()
        await client.disconnect()
        return False

    hass.data[DOMAIN][entry.entry_id]["initial_state"] = initial_state

    # Register the main HCU device itself in the Home Assistant device registry.
    device_registry = dr.async_get(hass)
    home_id = initial_state.get("home", {}).get("id")
    home_data = initial_state.get("devices", {}).get(home_id, {})
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, home_id)},
        name=home_data.get("label") or "Homematic IP HCU",
        manufacturer="eQ-3",
        model=home_data.get("modelType") or "HCU",
        sw_version=initial_state.get("home", {}).get("currentAPVersion"),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and disconnect the client."""
    client: HcuApiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    await client.disconnect()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)