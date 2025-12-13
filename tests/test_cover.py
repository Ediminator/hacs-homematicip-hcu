"""Tests for the HCU Cover platform."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverDeviceClass,
    CoverEntityFeature,
)

from custom_components.hcu_integration.cover import HcuCover, HcuCoverGroup, TILT_FEATURES
from custom_components.hcu_integration.const import API_PATHS

# Feature constants for test assertions
BASIC_COVER_FEATURES = (
    CoverEntityFeature.OPEN
    | CoverEntityFeature.CLOSE
    | CoverEntityFeature.STOP
    | CoverEntityFeature.SET_POSITION
)


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

@pytest.mark.parametrize(
    "level, expected_position",
    [
        (0.004, 100),  # (1 - 0.004) * 100 = 99.6 -> round(99.6) = 100
        (0.006, 99),   # (1 - 0.006) * 100 = 99.4 -> round(99.4) = 99
    ],
)
async def test_cover_device_rounding(
    mock_coordinator, mock_hcu_client, level, expected_position
):
    """Test rounding logic for single devices."""
    device_data = {
        "id": "device-id",
        "type": "HMIP-BROLL",
        "functionalChannels": {
            "1": {
                "label": "Shutter Channel",
                "shutterLevel": level,
            }
        },
    }

    mock_hcu_client.get_device_by_address = MagicMock(return_value=device_data)

    cover = HcuCover(mock_coordinator, mock_hcu_client, device_data, "1")
    assert cover.current_cover_position == expected_position

@pytest.mark.parametrize(
    "level, expected_position",
    [
        (0.004, 100),  # 0.4% -> 99.6% open -> 100
        (0.006, 99),   # 0.6% -> 99.4% open -> 99
    ],
)
async def test_cover_group_rounding(
    mock_coordinator, mock_hcu_client, level, expected_position
):
    """Test rounding logic for groups."""
    group_data = {
        "id": "group-id",
        "type": "SHUTTER",
        "primaryShadingLevel": level,
    }

    mock_hcu_client.get_group_by_id = MagicMock(return_value=group_data)

    cover = HcuCoverGroup(mock_coordinator, mock_hcu_client, group_data)
    assert cover.current_cover_position == expected_position

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

async def test_cover_device_tilt_passes_shutter_level(mock_coordinator, mock_hcu_client):
    """Test that setting tilt position passes the current shutter level."""
    # Setup device using primaryShadingLevel to verify dynamic property usage
    device_data = {
        "id": "device-id",
        "type": "HMIP-BBL", 
        "functionalChannels": {
            "1": {
                "label": "Blind Channel",
                "primaryShadingLevel": 0.4, # 40% closed (60% open)
                "slatsLevel": 0.0,
            }
        }
    }
    
    mock_hcu_client.async_set_slats_level = AsyncMock()
    mock_hcu_client.get_device_by_address = MagicMock(return_value=device_data)
    
    cover = HcuCover(mock_coordinator, mock_hcu_client, device_data, "1")
    
    # Verify level property detection
    assert cover._level_property == "primaryShadingLevel"
    
    # Set tilt to 50% (0.5 level)
    await cover.async_set_cover_tilt_position(tilt_position=50)
    
    # Check if async_set_slats_level was called with correct shutter_level
    mock_hcu_client.async_set_slats_level.assert_called_once_with(
        "device-id", 1, 0.5, shutter_level=0.4
    )


async def test_cover_group_with_none_secondary_shading_level(mock_coordinator, mock_hcu_client):
    """Test that groups with secondaryShadingLevel=None are classified as SHUTTER.

    This tests the fix for issue #207: BROLL-only groups were incorrectly imported
    as blinds because the API returns secondaryShadingLevel key with None value
    for groups without tilt support.
    """
    group_data = {
        "id": "group-id",
        "type": "SHUTTER",
        "label": "BROLL Group",
        "primaryShadingLevel": 0.0,
        "secondaryShadingLevel": None,  # Key present but None - no tilt support
    }

    mock_hcu_client.get_group_by_id = MagicMock(return_value=group_data)

    cover = HcuCoverGroup(mock_coordinator, mock_hcu_client, group_data)

    # Verify device class is SHUTTER (not BLIND)
    assert cover.device_class == CoverDeviceClass.SHUTTER

    # Verify basic cover features are supported
    assert cover.supported_features == BASIC_COVER_FEATURES

    # Verify tilt position returns None
    assert cover.current_cover_tilt_position is None

    # Verify position still works correctly
    assert cover.current_cover_position == 100  # 0.0 level = fully open


async def test_cover_device_with_none_slats_level(mock_coordinator, mock_hcu_client):
    """Test that devices with slatsLevel=None are reclassified from BLIND to SHUTTER.

    This tests the fix for issue #207: HmIPW-DRBL4 devices were incorrectly
    displayed as blinds because the API returns slatsLevel key with None value
    for channels without tilt/slats configured. Devices initially classified as
    BLIND (from device type mapping) but without actual tilt support should be
    reclassified as SHUTTER.
    """
    device_data = {
        "id": "device-id",
        "type": "WIRED_DIN_RAIL_BLIND_4",  # Mapped to BLIND in const.py
        "label": "02_DRBL4",
        "functionalChannels": {
            "1": {
                "label": "Channel 1",
                "functionalChannelType": "BLIND_CHANNEL",
                "shutterLevel": 0.5,
                "slatsLevel": None,  # Key present but None - no tilt configured
                "slatsReferenceTime": 0.0,
            }
        },
    }

    mock_hcu_client.get_device_by_address = MagicMock(return_value=device_data)

    cover = HcuCover(mock_coordinator, mock_hcu_client, device_data, "1")

    # Verify device class is SHUTTER (reclassified from BLIND due to no tilt support)
    assert cover.device_class == CoverDeviceClass.SHUTTER

    # Verify basic cover features are supported
    assert cover.supported_features == BASIC_COVER_FEATURES

    # Verify tilt position returns None
    assert cover.current_cover_tilt_position is None

    # Verify position works correctly
    assert cover.current_cover_position == 50  # 0.5 level = 50% open
