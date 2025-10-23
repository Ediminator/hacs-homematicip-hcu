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

        # REFACTOR: Correctly call the centralized naming helper.
        self._set_entity_name(channel_label=self._channel.get("label"))

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
            _LOGGER.error(
                "Cannot operate lock '%s': Please set the Authorization PIN in the integration options.",
                self.name,
            )
            self._config_entry.async_start_reauth(self.hass)
            return

        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            await self._client.async_set_lock_state(
                self._device_id, self._channel_index, state=state, pin=pin
            )
        except HcuApiError as err:
            _LOGGER.error("Failed to set lock state for %s: %s", self.name, err)
            try:
                # Try to parse the error message to see if it's an invalid PIN
                error_body = json.loads(
                    err.args[0].replace("HCU Error: ", "").replace("'", '"')
                )
                if (
                    error_body.get("body", {}).get("errorCode")
                    == "INVALID_AUTHORIZATION_PIN"
                ):
                    _LOGGER.error(
                        "Invalid PIN for lock '%s'. Triggering re-authentication.",
                        self.name,
                    )
                    self._config_entry.async_start_reauth(self.hass)
            except (json.JSONDecodeError, IndexError, AttributeError):
                pass  # Not the error we are looking for
        except ConnectionError as err:
            _LOGGER.error(
                "Connection failed while setting lock state for %s: %s", self.name, err
            )
        finally:
            # Note: We don't reset assumed state here, we let the coordinator update do it
            # to prevent state flickering if the command succeeds but the error handling
            # was for a different issue. The coordinator is the source of truth.
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