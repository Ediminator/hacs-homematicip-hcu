# custom_components/hcu_integration/api.py
"""API Client for the Homematic IP HCU."""
import aiohttp
import logging
import asyncio
from typing import Callable
from uuid import uuid4

_LOGGER = logging.getLogger(__name__)

class HcuApiClient:
    """A client to manage the WebSocket connection and state for a Homematic IP HCU."""
    def __init__(self, host: str, auth_token: str, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self._host = host
        self._auth_token = auth_token
        self._session = session
        self._websocket = None
        # --- FIX IS HERE ---
        # Initialize the state cache with empty dictionaries to prevent race conditions during startup.
        self._state = {"devices": {}, "groups": {}}
        # --- END OF FIX ---
        self._pending_requests: dict[str, asyncio.Future] = {}
        self._event_callback: Callable | None = None

    @property
    def is_connected(self) -> bool:
        """Return true if the websocket is connected."""
        return self._websocket is not None and not self._websocket.closed

    async def connect(self) -> None:
        """Establish a WebSocket connection to the HCU."""
        url = f"wss://{self._host}:9001"
        headers = { 
            "authtoken": self._auth_token, 
            "plugin-id": "de.homeassistant.hcu.integration",
            "hmip-system-events": "true"
        }
        self._websocket = await self._session.ws_connect(url, headers=headers, ssl=False)

    def register_event_callback(self, callback: Callable) -> None:
        """Register a callback function to handle non-response (push) events."""
        self._event_callback = callback

    def _handle_incoming_message(self, msg: dict) -> None:
        """Route incoming WebSocket messages."""
        msg_type = msg.get("type")
        msg_id = msg.get("id")

        if msg_type == "HMIP_SYSTEM_RESPONSE" and msg_id in self._pending_requests:
            future = self._pending_requests.get(msg_id)
            if future and not future.done():
                response_body = msg.get("body", {})
                if response_body.get("code") != 200:
                    _LOGGER.error("HCU returned an error: %s", response_body)
                    future.set_exception(Exception(f"HCU Error: {response_body}"))
                else:
                    future.set_result(response_body.get("body"))
        elif self._event_callback:
            self._event_callback(msg)

    async def listen(self) -> None:
        """The single, authoritative listener for all WebSocket messages."""
        if not self.is_connected:
            raise ConnectionAbortedError("WebSocket is not connected.")
        
        try:
            async for msg in self._websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self._handle_incoming_message(msg.json())
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    _LOGGER.warning("WebSocket connection closed or error: %s", msg.data)
                    raise ConnectionAbortedError("WebSocket connection lost.")
        finally:
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(ConnectionAbortedError("Listener stopped."))

    async def async_send_hmip_request(self, path: str, body: dict = None) -> dict | None:
        """Send a command and wait for its specific response."""
        if not self.is_connected:
            raise ConnectionError("Not connected to HCU WebSocket.")
        
        message_id = str(uuid4())
        message = {
            "type": "HMIP_SYSTEM_REQUEST", "pluginId": "de.homeassistant.hcu.integration",
            "id": message_id, "body": {"path": path, "body": body or {}},
        }
        
        future = asyncio.get_running_loop().create_future()
        self._pending_requests[message_id] = future
        
        _LOGGER.debug(f"Sending command to HCU: {message}")
        await self._websocket.send_json(message)

        try:
            result = await asyncio.wait_for(future, timeout=10)
            return result
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout waiting for response to message ID %s for request %s", message_id, path)
            raise
        finally:
            self._pending_requests.pop(message_id, None)

    async def get_system_state(self) -> dict:
        """Fetch the full system state and cache it."""
        response_body = await self.async_send_hmip_request(path="/hmip/home/getSystemState")
        if response_body:
            self._state = response_body
        return self._state

    def get_device_by_address(self, address: str) -> dict | None:
        """Get device or channel data by its address from the state cache."""
        return self._state.get("devices", {}).get(address)
        
    def get_group_by_id(self, group_id: str) -> dict | None:
        """Get group data by its ID from the state cache."""
        return self._state.get("groups", {}).get(group_id)

    def process_events(self, events: dict) -> set[str]:
        """Process a dictionary of events and update the internal state cache."""
        updated_ids = set()
        for event in events.values():
            event_type = event.get("pushEventType")
            if event_type == "DEVICE_CHANGED" and (device := event.get("device")):
                device_id = device["id"]
                self._state["devices"][device_id] = device
                updated_ids.add(device_id)
                if parent_id := device.get("PARENT"):
                    updated_ids.add(parent_id)
            elif event_type == "GROUP_CHANGED" and (group := event.get("group")):
                group_id = group["id"]
                self._state["groups"][group_id] = group
                updated_ids.add(group_id)
        return updated_ids

    # --- Control Methods ---
    async def async_set_switch_state(self, device_id: str, channel_index: int, on: bool) -> None:
        await self.async_send_hmip_request("/hmip/device/control/setSwitchState", {"deviceId": device_id, "channelIndex": channel_index, "on": on})
    
    async def async_set_dim_level(self, device_id: str, channel_index: int, dim_level: float) -> None:
        await self.async_send_hmip_request("/hmip/device/control/setDimLevel", {"deviceId": device_id, "channelIndex": channel_index, "dimLevel": dim_level})

    async def async_set_shutter_level(self, device_id: str, channel_index: int, shutter_level: float) -> None:
        await self.async_send_hmip_request("/hmip/device/control/setShutterLevel", {"deviceId": device_id, "channelIndex": channel_index, "shutterLevel": shutter_level})
        
    async def async_set_slats_level(self, device_id: str, channel_index: int, shutter_level: float, slats_level: float) -> None:
        await self.async_send_hmip_request("/hmip/device/control/setSlatsLevel", {"deviceId": device_id, "channelIndex": channel_index, "shutterLevel": shutter_level, "slatsLevel": slats_level})

    async def async_stop_cover(self, device_id: str, channel_index: int) -> None:
        await self.async_send_hmip_request("/hmip/device/control/stop", {"deviceId": device_id, "channelIndex": channel_index})

    async def async_set_lock_state(self, device_id: str, channel_index: int, state: str, pin: str) -> None:
        await self.async_send_hmip_request("/hmip/device/control/setLockState", {"deviceId": device_id, "channelIndex": channel_index, "targetLockState": state, "authorizationPin": pin})
        
    async def async_set_color_temperature_dim_level(self, device_id: str, channel_index: int, color_temp: int, dim_level: float) -> None:
        await self.async_send_hmip_request("/hmip/device/control/setColorTemperatureDimLevel", {"deviceId": device_id, "channelIndex": channel_index, "colorTemperature": color_temp, "dimLevel": dim_level})

    async def async_set_setpoint_temperature(self, group_id: str, temperature: float) -> None:
        await self.async_send_hmip_request("/hmip/group/heating/setSetPointTemperature", {"groupId": group_id, "setPointTemperature": temperature})
    
    async def async_set_control_mode(self, group_id: str, mode: str) -> None:
        await self.async_send_hmip_request("/hmip/group/heating/setControlMode", {"groupId": group_id, "controlMode": mode})
    
    async def async_set_boost(self, group_id: str, boost: bool) -> None:
        await self.async_send_hmip_request("/hmip/group/heating/setBoost", {"groupId": group_id, "boost": boost})

    async def disconnect(self) -> None:
        """Disconnect the WebSocket session."""
        if self.is_connected:
            await self._websocket.close()
        self._websocket = None