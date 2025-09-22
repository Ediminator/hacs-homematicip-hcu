# custom_components/hcu_integration/entity.py
"""Base entities for the Homematic IP HCU integration."""
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import DOMAIN, SIGNAL_UPDATE_ENTITY
from .api import HcuApiClient

class HcuBaseEntity(Entity):
    """Base class for HCU entities that are tied to a specific device channel."""

    _attr_should_poll = False

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the base entity."""
        self._client = client
        self._device_id = device_data["id"]
        self._channel_index_str = str(channel_index)
        self._channel_index = int(channel_index)

    @property
    def _device(self) -> dict:
        """Return the latest parent device data from the client's cache."""
        return self._client.get_device_by_address(self._device_id) or {}

    @property
    def _channel(self) -> dict:
        """Return the latest channel data from within the parent device's data structure."""
        return self._device.get("functionalChannels", {}).get(self._channel_index_str, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the device registry."""
        home_id = self._client._state.get("home", {}).get("id")
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device.get("label", "Unknown Device"),
            manufacturer="eQ-3",
            model=self._device.get("modelType"),
            sw_version=self._device.get("firmwareVersion"),
            via_device=(DOMAIN, home_id),
        )
    
    @property
    def available(self) -> bool:
        """Return if entity is available based on the device's unreach property."""
        maintenance_channel = self._device.get("functionalChannels", {}).get("0", {})
        return not maintenance_channel.get("unreach", False)

    async def async_added_to_hass(self) -> None:
        """Register a listener for state updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update
            )
        )

    @callback
    def _handle_update(self, updated_ids: set) -> None:
        """Handle a state update signal from the client."""
        if self._device_id in updated_ids:
            self.async_write_ha_state()

class HcuGroupBaseEntity(Entity):
    """Base class for HCU entities that are tied to a group (e.g., Climate)."""

    _attr_should_poll = False

    def __init__(self, client: HcuApiClient, group_data: dict):
        """Initialize the group base entity."""
        self._client = client
        self._group_id = group_data["id"]

    @property
    def _group(self) -> dict:
        """Return the latest group data from the client's cache."""
        return self._client.get_group_by_id(self._group_id) or {}

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this virtual group entity."""
        home_id = self._client._state.get("home", {}).get("id")
        return DeviceInfo(
            identifiers={(DOMAIN, self._group_id)},
            name=self._group.get("label") or "Unknown Group",
            manufacturer="Homematic IP",
            model="Heating Group",
            via_device=(DOMAIN, home_id),
        )

    @property
    def available(self) -> bool:
        """Return True if the entity's group exists in the state cache."""
        return self._group_id in self._client._state.get("groups", {})

    async def async_added_to_hass(self) -> None:
        """Register a listener for state updates."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_UPDATE_ENTITY, self._handle_update
            )
        )

    @callback
    def _handle_update(self, updated_ids: set) -> None:
        """Handle a state update signal from the client."""
        if self._group_id in updated_ids:
            self.async_write_ha_state()