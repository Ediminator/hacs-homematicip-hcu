import pytest
from unittest.mock import MagicMock
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
