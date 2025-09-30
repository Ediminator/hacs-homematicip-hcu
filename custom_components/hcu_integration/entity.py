# custom_components/hcu_integration/entity.py
"""Base entity classes for the Homematic IP HCU integration."""
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN
from .api import HcuApiClient

class HcuBaseEntity(Entity):
    """Base class for HCU entities tied to a specific device channel."""
    _attr_should_poll = False

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the base entity."""
        super().__init__()
        self._client = client
        self._device_id = device_data["id"]
        self._channel_index_str = str(channel_index)
        self._channel_index = int(channel_index)
        # Assumed state is used for optimistic updates to provide a responsive UI.
        self._attr_assumed_state = False

    @property
    def _device(self) -> dict:
        """Return the latest parent device data from the client's central cache."""
        return self._client.get_device_by_address(self._device_id) or {}

    @property
    def _channel(self) -> dict:
        """Return the latest channel data from the parent device's data structure."""
        return self._device.get("functionalChannels", {}).get(self._channel_index_str, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the Home Assistant device registry."""
        hcu_device_id = self._client.hcu_device_id
        
        # If this entity's device ID is one of the known IDs for the HCU,
        # we only provide the identifiers. This links the entity to the single,
        # coordinator-created HCU device entry instead of creating a new one.
        if self._device_id in self._client.hcu_part_device_ids:
            return DeviceInfo(
                identifiers={(DOMAIN, hcu_device_id)},
            )

        # For all other physical devices, create a full device entry and link it to the hub.
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device.get("label", "Unknown Device"),
            manufacturer=self._device.get("oem", "eQ-3"),
            model=self._device.get("modelType"),
            sw_version=self._device.get("firmwareVersion"),
            # This 'via_device' link correctly parents the physical device to the HCU hub.
            via_device=(DOMAIN, hcu_device_id),
        )
    
    @property
    def available(self) -> bool:
        """
        Return if entity is available.
        This is determined by the 'unreach' property of the device's maintenance channel (channel 0).
        """
        maintenance_channel = self._device.get("functionalChannels", {}).get("0", {})
        return not maintenance_channel.get("unreach", False)

    async def async_added_to_hass(self) -> None:
        """Register a callback for state updates when the entity is added to Home Assistant."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_update", self._handle_update
            )
        )

    @callback
    def _handle_update(self, updated_ids: set) -> None:
        """
        Handle a state update signal from the coordinator.
        If this entity's device ID is in the set of updated IDs, it tells Home Assistant
        to re-read its state. The 'assumed_state' is cleared because we now have a
        confirmed state from the device.
        """
        if self._device_id in updated_ids:
            self._attr_assumed_state = False
            self.async_write_ha_state()

class HcuGroupBaseEntity(Entity):
    """Base class for HCU entities that are tied to a group (e.g., Climate)."""
    _attr_should_poll = False

    def __init__(self, client: HcuApiClient, group_data: dict):
        """Initialize the group base entity."""
        super().__init__()
        self._client = client
        self._group_id = group_data["id"]
        self._attr_assumed_state = False

    @property
    def _group(self) -> dict:
        """Return the latest group data from the client's central cache."""
        return self._client.get_group_by_id(self._group_id) or {}

    @property
    def device_info(self) -> DeviceInfo:
        """
        Return device information for this virtual group entity.
        Groups are represented as their own devices in Home Assistant, parented to the HCU hub.
        """
        hcu_device_id = self._client.hcu_device_id
        return DeviceInfo(
            identifiers={(DOMAIN, self._group_id)},
            name=self._group.get("label") or "Unknown Group",
            manufacturer="Homematic IP",
            model="Group",
            via_device=(DOMAIN, hcu_device_id),
        )

    @property
    def available(self) -> bool:
        """Return True if the entity's group exists in the state cache."""
        return self._group_id in self._client.state.get("groups", {})

    async def async_added_to_hass(self) -> None:
        """Register a listener for state updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_update", self._handle_update
            )
        )

    @callback
    def _handle_update(self, updated_ids: set) -> None:
        """Handle a state update signal from the coordinator."""
        if self._group_id in updated_ids:
            # Clear any optimistic state attributes when a real update arrives.
            if hasattr(self, "_attr_hvac_mode"):
                self._attr_hvac_mode = None
            if hasattr(self, "_attr_target_temperature"):
                self._attr_target_temperature = None
            self._attr_assumed_state = False
            self.async_write_ha_state()

class HcuHomeBaseEntity(Entity):
    """Base class for HCU entities tied to the 'home' object (e.g., Alarm Panel)."""
    _attr_should_poll = False

    def __init__(self, client: HcuApiClient):
        """Initialize the home base entity."""
        super().__init__()
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

    async def async_added_to_hass(self) -> None:
        """Register a listener for state updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_update", self._handle_update
            )
        )

    @callback
    def _handle_update(self, updated_ids: set) -> None:
        """Handle a state update signal from the client."""
        if self._home_uuid in updated_ids:
            self._attr_assumed_state = False
            self.async_write_ha_state()