import logging
from typing import TYPE_CHECKING

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.exceptions import HomeAssistantError


from .const import CONF_PIN
from .entity import HcuBaseEntity
from .api import HcuApiClient

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the lock platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.LOCK):
        async_add_entities(entities)


class HcuLock(HcuBaseEntity, LockEntity):
    """Representation of a Homematic IP HCU door lock."""

    PLATFORM = Platform.LOCK
    _attr_supported_features = LockEntityFeature.OPEN
    _attr_has_entity_name = True
    _attr_name = None  # Use device name

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
        config_entry: ConfigEntry,
    ):
        super().__init__(coordinator, client, device_data, channel_index)
        self._config_entry = config_entry
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_lock"

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        return self._channel.get("lockState") == "LOCKED"
    
    @property
    def available(self) -> bool:
        """
        Return if entity is available.

        The lock is unavailable if the base device is unreachable OR if the PIN
        has not been configured in the integration.
        """
        pin_configured = bool(self._config_entry.data.get(CONF_PIN))
        if not pin_configured:
            _LOGGER.warning(
                "Lock '%s' is unavailable because the PIN is not configured.", self.name
            )
        return super().available and pin_configured


    async def _set_lock_state(self, state: str) -> None:
        """Send the command to set the lock state."""
        pin = self._config_entry.data.get(CONF_PIN)
        if not pin:
            # This should theoretically not be reached due to the availability check,
            # but it's good practice to have it as a safeguard.
            _LOGGER.error(
                "Cannot operate lock '%s': Please set the Authorization PIN in the integration options.",
                self.name,
            )
            # Request re-authentication to prompt the user for the PIN
            self.hass.async_create_task(
                self.hass.config_entries.async_reload(self._config_entry.entry_id)
            )
            self._config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError("Authorization PIN for lock is not configured.")

        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            await self._client.async_set_lock_state(
                self._device_id, self._channel_index, state=state, pin=pin
            )
        except Exception as err:
            _LOGGER.error("Failed to set lock state for %s: %s", self.name, err)
            # If the operation fails, clear the assumed state to reflect the actual state
            self._attr_assumed_state = False
            self.async_write_ha_state()
            raise HomeAssistantError(f"Failed to set lock state: {err}") from err

    async def async_lock(self, **kwargs) -> None:
        """Lock the door."""
        await self._set_lock_state("LOCKED")

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the door."""
        await self._set_lock_state("UNLOCKED")

    async def async_open(self, **kwargs) -> None:
        """Open the door latch."""
        await self._set_lock_state("OPEN")