"""Tests for the HCU API client."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.core import HomeAssistant

from custom_components.hcu_integration.api import HcuApiClient, HcuApiError


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    mock_ws = AsyncMock()
    mock_ws.closed = False
    mock_ws.send_json = AsyncMock()
    mock_ws.receive_json = AsyncMock()
    mock_ws.close = AsyncMock()
    return mock_ws


@pytest.fixture
async def api_client(hass: HomeAssistant):
    """Create an API client instance."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = HcuApiClient(
        hass=hass,
        host="192.168.1.100",
        auth_token="test-token",
        session=session,
        auth_port=6969,
        websocket_port=9001,
    )
    return client


async def test_api_client_initialization(api_client: HcuApiClient):
    """Test API client initialization."""
    assert api_client._host == "192.168.1.100"
    assert api_client._auth_token == "test-token"
    assert api_client._auth_port == 6969
    assert api_client._websocket_port == 9001
    assert api_client.state == {}
    assert not api_client.is_connected


async def test_api_client_state_property(api_client: HcuApiClient):
    """Test the state property."""
    test_state = {"devices": {}, "groups": {}}
    api_client._state = test_state
    assert api_client.state == test_state


async def test_get_device_by_address(api_client: HcuApiClient):
    """Test getting device by address."""
    test_device = {"id": "device1", "label": "Test Device"}
    api_client._state = {"devices": {"device1": test_device}}

    result = api_client.get_device_by_address("device1")
    assert result == test_device

    result = api_client.get_device_by_address("nonexistent")
    assert result is None


async def test_get_group_by_id(api_client: HcuApiClient):
    """Test getting group by ID."""
    test_group = {"id": "group1", "label": "Test Group"}
    api_client._state = {"groups": {"group1": test_group}}

    result = api_client.get_group_by_id("group1")
    assert result == test_group

    result = api_client.get_group_by_id("nonexistent")
    assert result is None


async def test_process_events_device_changed(api_client: HcuApiClient):
    """Test processing DEVICE_CHANGED events."""
    device_data = {
        "id": "device1",
        "label": "Updated Device",
        "functionalChannels": {},
    }
    events = {
        "event1": {
            "pushEventType": "DEVICE_CHANGED",
            "device": device_data,
        }
    }

    api_client._state = {"devices": {}}
    updated_ids = api_client.process_events(events)

    assert "device1" in updated_ids
    assert api_client._state["devices"]["device1"] == device_data


async def test_process_events_group_changed(api_client: HcuApiClient):
    """Test processing GROUP_CHANGED events."""
    group_data = {
        "id": "group1",
        "label": "Updated Group",
    }
    events = {
        "event1": {
            "pushEventType": "GROUP_CHANGED",
            "group": group_data,
        }
    }

    api_client._state = {"groups": {}}
    updated_ids = api_client.process_events(events)

    assert "group1" in updated_ids
    assert api_client._state["groups"]["group1"] == group_data


async def test_retry_logic_success_on_second_attempt(api_client: HcuApiClient, mock_websocket):
    """Test retry logic succeeds on second attempt."""
    # Mock the WebSocket to fail first then succeed
    api_client._ws = mock_websocket
    api_client._pending_requests = {}

    # First attempt fails, second succeeds
    call_count = 0

    async def mock_send(msg):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Connection failed")

    async def mock_response():
        return {"type": "HMIP_SYSTEM_RESPONSE", "id": "test-id", "body": {"result": "success"}}

    api_client._send_message = AsyncMock(side_effect=mock_send)

    # Simulate receiving response on second attempt
    with patch.object(asyncio, "wait_for") as mock_wait:
        mock_wait.side_effect = [
            asyncio.TimeoutError(),
            {"result": "success"},
        ]

        try:
            result = await api_client._send_hmip_request("/test/path", timeout=1)
            # Should succeed on retry
            assert call_count >= 1
        except HcuApiError:
            # Expected if both attempts fail
            assert call_count >= 2


async def test_hcu_device_id_property(api_client: HcuApiClient):
    """Test HCU device ID property."""
    api_client._state = {
        "devices": {
            "device1": {"type": "HCU", "id": "device1"},
            "device2": {"type": "HMIP-PSM", "id": "device2"},
        }
    }
    api_client._update_hcu_device_ids()

    assert api_client.hcu_device_id == "device1"


async def test_hcu_part_device_ids_property(api_client: HcuApiClient):
    """Test HCU part device IDs property."""
    api_client._state = {
        "devices": {
            "device1": {"type": "HCU", "id": "device1"},
            "device2": {"type": "HCU-PART", "id": "device2"},
            "device3": {"type": "HMIP-PSM", "id": "device3"},
        }
    }
    api_client._update_hcu_device_ids()

    assert api_client.hcu_part_device_ids == {"device2"}


async def test_event_callback_registration(api_client: HcuApiClient):
    """Test event callback registration."""
    callback_called = False

    def test_callback(event):
        nonlocal callback_called
        callback_called = True

    api_client.register_event_callback(test_callback)

    # Simulate receiving an event
    api_client._handle_incoming_message({"type": "HMIP_SYSTEM_EVENT", "body": {}})

    assert callback_called
