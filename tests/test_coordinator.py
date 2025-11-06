"""Tests for the HCU coordinator."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.hcu_integration import HcuCoordinator
from custom_components.hcu_integration.const import DOMAIN, EVENT_CHANNEL_TYPES


@pytest.fixture
async def coordinator(hass: HomeAssistant, mock_hcu_client: MagicMock, mock_config_entry: ConfigEntry):
    """Create a coordinator instance."""
    coordinator = HcuCoordinator(hass, mock_hcu_client, mock_config_entry)
    return coordinator


def test_coordinator_initialization(coordinator: HcuCoordinator, mock_hcu_client: MagicMock):
    """Test coordinator initialization."""
    assert coordinator.client == mock_hcu_client
    assert coordinator.entities == {}


def test_extract_event_channels(coordinator: HcuCoordinator):
    """Test extraction of event channels from events."""
    events = {
        "event1": {
            "pushEventType": "DEVICE_CHANGED",
            "device": {
                "id": "device1",
                "functionalChannels": {
                    "1": {"functionalChannelType": "WALL_MOUNTED_TRANSMITTER_CHANNEL"},
                    "2": {"functionalChannelType": "SWITCH_MEASURING"},
                },
            },
        },
    }

    result = coordinator._extract_event_channels(events)

    # WALL_MOUNTED_TRANSMITTER_CHANNEL should be extracted (it's an event channel type)
    assert ("device1", "1") in result
    # SWITCH_MEASURING should not be extracted (not an event channel type)
    assert ("device1", "2") not in result


async def test_fire_button_event(coordinator: HcuCoordinator, hass: HomeAssistant):
    """Test firing a button event."""
    events_fired = []

    def capture_event(event):
        events_fired.append(event)

    hass.bus.async_listen(f"{DOMAIN}_event", capture_event)

    coordinator._fire_button_event("device1", "1", "press")
    await hass.async_block_till_done()

    assert len(events_fired) == 1
    event = events_fired[0]
    assert event.data["device_id"] == "device1"
    assert event.data["channel"] == "1"
    assert event.data["type"] == "press"


async def test_handle_device_channel_events(coordinator: HcuCoordinator, hass: HomeAssistant):
    """Test handling DEVICE_CHANNEL_EVENT type events."""
    events_fired = []

    def capture_event(event):
        events_fired.append(event)

    hass.bus.async_listen(f"{DOMAIN}_event", capture_event)

    events = {
        "event1": {
            "pushEventType": "DEVICE_CHANNEL_EVENT",
            "channelEventType": "PRESS_SHORT",
            "deviceId": "device1",
            "functionalChannelIndex": "1",
        },
    }

    coordinator._handle_device_channel_events(events)
    await hass.async_block_till_done()

    assert len(events_fired) == 1
    event = events_fired[0]
    assert event.data["device_id"] == "device1"
    assert event.data["channel"] == "1"
    assert event.data["type"] == "PRESS_SHORT"


def test_should_fire_button_press_timestamp_changed(coordinator: HcuCoordinator):
    """Test button press detection when timestamp changes."""
    should_fire, reason = coordinator._should_fire_button_press(1000, 900)
    assert should_fire is True
    assert reason == "timestamp change"


def test_should_fire_button_press_stateless(coordinator: HcuCoordinator):
    """Test button press detection for stateless channels."""
    should_fire, reason = coordinator._should_fire_button_press(None, None)
    assert should_fire is True
    assert reason == "stateless channel"


def test_should_fire_button_press_no_change(coordinator: HcuCoordinator):
    """Test button press detection when timestamp hasn't changed."""
    should_fire, reason = coordinator._should_fire_button_press(1000, 1000)
    assert should_fire is False
    assert reason == ""


async def test_detect_timestamp_based_button_presses(coordinator: HcuCoordinator, hass: HomeAssistant):
    """Test timestamp-based button press detection."""
    events_fired = []

    def capture_event(event):
        events_fired.append(event)

    hass.bus.async_listen(f"{DOMAIN}_event", capture_event)

    # Setup mock device data
    device_data = {
        "id": "device1",
        "functionalChannels": {
            "1": {
                "functionalChannelType": "WALL_MOUNTED_TRANSMITTER_CHANNEL",
                "lastStatusUpdate": 2000,
            },
        },
    }

    coordinator.client.get_device_by_address = MagicMock(return_value=device_data)

    old_state = {
        "device1": {
            "1": 1000,  # Old timestamp
        }
    }

    event_channels = {("device1", "1")}
    updated_ids = {"device1"}

    coordinator._detect_timestamp_based_button_presses(updated_ids, event_channels, old_state)
    await hass.async_block_till_done()

    assert len(events_fired) == 1
    event = events_fired[0]
    assert event.data["device_id"] == "device1"
    assert event.data["type"] == "press"


async def test_handle_event_message_full_flow(coordinator: HcuCoordinator, hass: HomeAssistant):
    """Test complete event message handling flow."""
    events_fired = []

    def capture_event(event):
        events_fired.append(event)

    hass.bus.async_listen(f"{DOMAIN}_event", capture_event)

    # Setup mock client state
    coordinator.client.state = {
        "devices": {
            "device1": {
                "functionalChannels": {
                    "1": {
                        "functionalChannelType": "WALL_MOUNTED_TRANSMITTER_CHANNEL",
                        "lastStatusUpdate": 1000,
                    },
                },
            },
        },
    }

    coordinator.client.process_events = MagicMock(return_value={"device1"})

    updated_device = {
        "id": "device1",
        "functionalChannels": {
            "1": {
                "functionalChannelType": "WALL_MOUNTED_TRANSMITTER_CHANNEL",
                "lastStatusUpdate": 2000,  # Timestamp changed
            },
        },
    }
    coordinator.client.get_device_by_address = MagicMock(return_value=updated_device)

    # Simulate receiving an event message
    message = {
        "type": "HMIP_SYSTEM_EVENT",
        "body": {
            "eventTransaction": {
                "events": {
                    "event1": {
                        "pushEventType": "DEVICE_CHANGED",
                        "device": updated_device,
                    },
                },
            },
        },
    }

    coordinator._handle_event_message(message)
    await hass.async_block_till_done()

    # Should fire exactly one event for timestamp change
    assert len(events_fired) == 1


def test_handle_event_message_ignores_non_event_types(coordinator: HcuCoordinator):
    """Test that non-HMIP_SYSTEM_EVENT messages are ignored."""
    message = {"type": "OTHER_TYPE", "body": {}}

    # Should not raise an error
    coordinator._handle_event_message(message)


def test_handle_event_message_empty_events(coordinator: HcuCoordinator):
    """Test handling message with no events."""
    message = {
        "type": "HMIP_SYSTEM_EVENT",
        "body": {
            "eventTransaction": {
                "events": {},
            },
        },
    }

    # Should not raise an error
    coordinator._handle_event_message(message)
