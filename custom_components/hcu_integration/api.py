# custom_components/hcu_integration/api.py
"""API Client for Homematic IP HCU."""
import aiohttp
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

class HcuApiClient:
    """A client to communicate with the Homematic IP HCU WebSocket API."""
    def __init__(self, host: str, auth_token: str, session: aiohttp.ClientSession):
        self._host = host
        self._auth_token = auth_token
        self._session = session
        self._websocket = None

    async def connect(self) -> None:
        """Establish a WebSocket connection."""
        url = f"wss://{self._host}:9001"
        headers = { 
            "authtoken": self._auth_token, 
            "plugin-id": "de.homeassistant.hcu.integration",
            "hmip-system-events": "true"
        }
        self._websocket = await self._session.ws_connect(url, headers=headers, ssl=False)

    async def get_system_state(self) -> dict:
        """Fetch the full system state from the HCU."""
        if not self._websocket or self._websocket.closed:
            raise Exception("Not connected")
        
        get_state_message = { "type": "HMIP_SYSTEM_REQUEST", "pluginId": "de.homeassistant.hcu.integration", "id": "get_system_state_1", "body": {"path": "/hmip/home/getSystemState", "body": {}} }
        await self._websocket.send_json(get_state_message)
        response = await self._websocket.receive_json()
        return response.get("body", {}).get("body", {})

    async def _send_control_command(self, path: str, body: dict, id_key: str) -> None:
        """Helper to send a generic control command."""
        if not self._websocket or self._websocket.closed:
            raise Exception("Not connected")
        
        message_id = f"id_{body.get(id_key)}"
        message = { "type": "HMIP_SYSTEM_REQUEST", "pluginId": "de.homeassistant.hcu.integration", "id": message_id, "body": {"path": path, "body": body} }
        _LOGGER.debug(f"Sending command to HCU: {message}")
        await self._websocket.send_json(message)

    async def async_set_switch_state(self, device_id: str, channel_index: int, on: bool) -> None:
        await self._send_control_command("/hmip/device/control/setSwitchState", {"deviceId": device_id, "channelIndex": channel_index, "on": on}, "deviceId")

    async def async_set_dim_level(self, device_id: str, channel_index: int, dim_level: float) -> None:
        await self._send_control_command("/hmip/device/control/setDimLevel", {"deviceId": device_id, "channelIndex": channel_index, "dimLevel": dim_level}, "deviceId")

    async def async_set_shutter_level(self, device_id: str, channel_index: int, shutter_level: float) -> None:
        await self._send_control_command("/hmip/device/control/setShutterLevel", {"deviceId": device_id, "channelIndex": channel_index, "shutterLevel": shutter_level}, "deviceId")
        
    async def async_set_slats_level(self, device_id: str, channel_index: int, shutter_level: float, slats_level: float) -> None:
        """Set the slats level for a cover device."""
        await self._send_control_command(
            "/hmip/device/control/setSlatsLevel",
            {"deviceId": device_id, "channelIndex": channel_index, "shutterLevel": shutter_level, "slatsLevel": slats_level},
            "deviceId"
        )

    async def async_stop_cover(self, device_id: str, channel_index: int) -> None:
        await self._send_control_command("/hmip/device/control/stop", {"deviceId": device_id, "channelIndex": channel_index}, "deviceId")

    async def async_set_lock_state(self, device_id: str, channel_index: int, state: str, pin: str) -> None:
        await self._send_control_command("/hmip/device/control/setLockState", {"deviceId": device_id, "channelIndex": channel_index, "targetLockState": state, "authorizationPin": pin}, "deviceId")
        
    async def async_set_color_temperature_dim_level(self, device_id: str, channel_index: int, color_temp: int, dim_level: float) -> None:
        await self._send_control_command("/hmip/device/control/setColorTemperatureDimLevel", {"deviceId": device_id, "channelIndex": channel_index, "colorTemperature": color_temp, "dimLevel": dim_level}, "deviceId")

    async def async_set_setpoint_temperature(self, group_id: str, temperature: float) -> None:
        await self._send_control_command("/hmip/group/heating/setSetPointTemperature", {"groupId": group_id, "setPointTemperature": temperature}, "groupId")
    
    async def async_set_control_mode(self, group_id: str, mode: str) -> None:
        await self._send_control_command("/hmip/group/heating/setControlMode", {"groupId": group_id, "controlMode": mode}, "groupId")
    
    async def async_set_boost(self, group_id: str, boost: bool) -> None:
        """Set the boost mode for a heating group."""
        await self._send_control_command(
            "/hmip/group/heating/setBoost",
            {"groupId": group_id, "boost": boost},
            "groupId"
        )

    async def disconnect(self) -> None:
        if self._websocket and not self._websocket.closed:
            await self._websocket.close()
            self._websocket = None

    async def listen(self, callback: callable) -> None:
        """Listen for messages on the WebSocket."""
        if not self._websocket:
            return
        
        _LOGGER.info("Starting WebSocket listener")
        try:
            async for msg in self._websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await callback(msg.json())
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    _LOGGER.warning("WebSocket connection closed or error: %s", msg.data)
                    break
        except Exception as e:
            _LOGGER.error("Exception in WebSocket listener: %s", e)