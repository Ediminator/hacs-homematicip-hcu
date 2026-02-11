import pytest
from unittest.mock import MagicMock, call
from homeassistant.core import HomeAssistant
from custom_components.hcu_integration import HcuCoordinator
from custom_components.hcu_integration.const import (
    EVENT_CHANNEL_TYPES,
    DEVICE_CHANNEL_EVENT_ONLY_TYPES,
)

async def test_issue_183_channel_exclusion(hass: HomeAssistant):
    """Test that HmIP-FCI6 channels are correctly excluded from event extraction."""
    
    # Verify constants setup
    # HmIP-FCI6 uses MULTI_MODE_INPUT_CHANNEL
    # It SHOULD be in DEVICE_CHANNEL_EVENT_ONLY_TYPES
    # It SHOULD NOT be in EVENT_CHANNEL_TYPES
    assert "MULTI_MODE_INPUT_CHANNEL" in DEVICE_CHANNEL_EVENT_ONLY_TYPES
    assert "MULTI_MODE_INPUT_CHANNEL" not in EVENT_CHANNEL_TYPES
    
    # Setup Coordinator
    entry = MagicMock()
    entry.options = {}
    client = MagicMock()
    
    coordinator = HcuCoordinator(hass, client, entry)
    
    # Payload simulating HmIP-FCI6 update
    # This payload typically comes from a DEVICE_CHANGED event
    events = {
        "event_1": {
            "pushEventType": "DEVICE_CHANGED",
            "device": {
                "id": "3014F711A0001F20C98F2F47",
                "type": "HmIP-FCI6",
                "functionalChannels": {
                    "1": {
                        "functionalChannelType": "MULTI_MODE_INPUT_CHANNEL",
                        "label": "001_Tasteingang1"
                    }
                }
            }
        }
    }
    
    # Run extraction logic
    event_channels = coordinator._extract_event_channels(events)
    
    # Assert that NO channels were extracted for timestamp-based detection
    assert event_channels == set(), "HmIP-FCI6 channels should be excluded from timestamp detection!"

async def test_startup_safeguard(hass: HomeAssistant):
    """Test that events are ignored until initial state is loaded."""
    entry = MagicMock()
    entry.options = {}
    client = MagicMock()
    coordinator = HcuCoordinator(hass, client, entry)

    # Mock dependent methods to track calls and avoid side effects
    coordinator._handle_device_channel_events = MagicMock(return_value=set())
    coordinator._extract_event_channels = MagicMock(return_value=set())
    coordinator._detect_timestamp_based_button_presses = MagicMock()
    coordinator.async_set_updated_data = MagicMock()
    
    # Mock client methods
    coordinator.client.process_events = MagicMock(return_value=set())
    # Mock state access for old_timestamps calculation
    coordinator.client.state = {"devices": {}}

    events_payload = {
        "dummy_event": {"pushEventType": "DEVICE_CHANGED"}
    }
    msg_system_event = {
        "type": "HMIP_SYSTEM_EVENT",
        "body": {
            "eventTransaction": {
                "events": events_payload
            }
        }
    }

    # Case 1: Wrong Event Type
    msg_other = {"type": "OTHER_EVENT", "body": {}}
    coordinator._handle_event_message(msg_other)
    coordinator._handle_device_channel_events.assert_not_called()

    # Case 2: Initial state NOT loaded
    coordinator._initial_state_loaded = False
    coordinator._handle_event_message(msg_system_event)
    coordinator._handle_device_channel_events.assert_not_called()

    # Case 3: Initial state LOADED
    coordinator._initial_state_loaded = True
    coordinator._handle_event_message(msg_system_event)
    
    # Assert methods WERE called with CORRECT arguments
    coordinator._handle_device_channel_events.assert_called_once_with(events_payload)
    coordinator.client.process_events.assert_called_once_with(events_payload)

    # Case 4: No events in payload
    coordinator._handle_device_channel_events.reset_mock()
    msg_empty = {
        "type": "HMIP_SYSTEM_EVENT",
        "body": {
            "eventTransaction": {
                "events": {}
            }
        }
    }
    coordinator._handle_event_message(msg_empty)
    # Should return early before processing
    coordinator._handle_device_channel_events.assert_not_called()
