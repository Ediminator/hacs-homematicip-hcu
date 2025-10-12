from __future__ import annotations
from typing import TYPE_CHECKING

from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .api import HcuApiClient

if TYPE_CHECKING:
    from . import HcuCoordinator


class HcuBaseEntity(CoordinatorEntity["HcuCoordinator"], Entity):
    """Base class for entities tied to a specific device channel."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient, 
        device_data: dict, 
        channel_index: str
    ):
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._client = client
        self._device_id = device_data["id"]
        self._channel_index_str = str(channel_index)
        self._channel_index = int(channel_index)
        self._attr_assumed_state = False

    @property
    def _device(self) -> dict:
        """Return the latest parent device data from the client's cache."""
        return self._client.get_device_by_address(self._device_id) or {}

    @property
    def _channel(self) -> dict:
        """Return the latest channel data from the parent device's data structure."""
        return self._device.get("functionalChannels", {}).get(self._channel_index_str, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the Home Assistant device registry."""
        hcu_device_id = self._client.hcu_device_id

        if self._device_id in self._client.hcu_part_device_ids:
            return DeviceInfo(
                identifiers={(DOMAIN, hcu_device_id)},
            )

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device.get("label", "Unknown Device"),
            manufacturer=self._device.get("oem", "eQ-3"),
            model=self._device.get("modelType"),
            sw_version=self._device.get("firmwareVersion"),
            via_device=(DOMAIN, hcu_device_id),
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        maintenance_channel = self._device.get("functionalChannels", {}).get("0", {})
        return not maintenance_channel.get("unreach", False)
    
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Check if the device this entity belongs to was updated
        if self._device_id in self.coordinator.data:
            self._attr_assumed_state = False
            self.async_write_ha_state()
        super()._handle_coordinator_update()


class HcuGroupBaseEntity(CoordinatorEntity["HcuCoordinator"], Entity):
    """Base class for entities that are tied to a group."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self, 
        coordinator: "HcuCoordinator",
        client: HcuApiClient, 
        group_data: dict
    ):
        """Initialize the group base entity."""
        super().__init__(coordinator)
        self._client = client
        self._group_id = group_data["id"]
        self._attr_assumed_state = False

    @property
    def _group(self) -> dict:
        """Return the latest group data from the client's central cache."""
        return self._client.get_group_by_id(self._group_id) or {}

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this virtual group entity."""
        hcu_device_id = self._client.hcu_device_id
        # Format the group type to be more descriptive (e.g., "HEATING" -> "Heating Group")
        group_type = self._group.get("type", "Group").replace("_", " ").title()
        model_name = f"{group_type} Group"
        
        return DeviceInfo(
            identifiers={(DOMAIN, self._group_id)},
            name=self._group.get("label") or "Unknown Group",
            manufacturer="Homematic IP",
            model=model_name,
            via_device=(DOMAIN, hcu_device_id),
        )

    @property
    def available(self) -> bool:
        """Return True if the entity's group exists in the state cache."""
        return self._group_id in self._client.state.get("groups", {})

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._group_id in self.coordinator.data:
            if hasattr(self, "_attr_hvac_mode"):
                self._attr_hvac_mode = None
            if hasattr(self, "_attr_target_temperature"):
                self._attr_target_temperature = None
            self._attr_assumed_state = False
            self.async_write_ha_state()
        super()._handle_coordinator_update()


class HcuHomeBaseEntity(CoordinatorEntity["HcuCoordinator"], Entity):
    """Base class for entities tied to the 'home' object."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient
    ):
        """Initialize the home base entity."""
        super().__init__(coordinator)
        self._client = client
        self._hcu_device_id = self._client.hcu_device_id
        self._home_uuid = self._client.state.get("home", {}).get("id")
        self._attr_assumed_state = False

    @property
    def _home(self) -> dict:
        """Return the latest home data from the client's cache."""
        return self._client.state.get("home", {})

    @property
    def device_info(self) -> DeviceInfo:
        """Link this entity to the main HCU device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._hcu_device_id)},
        )

    @property
    def available(self) -> bool:
        """Return True if the home object exists in the state cache."""
        return bool(self._home)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the client."""
        if self._home_uuid in self.coordinator.data:
            self._attr_assumed_state = False
            self.async_write_ha_state()
        super()._handle_coordinator_update()
