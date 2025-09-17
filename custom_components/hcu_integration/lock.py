# custom_components/hcu_integration/lock.py
"""Lock platform for the Homematic IP HCU integration."""
import logging
from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_DEVICE_PLATFORM_MAP
from .entity import HcuBaseEntity
from .api import HcuApiClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the lock platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    coordinator = data["coordinator"]
    devices = coordinator.data.get("devices", {})
    
    new_locks = []
    for device_data in devices.values():
        if HMIP_DEVICE_PLATFORM_MAP.get(device_data.get("type")) == "lock":
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                if "lockState" in channel_data:
                    new_locks.append(HcuLock(client, coordinator, device_data, channel_index))
    if new_locks: async_add_entities(new_locks)

class HcuLock(HcuBaseEntity, LockEntity):
    """Representation of an HCU Lock."""
    _attr_supported_features = LockEntityFeature.OPEN

    def __init__(self, client, coordinator, device_data, channel_index):
        """Initialize the lock."""
        super().__init__(coordinator, device_data, channel_index)
        self._client = client
        self._attr_name = self._device.get("label") or "Unknown Lock"
        self._attr_unique_id = f"{self._device.get('id')}_{self._channel_index}_lock"
        # TODO: The authorization PIN must be configured by the user.
        self._pin = "PIN_NOT_CONFIGURED" 

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        return self._updated_channel.get("lockState") == "LOCKED"

    async def _set_lock_state(self, state: str) -> None:
        """Helper to set the lock state and log warnings if PIN is not set."""
        if self._pin == "PIN_NOT_CONFIGURED":
            _LOGGER.error(
                "Cannot operate lock %s: Authorization PIN is not configured.", self.name
            )
            return
        
        await self._client.async_set_lock_state(
            self._device.get("id"), self._channel.get("index"), state, self._pin
        )
        # No manual refresh needed with event-driven updates.

    async def async_lock(self, **kwargs) -> None:
        """Lock the door."""
        await self._set_lock_state("LOCKED")

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the door."""
        await self._set_lock_state("UNLOCKED")

    async def async_open(self, **kwargs) -> None:
        """Open the door latch."""
        await self._set_lock_state("OPEN")