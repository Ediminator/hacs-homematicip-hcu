# custom_components/hcu_integration/entity.py
from __future__ import annotations
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_ENTITY_PREFIX
from .api import HcuApiClient

if TYPE_CHECKING:
    from . import HcuCoordinator


class HcuEntityPrefixMixin:
    """Mixin to provide entity prefix property for all HCU entities."""

    coordinator: "HcuCoordinator"  # Type hint for the coordinator

    @property
    def _entity_prefix(self) -> str:
        """Get the entity name prefix from config entry."""
        return self.coordinator.config_entry.data.get(CONF_ENTITY_PREFIX, "")


class HcuBaseEntity(CoordinatorEntity["HcuCoordinator"], HcuEntityPrefixMixin, Entity):
    """Base class for entities tied to a specific Homematic IP device channel."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict[str, Any],
        channel_index: str,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._client = client
        self._device_id = device_data["id"]
        self._channel_index_str = str(channel_index)
        self._channel_index = int(channel_index)
        self._attr_assumed_state = False

    def _set_entity_name(
        self,
        channel_label: str | None = None,
        feature_name: str | None = None,
    ) -> None:
        """
        Set the entity name based on the channel label and feature.

        This central helper ensures consistent naming across all platforms.
        Applies entity prefix if configured for multi-home setups.
        """
        prefix = self._entity_prefix
        base_name: str | None = None

        if feature_name:
            # This is a "feature" entity (sensor, binary_sensor, button)
            if channel_label:
                # Sensor on a labeled channel: "Channel Label Feature Name"
                # (e.g., "Living Room Thermostat Temperature")
                base_name = f"{channel_label} {feature_name}"
                self._attr_has_entity_name = False
            else:
                # Sensor on an unlabeled channel: "Feature Name"
                # (e.g., "Low Battery" on a device)
                base_name = feature_name
                self._attr_has_entity_name = True
        else:
            # This is a "main" entity (switch, light, cover, lock)
            if channel_label:
                # Main entity on a labeled channel: "Channel Label"
                # (e.g., "Ceiling Light")
                base_name = channel_label
                self._attr_has_entity_name = False
            else:
                # Main entity on an unlabeled channel (e.g., FROLL, PSM-2)
                # Use the device's label, model type, or device ID as fallback.
                # Setting has_entity_name to True makes it a standalone entity name.
                # The prefix will be applied by the logic below.
                # (e.g., "HmIP-PSM-2" or "House1 HmIP-PSM-2" if prefixed)
                base_name = self._device.get("label") or self._device.get("modelType") or self._device_id
                self._attr_has_entity_name = True

        # Apply prefix to base name (only if base_name is not None)
        if base_name is not None:
            self._attr_name = f"{prefix} {base_name}" if prefix else base_name

    @property
    def _device(self) -> dict[str, Any]:
        """Return the latest parent device data from the client's state cache."""
        return self._client.get_device_by_address(self._device_id) or {}

    @property
    def _channel(self) -> dict[str, Any]:
        """Return the latest channel data from the parent device's data structure."""
        return self._device.get("functionalChannels", {}).get(self._channel_index_str, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the Home Assistant device registry."""
        hcu_device_id = self._client.hcu_device_id

        # If the entity belongs to the HCU itself, link it to the main HCU device
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
        """Return True if the entity is available."""
        if not self._client.is_connected or not self._device or not self._channel:
            return False

        # Devices that are permanently reachable (e.g., wired/powered devices)
        # are always available when connected
        if self._device.get("permanentlyReachable", False):
            return True

        # For non-permanently-reachable devices (e.g., battery-powered),
        # check the maintenance channel's reachability status
        maintenance_channel = self._device.get("functionalChannels", {}).get("0", {})
        return not maintenance_channel.get("unreach", False)


    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._device_id in self.coordinator.data:
            self._attr_assumed_state = False
            self.async_write_ha_state()


class HcuGroupBaseEntity(CoordinatorEntity["HcuCoordinator"], HcuEntityPrefixMixin, Entity):
    """Base class for entities that represent a Homematic IP group."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        group_data: dict[str, Any],
    ) -> None:
        """Initialize the group base entity."""
        super().__init__(coordinator)
        self._client = client
        self._group_id = group_data["id"]
        self._attr_assumed_state = False

    @property
    def _group(self) -> dict[str, Any]:
        """Return the latest group data from the client's state cache."""
        return self._client.get_group_by_id(self._group_id) or {}

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this virtual group entity."""
        hcu_device_id = self._client.hcu_device_id
        group_type = self._group.get("type", "Group").replace("_", " ").title()
        model_name = f"{group_type} Group"

        return DeviceInfo(
            identifiers={(DOMAIN, self._group_id)},
            name=self._group.get("label", "Unknown Group"),
            manufacturer="Homematic IP",
            model=model_name,
            via_device=(DOMAIN, hcu_device_id),
        )

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._client.is_connected and bool(self._group)


    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._group_id in self.coordinator.data:
            self._attr_assumed_state = False
            self.async_write_ha_state()


class HcuHomeBaseEntity(CoordinatorEntity["HcuCoordinator"], HcuEntityPrefixMixin, Entity):
    """Base class for entities tied to the global 'home' object."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
    ) -> None:
        """Initialize the home base entity."""
        super().__init__(coordinator)
        self._client = client
        self._hcu_device_id = self._client.hcu_device_id
        self._home_uuid = self._client.state.get("home", {}).get("id")
        self._attr_assumed_state = False

    @property
    def _home(self) -> dict[str, Any]:
        """Return the latest home data from the client's state cache."""
        return self._client.state.get("home", {})

    @property
    def device_info(self) -> DeviceInfo:
        """Link this entity to the main HCU device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._hcu_device_id)},
        )

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._client.is_connected and bool(self._home)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self._home_uuid in self.coordinator.data:
            self._attr_assumed_state = False
            self.async_write_ha_state()