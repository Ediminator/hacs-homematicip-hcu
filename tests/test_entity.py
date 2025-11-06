"""Tests for entity base classes."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.hcu_integration.entity import (
    HcuBaseEntity,
    HcuGroupBaseEntity,
    HcuHomeBaseEntity,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock()
    return coordinator


async def test_hcu_base_entity_initialization(mock_coordinator, mock_hcu_client, mock_device_data):
    """Test HcuBaseEntity initialization."""
    entity = HcuBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        device_data=mock_device_data,
        channel_index="1",
    )

    assert entity._client == mock_hcu_client
    assert entity._device_id == "test-device-id"
    assert entity._channel_index_str == "1"
    assert entity._channel_index == 1
    assert entity._attr_assumed_state is False


async def test_hcu_base_entity_device_info(mock_coordinator, mock_hcu_client, mock_device_data):
    """Test device_info property."""
    # Configure mock to return device data when entity accesses it
    mock_hcu_client.get_device_by_address = MagicMock(return_value=mock_device_data)

    entity = HcuBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        device_data=mock_device_data,
        channel_index="1",
    )

    device_info = entity.device_info
    assert device_info["identifiers"] == {("hcu_integration", "test-device-id")}
    assert device_info["name"] == "Test Device"
    assert device_info["model"] == "HMIP-PSM"


async def test_hcu_base_entity_set_entity_name_with_feature(mock_coordinator, mock_hcu_client, mock_device_data):
    """Test _set_entity_name with feature name."""
    entity = HcuBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        device_data=mock_device_data,
        channel_index="1",
    )

    entity._set_entity_name(channel_label="Test Channel", feature_name="Power Consumption")

    assert entity._attr_name == "Power Consumption"
    assert entity._attr_translation_key is None


async def test_hcu_base_entity_set_entity_name_without_feature(mock_coordinator, mock_hcu_client, mock_device_data):
    """Test _set_entity_name without feature name."""
    entity = HcuBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        device_data=mock_device_data,
        channel_index="1",
    )

    entity._set_entity_name(channel_label="Test Channel")

    assert entity._attr_name == "Test Channel"


async def test_hcu_group_base_entity_initialization(mock_coordinator, mock_hcu_client, mock_group_data):
    """Test HcuGroupBaseEntity initialization."""
    entity = HcuGroupBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        group_data=mock_group_data,
    )

    assert entity._client == mock_hcu_client
    assert entity._group_id == "test-group-id"
    assert entity._attr_assumed_state is False


async def test_hcu_group_base_entity_group_property(mock_coordinator, mock_hcu_client, mock_group_data):
    """Test _group property."""
    mock_hcu_client.get_group_by_id = MagicMock(return_value=mock_group_data)

    entity = HcuGroupBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        group_data=mock_group_data,
    )

    group = entity._group
    assert group == mock_group_data
    mock_hcu_client.get_group_by_id.assert_called_once_with("test-group-id")


async def test_hcu_group_base_entity_device_info(mock_coordinator, mock_hcu_client, mock_group_data):
    """Test device_info property for group entity."""
    mock_hcu_client.hcu_device_id = "hcu-device-id"

    entity = HcuGroupBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        group_data=mock_group_data,
    )

    device_info = entity.device_info
    assert device_info["identifiers"] == {("hcu_integration", "hcu-device-id")}


async def test_hcu_home_base_entity_initialization(mock_coordinator, mock_hcu_client):
    """Test HcuHomeBaseEntity initialization."""
    mock_hcu_client.hcu_device_id = "hcu-device-id"
    mock_hcu_client.state = {
        "home": {
            "id": "home-uuid",
        },
    }

    entity = HcuHomeBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
    )

    assert entity._client == mock_hcu_client
    assert entity._hcu_device_id == "hcu-device-id"
    assert entity._home_uuid == "home-uuid"
    assert entity._attr_assumed_state is False


async def test_hcu_home_base_entity_home_property(mock_coordinator, mock_hcu_client):
    """Test _home property."""
    home_data = {"id": "home-uuid", "currentAPVersion": "1.0.0"}
    mock_hcu_client.state = {"home": home_data}
    mock_hcu_client.hcu_device_id = "hcu-device-id"

    entity = HcuHomeBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
    )

    home = entity._home
    assert home == home_data


async def test_hcu_home_base_entity_device_info(mock_coordinator, mock_hcu_client):
    """Test device_info property for home entity."""
    mock_hcu_client.hcu_device_id = "hcu-device-id"
    mock_hcu_client.state = {"home": {"id": "home-uuid"}}

    entity = HcuHomeBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
    )

    device_info = entity.device_info
    assert device_info["identifiers"] == {("hcu_integration", "hcu-device-id")}


async def test_hcu_base_entity_available_when_connected(mock_coordinator, mock_hcu_client, mock_device_data):
    """Test entity availability when client is connected and device is reachable."""
    mock_hcu_client.is_connected = True
    mock_hcu_client.get_device_by_address = MagicMock(return_value={
        "id": "test-device-id",
        "functionalChannels": {
            "0": {"unreach": False},  # Maintenance channel must be reachable
            "1": {},
        },
    })

    entity = HcuBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        device_data=mock_device_data,
        channel_index="1",
    )

    assert entity.available is True


async def test_hcu_base_entity_unavailable_when_disconnected(mock_coordinator, mock_hcu_client, mock_device_data):
    """Test entity availability when client is disconnected."""
    mock_hcu_client.is_connected = False

    entity = HcuBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        device_data=mock_device_data,
        channel_index="1",
    )

    assert entity.available is False


async def test_hcu_base_entity_unavailable_when_device_unreachable(mock_coordinator, mock_hcu_client, mock_device_data):
    """Test entity availability when device is unreachable."""
    mock_hcu_client.is_connected = True
    mock_hcu_client.get_device_by_address = MagicMock(return_value={
        "id": "test-device-id",
        "functionalChannels": {
            "0": {"unreach": True},  # Maintenance channel reports unreachable
            "1": {},
        },
    })

    entity = HcuBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        device_data=mock_device_data,
        channel_index="1",
    )

    assert entity.available is False


async def test_hcu_base_entity_unavailable_when_device_not_found(mock_coordinator, mock_hcu_client, mock_device_data):
    """Test entity availability when device is not found in client state."""
    mock_hcu_client.is_connected = True
    mock_hcu_client.get_device_by_address = MagicMock(return_value=None)

    entity = HcuBaseEntity(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        device_data=mock_device_data,
        channel_index="1",
    )

    assert entity.available is False
