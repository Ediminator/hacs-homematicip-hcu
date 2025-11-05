# custom_components/hcu_integration/lock.py
import logging
from typing import TYPE_CHECKING
import json

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PIN
from .entity import HcuBaseEntity
from .api import HcuApiClient, HcuApiError

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
        self._set_entity_name(channel_label=self._channel.get("label"))
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_lock"
        
        # Track if this specific lock has determined it requires a PIN
        self._pin_required: bool | None = None

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        return self._channel.get("lockState") == "LOCKED"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        attrs = {}
        
        # Indicate PIN status
        pin_configured = bool(self._config_entry.data.get(CONF_PIN))
        attrs["pin_configured"] = pin_configured
        
        # If we've determined this lock requires a PIN, indicate that
        if self._pin_required is not None:
            attrs["pin_required"] = self._pin_required
            
        return attrs

    async def _set_lock_state(self, state: str) -> None:
        """Send the command to set the lock state."""
        pin = self._config_entry.data.get(CONF_PIN)
        
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            await self._client.async_set_lock_state(
                self._device_id, self._channel_index, state=state, pin=pin
            )
            # If successful and we used no PIN, mark this lock as not requiring one
            if not pin and self._pin_required is None:
                self._pin_required = False
                
        except HcuApiError as err:
            error_str = str(err)
            
            # Parse the error to check if it's a PIN issue
            if "INVALID_AUTHORIZATION_PIN" in error_str:
                _LOGGER.error(
                    "Invalid or missing PIN for lock '%s'. Please configure the correct PIN in integration settings.",
                    self.name,
                )
                self._pin_required = True
                
                # Only trigger reauth if we already have a PIN configured (meaning it's wrong)
                # If no PIN is configured, user will see the attribute and can add it
                if pin:
                    self._config_entry.async_start_reauth(self.hass)
                else:
                    _LOGGER.warning(
                        "Lock '%s' requires a PIN. Please reconfigure the integration to add the PIN.",
                        self.name
                    )
                    
            else:
                _LOGGER.error("Failed to set lock state for %s: %s", self.name, err)
                
        except ConnectionError as err:
            _LOGGER.error(
                "Connection failed while setting lock state for %s: %s", self.name, err
            )
        finally:
            # Reset assumed state to let coordinator update provide actual state
            pass

    async def async_lock(self, **kwargs) -> None:
        """Lock the door."""
        await self._set_lock_state("LOCKED")

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the door."""
        await self._set_lock_state("UNLOCKED")

    async def async_open(self, **kwargs) -> None:
        """Open the door latch."""
        await self._set_lock_state("OPEN")
