# custom_components/hcu_integration/__init__.py
"""The Homematic IP Local (HCU) integration."""
import logging
import asyncio
from copy import deepcopy

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import device_registry as dr

from .api import HcuApiClient
from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Homematic IP Local (HCU) from a config entry."""
    host = entry.data[CONF_HOST]
    auth_token = entry.data[CONF_TOKEN]
    session = async_get_clientsession(hass)
    client = HcuApiClient(host, auth_token, session)

    try:
        await client.connect()
    except Exception as e:
        _LOGGER.error(f"Failed to connect to HCU: {e}")
        return False

    async def async_initial_data_fetch():
        """Fetch initial data from the API."""
        try:
            return await client.get_system_state()
        except Exception as e:
            raise UpdateFailed(f"Error communicating with API for initial fetch: {e}")

    coordinator = DataUpdateCoordinator(
        hass, _LOGGER, name="hcu_system_state",
        update_method=async_initial_data_fetch
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator
    }

    device_registry = dr.async_get(hass)
    home_data = coordinator.data.get("devices", {}).get(coordinator.data.get("home", {}).get("id"), {})
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, coordinator.data.get("home", {}).get("id"))},
        name=home_data.get("label") or "Homematic IP HCU",
        manufacturer="eQ-3",
        model=home_data.get("modelType") or "HCU",
        sw_version=home_data.get("firmwareVersion"),
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _handle_ws_message(message: dict):
        """Handle incoming WebSocket messages and update coordinator data."""
        msg_type = message.get("type")
        if msg_type != "HMIP_SYSTEM_EVENT":
            return

        new_data = deepcopy(coordinator.data)
        events = message.get("body", {}).get("eventTransaction", {}).get("events", {})

        for event in events.values():
            event_type = event.get("pushEventType")
            if event_type == "DEVICE_CHANGED":
                device = event.get("device", {})
                if device and "id" in device:
                    new_data["devices"][device["id"]] = device
            elif event_type == "GROUP_CHANGED":
                group = event.get("group", {})
                if group and "id" in group:
                    new_data["groups"][group["id"]] = group
            elif event_type == "DEVICE_REMOVED":
                new_data["devices"].pop(event.get("id"), None)
            elif event_type == "GROUP_REMOVED":
                new_data["groups"].pop(event.get("id"), None)
        
        coordinator.async_set_updated_data(new_data)

    entry.async_on_unload(
        hass.async_create_background_task(
            client.listen(_handle_ws_message), name="hcu_websocket_listener"
        )
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    client: HcuApiClient = hass.data[DOMAIN][entry.entry_id]["client"]
    await client.disconnect()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok