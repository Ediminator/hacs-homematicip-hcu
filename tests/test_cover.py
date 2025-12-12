"""Tests for the HCU Cover platform."""
from unittest.mock import AsyncMock, MagicMock
from pytest import approx
import pytest

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntityFeature,
)

from custom_components.hcu_integration.cover import HcuCover, HcuCoverGroup
from custom_components.hcu_integration.const import API_PATHS

@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock()
    return coordinator

@pytest.fixture
def mock_hcu_client():
    """Create a mock HCU client."""
    client = MagicMock()
    return client

async def test_cover_group_properties_shutter(mock_coordinator, mock_hcu_client):
    """Test cover group position reading (SHUTTER)."""
    group_data = {
        "id": "group-id",
        "type": "SHUTTER",
        "label": "Test Shutter Group",
        "primaryShadingLevel": 0.0, # Open
        "shutterLevel": 0.5, # Should be ignored
    }
    
    mock_hcu_client.get_group_by_id = MagicMock(return_value=group_data)

    cover = HcuCoverGroup(mock_coordinator, mock_hcu_client, group_data)
    
    # Verify device class is SHUTTER
    assert cover.device_class == CoverDeviceClass.SHUTTER
    
    # Check initial position
    assert cover.current_cover_position == 100 
    
    # Update data
    group_data["primaryShadingLevel"] = 0.5
    assert cover.current_cover_position == 50
    
    group_data["primaryShadingLevel"] = 1.0 # Closed
    assert cover.current_cover_position == 0
    assert cover.is_closed is True

async def test_cover_group_properties_blind(mock_coordinator, mock_hcu_client):
    """Test cover group position and tilt reading (BLIND)."""
    group_data = {
        "id": "group-id",
        "type": "BLIND",
        "label": "Test Blind Group",
        "primaryShadingLevel": 0.25,
        "secondaryShadingLevel": 0.75,
        "shutterLevel": 0.0, # Should be ignored
    }
    
    mock_hcu_client.get_group_by_id = MagicMock(return_value=group_data)

    cover = HcuCoverGroup(mock_coordinator, mock_hcu_client, group_data)
    
    # Verify supported features include all TILT capabilities
    assert cover.supported_features & CoverEntityFeature.SET_TILT_POSITION
    assert cover.supported_features & CoverEntityFeature.OPEN_TILT
    assert cover.supported_features & CoverEntityFeature.CLOSE_TILT
    assert cover.supported_features & CoverEntityFeature.STOP_TILT
    
    # Verify device class is BLIND
    assert cover.device_class == CoverDeviceClass.BLIND

    # 0.25 level = 75% open
    assert cover.current_cover_position == 75
    
    # 0.75 level = 25% open (tilt)
    assert cover.current_cover_tilt_position == 25

async def test_cover_device_rounding(mock_coordinator, mock_hcu_client):
    """Test rounding logic for single devices."""
    device_data = {
        "id": "device-id",
        "type": "HMIP-BROLL",
        "functionalChannels": {
            "1": {
                "label": "Shutter Channel",
                "shutterLevel": 0.004, # 0.4% -> Should round to 0% closed -> 100% open
            }
        }
    }
    
    mock_hcu_client.get_device_by_address = MagicMock(return_value=device_data)
    
    # Test 1: 0.4% level -> 99.6% open -> round to 100
    # 0.004 level means (1 - 0.004) * 100 = 0.996 * 100 = 99.6 -> round(99.6) = 100
    cover = HcuCover(mock_coordinator, mock_hcu_client, device_data, "1")
    assert cover.current_cover_position == 100
    
    # Test 2: 0.6% level -> 99.4% open -> round to 99
    # 0.006 level means (1 - 0.006) * 100 = 0.994 * 100 = 99.4 -> round(99.4) = 99
    device_data["functionalChannels"]["1"]["shutterLevel"] = 0.006
    assert cover.current_cover_position == 99

async def test_cover_group_rounding(mock_coordinator, mock_hcu_client):
    """Test rounding logic for groups."""
    group_data = {
        "id": "group-id",
        "type": "SHUTTER",
        "primaryShadingLevel": 0.004, # 0.4% -> 99.6% open -> 100
    }
    
    mock_hcu_client.get_group_by_id = MagicMock(return_value=group_data)

    cover = HcuCoverGroup(mock_coordinator, mock_hcu_client, group_data)
    assert cover.current_cover_position == 100
    
    group_data["primaryShadingLevel"] = 0.006 # 0.6% -> 99.4% open -> 99
    assert cover.current_cover_position == 99

async def test_cover_tilt_rounding(mock_coordinator, mock_hcu_client):
    """Test rounding logic for tilt (device)."""
    device_data = {
        "id": "device-id",
        "type": "HMIP-BBL", # Blind
        "functionalChannels": {
            "1": {
                "label": "Blind Channel",
                "shutterLevel": 0.0,
                "slatsLevel": 0.505, # 50.5% -> 49.5% open -> round to 50
            }
        }
    }
    mock_hcu_client.get_device_by_address = MagicMock(return_value=device_data)
    
    cover = HcuCover(mock_coordinator, mock_hcu_client, device_data, "1")
    
    # (1 - 0.505) * 100 = 0.495 * 100 = 49.5 -> round(49.5) = 50 
    # (Note: python 3 rounds to nearest even number for .5 constraints, so 49.5 -> 50, 50.5 -> 50)
    # Let's check a clear case: 0.506 -> 0.494 * 100 = 49.4 -> 49
    
    assert cover.current_cover_tilt_position == 50
    
    device_data["functionalChannels"]["1"]["slatsLevel"] = 0.506
    assert cover.current_cover_tilt_position == 49

async def test_cover_device_blind_class(mock_coordinator, mock_hcu_client):
    """Test device class detection for blind devices."""
    device_data = {
        "id": "device-id",
        "type": "HMIP-BBL", # Blind
        "functionalChannels": {
            "1": {
                "label": "Blind Channel",
                "shutterLevel": 0.0,
                "slatsLevel": 0.0,
            }
        }
    }
    
    mock_hcu_client.get_device_by_address = MagicMock(return_value=device_data)
    
    cover = HcuCover(mock_coordinator, mock_hcu_client, device_data, "1")
    
    assert cover.device_class == CoverDeviceClass.BLIND
    assert cover.supported_features & CoverEntityFeature.SET_TILT_POSITION
