"""Test for Issue 120: HmIP-WLAN-HAP device identification."""
import pytest
from custom_components.hcu_integration.api import HcuApiClient

async def test_hcu_part_device_ids_excludes_wlan_hap(api_client: HcuApiClient):
    """Test that HmIP-WLAN-HAP is excluded from HCU part device IDs."""
    api_client._state = {
        "home": {
            "accessPointId": "hcu_device",
        },
        "devices": {
            "hcu_device": {
                "type": "HOME_CONTROL_ACCESS_POINT",
                "modelType": "HmIP-HCU-1",
                "id": "hcu_device"
            },
            "wlan_hap_device": {
                "type": "HOME_CONTROL_ACCESS_POINT",
                "modelType": "HmIP-WLAN-HAP",
                "id": "wlan_hap_device"
            },
        }
    }
    
    api_client._update_hcu_device_ids()

    assert api_client.hcu_device_id == "hcu_device"
    assert "hcu_device" in api_client.hcu_part_device_ids
    assert "wlan_hap_device" not in api_client.hcu_part_device_ids
