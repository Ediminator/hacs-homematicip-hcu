# custom_components/hcu_integration/api.py
"""API client for communicating with the Homematic IP Home Control Unit (HCU)."""
import aiohttp
import logging
import asyncio
from typing import Callable, Any
from uuid import uuid4

from homeassistant.core import HomeAssistant

from .const import (
    PLUGIN_ID,
    HCU_DEVICE_TYPES,
    HCU_MODEL_TYPES,
    API_REQUEST_TIMEOUT,
    API_PATHS,
    API_RETRY_DELAY,
    WEBSOCKET_HEARTBEAT_INTERVAL,
    WEBSOCKET_RECEIVE_TIMEOUT,
)
from .util import create_unverified_ssl_context

_LOGGER = logging.getLogger(__name__)


class HcuApiError(Exception):
    """Custom exception for API errors returned by the HCU."""

    pass


class HcuApiClient:
    """
    Client for managing WebSocket connection and communication with HCU.

    This client handles:
    - WebSocket connection lifecycle (connect, disconnect, reconnect)
    - Bidirectional message exchange (requests and events)
    - State caching for devices, groups, and home data
    - Request/response correlation via message IDs
    """

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        auth_token: str,
        session: aiohttp.ClientSession,
        auth_port: int,
        websocket_port: int,
    ):
        """Initialize the API client."""
        self.hass = hass
        self._host = host
        self._auth_token = auth_token
        self.plugin_id = PLUGIN_ID
        self._session = session
        self._auth_port = auth_port
        self._websocket_port = websocket_port
        self._websocket: aiohttp.ClientWebSocketResponse | None = None
        self._state: dict = {"devices": {}, "groups": {}}

        self._pending_requests: dict[str, asyncio.Future] = {}
        self._event_callback: Callable | None = None
        self._hcu_device_ids: set[str] = set()
        self._primary_hcu_device_id: str | None = None

    @property
    def state(self) -> dict:
        """Return the current cached state."""
        if not self._state:
            _LOGGER.warning("State accessed before initialization")
        return self._state

    @property
    def hcu_device_id(self) -> str | None:
        """Return the primary HCU's device ID (SGTIN)."""
        return self._primary_hcu_device_id

    @property
    def hcu_part_device_ids(self) -> set[str]:
        """Return all device IDs that are part of the HCU hardware."""
        return self._hcu_device_ids

    def _update_hcu_device_ids(self) -> None:
        """
        Identify which devices in the state represent the HCU itself.
        This is used to correctly associate entities with the main HCU device.
        """
        primary_id = self.state.get("home", {}).get("accessPointId")

        hcu_ids = {
            device_id
            for device_id, device_data in self.state.get("devices", {}).items()
            if device_data.get("type") in HCU_DEVICE_TYPES
        }

        if not hcu_ids:
            _LOGGER.debug("No HCU found by device type, trying fallback by model type.")
            hcu_ids = {
                device_id
                for device_id, device_data in self.state.get("devices", {}).items()
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
            self._primary_hcu_device_id,
            self._hcu_device_ids,
        )

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket connection is active."""
        return self._websocket is not None and not self._websocket.closed

    async def connect(self) -> None:
        """
        Establish WebSocket connection to the HCU.
        """
        if self.is_connected:
            await self.disconnect()

        url = f"wss://{self._host}:{self._websocket_port}"
        headers = {
            "authtoken": self._auth_token,
            "plugin-id": self.plugin_id,
            "hmip-system-events": "true",
        }

        _LOGGER.info("Connecting to HCU WebSocket at %s", url)
        ssl_context = await create_unverified_ssl_context(self.hass)

        self._websocket = await self._session.ws_connect(
            url,
            headers=headers,
            ssl=ssl_context,
            heartbeat=WEBSOCKET_HEARTBEAT_INTERVAL,
            receive_timeout=WEBSOCKET_RECEIVE_TIMEOUT,
        )

    def register_event_callback(self, callback: Callable) -> None:
        """Register a callback to handle incoming event messages."""
        self._event_callback = callback

    def _handle_incoming_message(self, msg: dict) -> None:
        """
        Route incoming WebSocket messages to appropriate handlers.
        Responses to pending requests are resolved via their futures.
        All other messages are passed to the event callback.
        """
        msg_type = msg.get("type")
        msg_id = msg.get("id")

        if msg_type == "HMIP_SYSTEM_RESPONSE" and msg_id in self._pending_requests:
            future = self._pending_requests.pop(msg_id)
            if not future.done():
                response_body = msg.get("body", {})
                if response_body.get("code") != 200:
                    _LOGGER.error(
                        "HCU returned an error for request ID %s: %s", msg_id, response_body
                    )
                    future.set_exception(HcuApiError(f"HCU Error: {response_body}"))
                else:
                    future.set_result(response_body.get("body"))
        elif self._event_callback:
            self._event_callback(msg)

    async def listen(self) -> None:
        """
        Listen for incoming WebSocket messages in a continuous loop.
        This is the main loop for receiving real-time events from the HCU.
        """
        if not self.is_connected:
            raise ConnectionAbortedError("WebSocket is not connected.")

        try:
            async for msg in self._websocket:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    self._handle_incoming_message(msg.json())
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    raise ConnectionAbortedError(
                        f"WebSocket connection issue: {msg.data}"
                    )
        finally:
            # Clean up any pending requests if the listener stops unexpectedly.
            for future in self._pending_requests.values():
                if not future.done():
                    future.set_exception(
                        ConnectionAbortedError("WebSocket listener stopped unexpectedly.")
                    )
            self._pending_requests.clear()

    async def async_send_message(self, message: dict) -> None:
        """Send a JSON message over the WebSocket."""
        if not self.is_connected:
            raise ConnectionError("Not connected to HCU WebSocket.")
        _LOGGER.debug("Sending message to HCU: %s", message)
        await self._websocket.send_json(message)

    async def async_send_hmip_request(
        self, path: str, body: dict | None = None, timeout: int = API_REQUEST_TIMEOUT
    ) -> dict | None:
        """
        Send a command to the HCU and wait for the response.
        This is a core method that wraps a command in the required HMIP_SYSTEM_REQUEST
        envelope and handles the request-response correlation using a unique message ID.
        It also includes a retry mechanism for transient connection errors.
        """
        message_id = str(uuid4())
        message = {
            "type": "HMIP_SYSTEM_REQUEST",
            "pluginId": self.plugin_id,
            "id": message_id,
            "body": {"path": path, "body": body or {}},
        }

        last_exception = None

        for attempt in range(2):
            future = asyncio.get_running_loop().create_future()
            self._pending_requests[message_id] = future

            try:
                await self.async_send_message(message)
                return await asyncio.wait_for(future, timeout=timeout)

            except (
                ConnectionError,
                ConnectionAbortedError,
                asyncio.TimeoutError,
            ) as err:
                _LOGGER.warning(
                    "Request failed on attempt %d for path %s: %s", attempt + 1, path, err
                )
                last_exception = err
                self._pending_requests.pop(message_id, None)

                if attempt == 0:
                    await asyncio.sleep(API_RETRY_DELAY)

            except HcuApiError as err:
                _LOGGER.error("HCU returned an unrecoverable error for path %s.", path)
                self._pending_requests.pop(message_id, None)
                last_exception = err
                break

        raise HcuApiError(
            f"Request failed after multiple retries for path {path}"
        ) from last_exception

    async def get_system_state(self) -> dict:
        """
        Fetch complete system state from HCU.
        This is typically called once on startup to get the initial state
        of all devices, groups, and the home object.
        """
        response_body = await self.async_send_hmip_request(
            path=API_PATHS["GET_SYSTEM_STATE"], timeout=30
        )
        if response_body:
            self._state = response_body
            self._update_hcu_device_ids()
        return self._state

    def get_device_by_address(self, address: str) -> dict | None:
        """Retrieve device data from the local cache by SGTIN (device ID)."""
        if not self.is_connected and not self._state:
            _LOGGER.debug("Device lookup attempted while disconnected and no cached state")
        return self._state.get("devices", {}).get(address)

    def get_group_by_id(self, group_id: str) -> dict | None:
        """Retrieve group data from the local cache by group ID."""
        return self._state.get("groups", {}).get(group_id)

    def process_events(self, events: dict) -> set[str]:
        """
        Process push events from HCU and update local state cache.
        Returns a set of device/group IDs that were updated.
        """
        updated_ids = set()

        # Events are sorted by index to ensure they are processed in order.
        for event in sorted(events.values(), key=lambda e: e.get("index", 0)):
            event_type = event.get("pushEventType")

            if event_type == "DEVICE_CHANGED" and (device := event.get("device")):
                device_id = device["id"]

                # Merge partial updates into the existing device data.
                if self._state["devices"].get(device_id) and device.get(
                    "functionalChannels"
                ):
                    for ch_idx, ch_data in device["functionalChannels"].items():
                        self._state["devices"][device_id]["functionalChannels"][
                            ch_idx
                        ].update(ch_data)
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

    # ----------------------------------------------------------------
    # Generic Control Methods
    # ----------------------------------------------------------------
    async def async_device_control(
        self,
        path: str,
        device_id: str,
        channel_index: int,
        body: dict[str, Any] | None = None,
    ) -> None:
        """Generic method to send a control command to a specific device channel."""
        payload = {"deviceId": device_id, "channelIndex": channel_index}
        if body:
            payload.update(body)
        await self.async_send_hmip_request(path, payload)

    async def async_group_control(
        self, path: str, group_id: str, body: dict[str, Any] | None = None
    ) -> None:
        """Generic method to send a control command to a group."""
        payload = {"groupId": group_id}
        if body:
            payload.update(body)
        await self.async_send_hmip_request(path, payload)

    async def async_home_control(
        self, path: str, body: dict[str, Any] | None = None
    ) -> None:
        """Generic method to send a control command at home level."""
        await self.async_send_hmip_request(path, body or {})

    # ----------------------------------------------------------------
    # Specific Device Control Methods
    # ----------------------------------------------------------------
    async def async_set_switch_state(
        self, device_id: str, channel_index: int, is_on: bool
    ) -> None:
        await self.async_device_control(
            API_PATHS["SET_SWITCH_STATE"], device_id, channel_index, {"on": is_on}
        )

    async def async_set_watering_switch_state(
        self, device_id: str, channel_index: int, is_on: bool
    ) -> None:
        await self.async_device_control(
            API_PATHS["SET_WATERING_SWITCH_STATE"],
            device_id,
            channel_index,
            {"wateringActive": is_on},
        )

    async def async_set_dim_level(
        self, device_id: str, channel_index: int, dim_level: float
    ) -> None:
        await self.async_device_control(
            API_PATHS["SET_DIM_LEVEL"], device_id, channel_index, {"dimLevel": dim_level}
        )

    async def async_set_color_temperature(
        self, device_id: str, channel_index: int, color_temp: int, dim_level: float
    ) -> None:
        body = {"colorTemperature": color_temp, "dimLevel": dim_level}
        await self.async_device_control(
            API_PATHS["SET_COLOR_TEMP"], device_id, channel_index, body
        )

    async def async_set_hue_saturation(
        self,
        device_id: str,
        channel_index: int,
        hue: int,
        saturation: float,
        dim_level: float,
    ) -> None:
        body = {"hue": hue, "saturationLevel": saturation, "dimLevel": dim_level}
        await self.async_device_control(API_PATHS["SET_HUE"], device_id, channel_index, body)

    async def async_set_shutter_level(
        self, device_id: str, channel_index: int, shutter_level: float
    ) -> None:
        await self.async_device_control(
            API_PATHS["SET_SHUTTER_LEVEL"],
            device_id,
            channel_index,
            {"shutterLevel": shutter_level},
        )

    async def async_set_slats_level(
        self, device_id: str, channel_index: int, slats_level: float
    ) -> None:
        await self.async_device_control(
            API_PATHS["SET_SLATS_LEVEL"],
            device_id,
            channel_index,
            {"slatsLevel": slats_level},
        )

    async def async_stop_cover(self, device_id: str, channel_index: int) -> None:
        await self.async_device_control(API_PATHS["STOP_COVER"], device_id, channel_index)

    async def async_send_door_command(
        self, device_id: str, channel_index: int, command: str
    ) -> None:
        await self.async_device_control(
            API_PATHS["SEND_DOOR_COMMAND"], device_id, channel_index, {"doorCommand": command}
        )

    async def async_toggle_garage_door_state(
        self, device_id: str, channel_index: int
    ) -> None:
        await self.async_device_control(
            API_PATHS["TOGGLE_GARAGE_DOOR_STATE"], device_id, channel_index
        )

    async def async_set_lock_state(
        self, device_id: str, channel_index: int, state: str, pin: str
    ) -> None:
        body = {"targetLockState": state, "authorizationPin": pin}
        await self.async_device_control(
            API_PATHS["SET_LOCK_STATE"], device_id, channel_index, body
        )

    async def async_set_sound_file(
        self,
        device_id: str,
        channel_index: int,
        sound_file: str,
        volume: float,
        duration: float,
    ) -> None:
        """Play a sound file on a compatible device."""
        body = {"soundFile": sound_file, "volumeLevel": volume, "onTime": duration}
        await self.async_device_control(API_PATHS["SET_SOUND_FILE"], device_id, channel_index, body)

    async def async_reset_energy_counter(
        self, device_id: str, channel_index: int
    ) -> None:
        """Reset the energy counter for a specific device channel."""
        await self.async_device_control(
            API_PATHS["RESET_ENERGY_COUNTER"], device_id, channel_index
        )

    async def async_enable_simple_rule(self, rule_id: str, enabled: bool) -> None:
        """Enable or disable a simple rule (automation)."""
        await self.async_home_control(
            API_PATHS["ENABLE_SIMPLE_RULE"], {"ruleId": rule_id, "enabled": enabled}
        )

    async def async_set_epaper_display(
        self, device_id: str, channel_index: int, display_data: dict
    ) -> None:
        """Set the content of an e-paper display."""
        await self.async_device_control(
            API_PATHS["SET_EPAPER_DISPLAY"],
            device_id,
            channel_index,
            {"display": display_data},
        )

    # ----------------------------------------------------------------
    # Specific Group and Home Control Methods
    # ----------------------------------------------------------------
    async def async_set_group_boost(self, group_id: str, boost: bool) -> None:
        await self.async_group_control(API_PATHS["SET_GROUP_BOOST"], group_id, {"boost": boost})

    async def async_set_group_control_mode(self, group_id: str, mode: str) -> None:
        await self.async_group_control(
            API_PATHS["SET_GROUP_CONTROL_MODE"], group_id, {"controlMode": mode}
        )

    async def async_set_group_setpoint_temperature(self, group_id: str, temperature: float) -> None:
        """Set the target temperature for a heating group."""
        await self.async_group_control(
            API_PATHS["SET_GROUP_SET_POINT_TEMP"], group_id, {"setPointTemperature": temperature}
        )

    async def async_set_zones_activation(self, payload: dict) -> None:
        await self.async_home_control(API_PATHS["SET_ZONES_ACTIVATION"], payload)

    async def async_activate_vacation(self, temperature: float, end_time: str) -> None:
        """
        Activate vacation mode with a specific temperature and end time.
        
        Args:
            temperature: The temperature to maintain during vacation (typically eco temp)
            end_time: End time in format "YYYY_MM_DD HH:MM"
        """
        await self.async_home_control(
            API_PATHS["ACTIVATE_VACATION"],
            {
                "temperature": temperature,
                "endTime": end_time
            }
        )

    async def async_deactivate_vacation(self) -> None:
        """Deactivate vacation mode and return to normal heating schedules."""
        await self.async_home_control(API_PATHS["DEACTIVATE_VACATION"])

    async def disconnect(self) -> None:
        """Close the WebSocket connection gracefully."""
        if self.is_connected:
            _LOGGER.info("Closing WebSocket connection.")
            await self._websocket.close()
        self._websocket = None