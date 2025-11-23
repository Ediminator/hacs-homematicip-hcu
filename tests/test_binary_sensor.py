from unittest.mock import MagicMock
import pytest

@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.async_add_listener = MagicMock()
    # Mock config_entry to return an empty dict for get() to prevent MagicMock objects in strings
    coordinator.config_entry.data.get.return_value = ""
    return coordinator

def test_hcu_unreach_binary_sensor_availability(mock_coordinator, mock_hcu_client, mock_device_data):
    """Test HcuUnreachBinarySensor availability."""
    from custom_components.hcu_integration.binary_sensor import HcuUnreachBinarySensor
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass

    mapping = {
        "name": "Connectivity",
        "device_class": BinarySensorDeviceClass.CONNECTIVITY,
    }

    # Simulate unreachable device
    mock_device_data["permanentlyReachable"] = False
    mock_device_data["functionalChannels"]["0"]["unreach"] = True

    mock_hcu_client.get_device_by_address = MagicMock(return_value=mock_device_data)
    # Ensure client is considered connected
    mock_hcu_client.is_connected = True

    entity = HcuUnreachBinarySensor(
        coordinator=mock_coordinator,
        client=mock_hcu_client,
        device_data=mock_device_data,
        channel_index="0",
        feature="unreach",
        mapping=mapping,
    )

    # Should be available even if device is unreachable, as long as client is connected
    assert entity.available is True

    # Value should be False (not connected)
    assert entity.is_on is False

    # Simulate client disconnect
    mock_hcu_client.is_connected = False
    assert entity.available is False
