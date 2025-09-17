# custom_components/hcu_integration/entity.py
"""Base entity for the Homematic IP HCU integration."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

class HcuBaseEntity(CoordinatorEntity):
    """Base class for all HCU entities."""
    def __init__(self, coordinator, device_data: dict, channel_index: str):
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._device = device_data
        self._channel_index = channel_index
        self._channel = self._device.get("functionalChannels", {}).get(self._channel_index, {})

    @property
    def _updated_channel(self) -> dict:
        """Return the updated channel data from the coordinator's latest fetch."""
        updated_device = self.coordinator.data.get("devices", {}).get(self._device.get("id"))
        if updated_device:
            return updated_device.get("functionalChannels", {}).get(self._channel_index, {})
        return {}

    @property
    def device_info(self):
        """Return device information for the device registry."""
        home_id = self.coordinator.data.get("home", {}).get("id")
        return {
            "identifiers": {(DOMAIN, self._device.get("id"))},
            "name": self._device.get("label"),
            "manufacturer": self._device.get("oem"),
            "model": self._device.get("modelType"),
            "sw_version": self._device.get("firmwareVersion"),
            "via_device": (DOMAIN, home_id),
        }