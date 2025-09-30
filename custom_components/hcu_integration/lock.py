# custom_components/hcu_integration/lock.py
"""
Lock platform for the Homematic IP HCU integration.

This platform creates lock entities for Homematic IP door lock actuators.
"""
import logging
from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_PIN, HMIP_FEATURE_TO_ENTITY, API_PATHS
from .entity import HcuBaseEntity
from .api import HcuApiClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the lock platform from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = coordinator.client
    
    new_entities = []
    created_entity_ids = set()

    for device_data in client.state.get("devices", {}).values():
        if device_data.get("PARENT"):
            continue # Skip child devices as they are handled by their parent.

        oem = device_data.get("oem")
        if oem and oem != "eQ-3":
            # Check if importing devices from this third-party manufacturer is enabled.
            option_key = f"import_{oem.lower().replace(' ', '_')}"
            if not config_entry.options.get(option_key, True):
                continue

        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            if "lockState" in channel_data:
                mapping = HMIP_FEATURE_TO_ENTITY.get("lockState", {})
                if mapping.get("class") == "HcuLock":
                    unique_id = f"{device_data['id']}_{channel_index}_lock"
                    if unique_id not in created_entity_ids:
                        new_entities.append(HcuLock(client, device_data, channel_index, config_entry))
                        created_entity_ids.add(unique_id)

    if new_entities:
        async_add_entities(new_entities)


class HcuLock(HcuBaseEntity, LockEntity):
    """Representation of a Homematic IP HCU door lock."""
    _attr_supported_features = LockEntityFeature.OPEN

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str, config_entry: ConfigEntry):
        """Initialize the lock entity."""
        super().__init__(client, device_data, channel_index)
        self._config_entry = config_entry
        self._attr_name = self._device.get("label") or "Unknown Lock"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_lock"

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is in the 'LOCKED' state."""
        return self._channel.get("lockState") == "LOCKED"

    async def _set_lock_state(self, state: str) -> None:
        """Helper function to send a lock command to the HCU."""
        pin = self._config_entry.options.get(CONF_PIN)
        if not pin:
            _LOGGER.error(
                "Cannot operate lock '%s': Please set the Authorization PIN in the integration options.", self.name
            )
            return
        
        self._attr_assumed_state = True
        self.async_write_ha_state()

        await self._client.async_device_control(
            path=API_PATHS.SET_LOCK_STATE,
            device_id=self._device_id, 
            channel_index=self._channel_index, 
            body={"targetLockState": state, "authorizationPin": pin}
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