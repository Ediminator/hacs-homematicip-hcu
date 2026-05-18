"""Bridge to expose selected Home Assistant entities to the HCU as plugin devices."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Awaitable
from uuid import uuid4

from homeassistant.const import (
    STATE_ON, STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN,
    ATTR_FRIENDLY_NAME,
)
from homeassistant.components.light import ATTR_BRIGHTNESS
from homeassistant.core import HomeAssistant, State, callback

_LOGGER = logging.getLogger(__name__)

STATUS_EVENT_THROTTLE_SECONDS = 5.0

SENSOR_CLASS_TO_PROPERTY: dict[str, str] = {
    "temperature": "ActualTemperature",
    "humidity": "Humidity",
    "illuminance": "Illumination",
    "power": "PowerConsumption",
    "energy": "EnergyCounter",
    "co2": "Co2Concentration",
    "carbon_dioxide": "Co2Concentration",
    "carbon_monoxide": "COConcentration",
    "pressure": "AirPressure",
    "battery": "BatteryLevel",
    "voltage": "Voltage",
    "current": "Current",
    "pm25": "PM2_5",
    "pm10": "PM10",
    "moisture": "Humidity",
    "power_factor": "PowerFactor",
    "frequency": "Frequency",
    "apparent_power": "ApparentPower",
    "reactive_power": "ReactivePower",
    "gas": "GasVolume",
    "water": "WaterVolume",
    "wind_speed": "WindSpeed",
    "precipitation": "TodayRainCounter",
}

HA_ENTITY_PREFIX = "ha."


class HaEntityBridge:
    """Bridges selected HA entities to the HCU plugin protocol."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_ids: list[str],
        send_message_fn: Callable[[dict[str, Any]], Awaitable[None]],
        plugin_id: str,
    ) -> None:
        self.hass = hass
        self.entity_ids: set[str] = set(entity_ids)
        self._send_message = send_message_fn
        self._plugin_id = plugin_id
        self._unsub: Callable | None = None
        self._last_sent: dict[str, float] = {}

    # --- Device ID helpers ---

    @staticmethod
    def entity_to_device_id(entity_id: str) -> str:
        """Convert a HA entity_id to a HCU plugin deviceId."""
        return f"{HA_ENTITY_PREFIX}{entity_id}"

    @staticmethod
    def device_to_entity_id(device_id: str) -> str | None:
        """Convert a HCU plugin deviceId back to a HA entity_id."""
        if device_id.startswith(HA_ENTITY_PREFIX):
            return device_id[len(HA_ENTITY_PREFIX):]
        return None

    def is_ha_device(self, device_id: str) -> bool:
        """Return True if device_id belongs to a managed HA entity."""
        entity_id = self.device_to_entity_id(device_id)
        return entity_id is not None and entity_id in self.entity_ids

    # --- Discovery ---

    def build_discover_devices(self) -> list[dict[str, Any]]:
        """Build the device list for DISCOVER_RESPONSE."""
        devices = []
        for entity_id in sorted(self.entity_ids):
            state = self.hass.states.get(entity_id)
            label = (
                (state.attributes.get(ATTR_FRIENDLY_NAME) if state else None)
                or entity_id
            )
            domain = entity_id.split(".")[0]
            device_id = self.entity_to_device_id(entity_id)

            if domain == "switch":
                devices.append({
                    "deviceId": device_id,
                    "label": label,
                    "deviceType": "SWITCH",
                    "features": ["SWITCHING"],
                    "groups": [],
                })
            elif domain == "light":
                devices.append({
                    "deviceId": device_id,
                    "label": label,
                    "deviceType": "DIMMER",
                    "features": ["SWITCHING", "DIMMING"],
                    "groups": [],
                })
            elif domain == "sensor":
                device_class = (state.attributes.get("device_class") if state else None) or ""
                prop_type = SENSOR_CLASS_TO_PROPERTY.get(device_class, "ActualTemperature")
                devices.append({
                    "deviceId": device_id,
                    "label": label,
                    "deviceType": "TEMPERATURE_HUMIDITY_SENSOR",
                    "features": [prop_type],
                    "groups": [],
                })
        return devices

    # --- Status ---

    def build_status_devices(
        self, entity_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Build device status list for STATUS_RESPONSE or STATUS_EVENT."""
        targets = entity_ids if entity_ids is not None else sorted(self.entity_ids)
        result = []
        for entity_id in targets:
            if entity_id not in self.entity_ids:
                continue
            state = self.hass.states.get(entity_id)
            if state is None:
                continue
            domain = entity_id.split(".")[0]
            properties = self._state_to_properties(domain, state)
            if properties:
                result.append({
                    "deviceId": self.entity_to_device_id(entity_id),
                    "properties": properties,
                })
        return result

    def _state_to_properties(
        self, domain: str, state: State
    ) -> list[dict[str, Any]]:
        if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return []

        props: list[dict[str, Any]] = []

        if domain == "switch":
            props.append({
                "propertyType": "SwitchState",
                "value": "true" if state.state == STATE_ON else "false",
            })

        elif domain == "light":
            is_on = state.state == STATE_ON
            props.append({
                "propertyType": "SwitchState",
                "value": "true" if is_on else "false",
            })
            if is_on:
                brightness = state.attributes.get(ATTR_BRIGHTNESS)
                if brightness is not None:
                    props.append({
                        "propertyType": "DimLevel",
                        "value": str(round(brightness / 255, 4)),
                    })

        elif domain == "sensor":
            device_class = state.attributes.get("device_class") or ""
            prop_type = SENSOR_CLASS_TO_PROPERTY.get(device_class, "ActualTemperature")
            try:
                props.append({
                    "propertyType": prop_type,
                    "value": str(float(state.state)),
                })
            except (ValueError, TypeError):
                pass

        return props

    # --- Control ---

    async def handle_control_request(self, body: dict[str, Any]) -> None:
        """Execute a ControlRequest targeting an HA entity."""
        device_id = body.get("deviceId", "")
        entity_id = self.device_to_entity_id(device_id)
        if not entity_id or entity_id not in self.entity_ids:
            return

        domain = entity_id.split(".")[0]
        properties: list[dict[str, Any]] = body.get("properties", [])

        for prop in properties:
            prop_type = prop.get("propertyType")
            value = prop.get("value")

            if prop_type == "SwitchState":
                service = "turn_on" if value == "true" else "turn_off"
                await self.hass.services.async_call(
                    domain, service, {"entity_id": entity_id}, blocking=False
                )
            elif prop_type == "DimLevel" and domain == "light":
                try:
                    brightness = int(float(value) * 255)
                    await self.hass.services.async_call(
                        "light",
                        "turn_on",
                        {"entity_id": entity_id, "brightness": brightness},
                        blocking=False,
                    )
                except (ValueError, TypeError):
                    _LOGGER.warning("Invalid DimLevel value: %s", value)

    # --- Status Event ---

    async def send_status_event(self, entity_ids: list[str] | None = None) -> None:
        """Push current HA entity states to the HCU as a STATUS_EVENT."""
        devices = self.build_status_devices(entity_ids)
        if not devices:
            return
        try:
            await self._send_message({
                "id": str(uuid4()),
                "pluginId": self._plugin_id,
                "type": "STATUS_EVENT",
                "body": {"devices": devices},
            })
        except ConnectionError:
            pass

    # --- State listener ---

    def start_listening(self) -> None:
        """Subscribe to HA state_changed events for managed entities."""
        if not self.entity_ids:
            return

        @callback
        def _on_state_changed(event: Any) -> None:
            entity_id = event.data.get("entity_id")
            if entity_id not in self.entity_ids:
                return
            now = time.monotonic()
            if now - self._last_sent.get(entity_id, 0) < STATUS_EVENT_THROTTLE_SECONDS:
                return
            self._last_sent[entity_id] = now
            self.hass.async_create_task(
                self.send_status_event([entity_id]),
                name=f"HCU status_event {entity_id}",
            )

        self._unsub = self.hass.bus.async_listen("state_changed", _on_state_changed)
        _LOGGER.debug("HaEntityBridge: listening to %d entities", len(self.entity_ids))

    def stop_listening(self) -> None:
        """Unsubscribe from HA state changes."""
        if self._unsub:
            self._unsub()
            self._unsub = None
