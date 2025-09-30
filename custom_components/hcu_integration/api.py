# custom_components/hcu_integration/api.py
"""API Client for the Homematic IP HCU integration."""
import aiohttp
import logging
import asyncio
from typing import Callable
from uuid import uuid4

from .const import (
    HCU_WEBSOCKET_PORT, PLUGIN_ID, HCU_DEVICE_TYPES, HCU_MODEL_TYPES, 
    API_REQUEST_TIMEOUT, API_PATHS
)

_LOGGER = logging.getLogger(__name__)


class HcuApiError(Exception):
    """Custom exception for API errors returned by the HCU."""
    pass

class HcuApiClient:
    """A client to manage the WebSocket connection and state for a Homematic IP HCU."""

    def __init__(self, host: str, auth_token: str, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self._host = host
        self._auth_token = auth_token
        self.plugin_id = PLUGIN_ID
        self._session = session
        self._websocket: aiohttp.ClientWebSocketResponse | None = None
        self._state: dict = {"devices": {}, "groups": {}}
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._event_callback: Callable | None = None
        
        self._hcu_device_ids: set[str] = set()
        self._primary_hcu_device_id: str | None = None

    @property
    def state(self) -> dict:
        """Return the cached system state."""
        return self._state
        
    @property
    def hcu_device_id(self) -> str | None:
        """
        Return the primary HCU's device ID (SGTIN).
        This is used as the main identifier for the HCU device in Home Assistant.
        """
        return self._primary_hcu_device_id

    @property
    def hcu_part_device_ids(self) -> set[str]:
        """
        Return a set of all device IDs that represent a part of the HCU.
        This is crucial for preventing duplicate device entries in Home Assistant.
        """
        return self._hcu_device_ids

    def _update_hcu_device_ids(self) -> None:
        """
        Scan the state to find all devices that are part of the HCU.
        This prevents creating duplicate devices if the HCU is composed of multiple entries.
        """
        primary_id = self.state.get("home", {}).get("accessPointId")
        
        # First, search by specific device types known to be the HCU.
        hcu_ids = {
            device_id for device_id, device_data in self.state.get("devices", {}).items()
            if device_data.get("type") in HCU_DEVICE_TYPES
        }
        
        # As a fallback for different firmware or models, search by model type if no devices were found.
        if not hcu_ids:
            _LOGGER.debug("No HCU found by device type, trying fallback by model type.")
            hcu_ids = {
                device_id for device_id, device_data in self.state.get("devices", {}).items()
                if device_data.get("modelType") in HCU_MODEL_TYPES
            }

        if primary_id:
            hcu_ids.add(primary_id)
        
        self._hcu_device_ids = hcu_ids
        
        if primary_id:
            self._primary_hcu_device_id = primary_id
        elif hcu_ids:
            self._primary_hcu_device_id = next(iter(hcu_ids))
        else:
            self._primary_hcu_device_id = None
        
        _LOGGER.debug(
            "Identified HCU parts. Primary ID: %s, All IDs: %s", 
            self._primary_hcu_device_id, self._hcu_device_ids
        )

    @property
    def is_connected(self) -> bool:
        """Return true if the websocket is connected."""
        return self._websocket is not None and not self._websocket.closed

    async def connect(self) -> None:
        """Establish a WebSocket connection to the HCU."""
        if self.is_connected:
            await self.disconnect()

        url = f"wss://{self._host}:{HCU_WEBSOCKET_PORT}"
        headers = { 
            "authtoken": self._auth_token, 
            "plugin-id": self.plugin_id,
            "hmip-system-events": "true"
        }
        _LOGGER.info("Connecting to HCU WebSocket at %s", url)
        self._websocket = await self._session.ws_connect(url, headers=headers, ssl=False)

    def register_event_callback(self, callback: Callable) -> None:
        """Register a callback function to handle non-response (push) events."""
        self._event_callback = callback

    def _handle_incoming_message(self, msg: dict) -> None:
        """Route incoming WebSocket messages."""
        msg_type = msg.get("type")
        msg_id = msg.get("id")

        if msg_type == "HMIP_SYSTEM_RESPONSE" and msg_id in self._pending_requests:
            future = self._pending_requests.pop(msg_id)
            if not future.done():
                response_body = msg.get("body", {})
                if response_body.get("code") != 200:
                    _LOGGER.error("HCU returned an error for request ID %s: %s", msg_id, response_body)
                    future.set_exception(HcuApiError(f"HCU Error: {response_body}"))
                else:
                    future.set_result(response_body.get("body"))
        elif self._event_callback:
            self._event_callback(msg)

    async def listen(self) -> None:
        """Listen for all WebSocket messages and route them."""
        if not self.is_connected:
            raise ConnectionAbortedError("WebSocket is not connected.")
        
        try:
            async for msg in self._websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self._handle_incoming_message(msg.json())
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    raise ConnectionAbortedError(f"WebSocket connection issue: {msg.data}")
        finally:
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(ConnectionAbortedError("WebSocket listener stopped unexpectedly."))
            self._pending_requests.clear()

    async def async_send_message(self, message: dict) -> None:
        """Send a raw JSON message to the WebSocket."""
        if not self.is_connected:
            raise ConnectionError("Not connected to HCU WebSocket.")
        _LOGGER.debug("Sending message to HCU: %s", message)
        await self._websocket.send_json(message)

    async def async_send_hmip_request(self, path: str, body: dict | None = None, timeout: int = API_REQUEST_TIMEOUT) -> dict | None:
        """
        Send a command and wait for a response.
        
        This includes retry logic for transient connection/network errors.
        HCU API errors (e.g., bad request) are not retried as they indicate a
        non-transient issue with the command itself.
        """
        message_id = str(uuid4())
        message = {
            "type": "HMIP_SYSTEM_REQUEST", "pluginId": self.plugin_id,
            "id": message_id, "body": {"path": path, "body": body or {}},
        }
        
        last_exception = None
        for attempt in range(2):
            future = asyncio.get_running_loop().create_future()
            self._pending_requests[message_id] = future
            try:
                await self.async_send_message(message)
                return await asyncio.wait_for(future, timeout=timeout)
            except (ConnectionError, ConnectionAbortedError, asyncio.TimeoutError) as err:
                _LOGGER.warning("Request failed on attempt %d for path %s: %s", attempt + 1, path, err)
                last_exception = err
                self._pending_requests.pop(message_id, None)
                if attempt == 0:
                    await asyncio.sleep(2)
            except HcuApiError as err:
                _LOGGER.error("HCU returned an unrecoverable error for path %s.", path)
                last_exception = err
                break

        raise HcuApiError(f"Request failed after multiple retries for path {path}") from last_exception

    async def get_system_state(self) -> dict:
        """Fetch the full system state, cache it, and identify HCU devices."""
        response_body = await self.async_send_hmip_request(
            path=API_PATHS.GET_SYSTEM_STATE, timeout=30
        )
        if response_body:
            self._state = response_body
            self._update_hcu_device_ids()
        return self._state

    def get_device_by_address(self, address: str) -> dict | None:
        """Get device data by its address from the state cache."""
        return self._state.get("devices", {}).get(address)
        
    def get_group_by_id(self, group_id: str) -> dict | None:
        """Get group data by its ID from the state cache."""
        return self._state.get("groups", {}).get(group_id)

    def process_events(self, events: dict) -> set[str]:
        """Process a dictionary of events and update the internal state cache."""
        updated_ids = set()
        for event in sorted(events.values(), key=lambda e: e.get("index", 0)):
            event_type = event.get("pushEventType")
            if event_type == "DEVICE_CHANGED" and (device := event.get("device")):
                device_id = device["id"]
                if self._state["devices"].get(device_id) and device.get("functionalChannels"):
                    for ch_idx, ch_data in device["functionalChannels"].items():
                        self._state["devices"][device_id]["functionalChannels"][ch_idx].update(ch_data)
                else:
                    self._state["devices"][device_id] = device
                updated_ids.add(device_id)
            elif event_type == "GROUP_CHANGED" and (group := event.get("group")):
                group_id = group["id"]
                self._state["groups"][group_id] = group
                updated_ids.add(group_id)
            elif event_type == "HOME_CHANGED" and (home := event.get("home")):
                home_id = home["id"]
                self._state["home"] = home
                updated_ids.add(home_id)
        return updated_ids

    async def async_device_control(self, path: str, device_id: str, channel_index: int, body: dict | None = None) -> None:
        """Send a generic device control command."""
        payload = {"deviceId": device_id, "channelIndex": channel_index}
        if body:
            payload.update(body)
        await self.async_send_hmip_request(path, payload)

    async def async_group_control(self, path: str, group_id: str, body: dict | None = None) -> None:
        """Send a generic group control command."""
        payload = {"groupId": group_id}
        if body:
            payload.update(body)
        await self.async_send_hmip_request(path, payload)
        
    async def async_home_control(self, path: str, body: dict | None = None) -> None:
        """Send a generic home control command."""
        await self.async_send_hmip_request(path, body or {})

    async def disconnect(self) -> None:
        """Disconnect the WebSocket session."""
        if self.is_connected:
            _LOGGER.info("Closing WebSocket connection.")
            await self._websocket.close()
        self._websocket = None