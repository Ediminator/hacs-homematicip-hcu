# custom_components/hcu_integration/lock.py
"""Lock platform for the Homematic IP HCU integration."""
import logging
from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HcuBaseEntity
from .api import HcuApiClient

_LOGGER = logging.getLogger(__name__)
CONF_PIN = "pin"

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the lock platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    devices = data["initial_state"].get("devices", {})
    
    new_locks = []
    for device_data in devices.values():
        if not device_data.get("PARENT"):
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                # Discover a lock if its channel has the 'lockState' feature.
                if "lockState" in channel_data:
                    new_locks.append(HcuLock(client, device_data, channel_index, config_entry))
    if new_locks:
        async_add_entities(new_locks)

class HcuLock(HcuBaseEntity, LockEntity):
    """Representation of a Homematic IP HCU door lock."""
    _attr_supported_features = LockEntityFeature.OPEN

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str, config_entry: ConfigEntry):
        """Initialize the lock entity."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = self._device.get("label") or "Unknown Lock"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_lock"
        
        # The authorization PIN is required for all lock operations.
        # It is configured by the user in the integration's options flow.
        self._pin = config_entry.options.get(CONF_PIN)

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is in the 'LOCKED' state."""
        return self._channel.get("lockState") == "LOCKED"

    async def _set_lock_state(self, state: str) -> None:
        """Helper function to send a lock command to the HCU."""
        if not self._pin:
            _LOGGER.error(
                "Cannot operate lock '%s': Please set the Authorization PIN in the integration options.", self.name
            )
            return
        
        await self._client.async_set_lock_state(
            self._device_id, self._channel_index, state, self._pin
        )

    async def async_lock(self, **kwargs) -> None:
        """Lock the door."""
        await self._set_lock_state("LOCKED")

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the door."""
        await self._set_lock_state("UNLOCKED")

    async def async_open(self, **kwargs) -> None:
        """Open the door latch."""
        await self._set_lock_state("OPEN")