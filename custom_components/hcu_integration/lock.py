# custom_components/hcu_integration/lock.py
import logging
from typing import TYPE_CHECKING
import json

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PIN, DOCS_URL_LOCK_PIN_CONFIG
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

        # Log available channel data fields for diagnostics
        _LOGGER.debug(
            "Lock '%s' initialized with channel data fields: %s",
            self._attr_unique_id,
            list(self._channel.keys())
        )

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        return self._channel.get("lockState") == "LOCKED"

    @property
    def is_locking(self) -> bool | None:
        """Return true if the lock is locking."""
        # Check motorState field (confirmed to exist on HmIP-DLD channel 1)
        motor_state = self._channel.get("motorState")
        if motor_state == "LOCKING":
            return True

        # Check if lockState is transitioning to LOCKED
        lock_state = self._channel.get("lockState")
        if lock_state == "LOCKING":
            return True

        return None

    @property
    def is_unlocking(self) -> bool | None:
        """Return true if the lock is unlocking."""
        # Check motorState field (confirmed to exist on HmIP-DLD channel 1)
        motor_state = self._channel.get("motorState")
        if motor_state == "UNLOCKING":
            return True

        # Check if lockState is transitioning to UNLOCKED
        lock_state = self._channel.get("lockState")
        if lock_state == "UNLOCKING":
            return True

        return None

    @property
    def is_jammed(self) -> bool | None:
        """Return true if the lock is jammed (incomplete locking)."""
        # Check lockJammed on channel 0 (DEVICE_OPERATIONLOCK)
        # This is the actual field name on HmIP-DLD firmware 1.4.12+
        device_channel = self._device.get("functionalChannels", {}).get("0", {})
        lock_jammed = device_channel.get("lockJammed")
        if lock_jammed is True:
            return True

        # Check motorState for jammed condition (in case it's reported there)
        motor_state = self._channel.get("motorState")
        if motor_state == "JAMMED":
            return True

        # Check lockState for jammed condition
        lock_state = self._channel.get("lockState")
        if lock_state == "JAMMED":
            return True

        return None

    @property
    def is_opening(self) -> bool | None:
        """Return true if the lock is opening."""
        # Check motorState field (confirmed to exist on HmIP-DLD channel 1)
        motor_state = self._channel.get("motorState")
        if motor_state == "OPENING":
            return True

        # Check if lockState is transitioning to OPEN
        lock_state = self._channel.get("lockState")
        if lock_state == "OPENING":
            return True

        return None

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

        # Expose motorState for diagnostics (confirmed to exist on HmIP-DLD)
        motor_state = self._channel.get("motorState")
        if motor_state is not None:
            attrs["motor_state"] = motor_state

        # Expose lockJammed from channel 0 (DEVICE_OPERATIONLOCK)
        device_channel = self._device.get("functionalChannels", {}).get("0", {})
        lock_jammed = device_channel.get("lockJammed")
        if lock_jammed is not None:
            attrs["lock_jammed"] = lock_jammed

        # Expose auto relock configuration
        auto_relock_enabled = self._channel.get("autoRelockEnabled")
        if auto_relock_enabled is not None:
            attrs["auto_relock_enabled"] = auto_relock_enabled

        auto_relock_delay = self._channel.get("autoRelockDelay")
        if auto_relock_delay is not None:
            attrs["auto_relock_delay"] = auto_relock_delay

        # Check access authorization channels for diagnostic purposes
        # Helps users understand if the plugin has permission to control the lock
        channels = self._device.get("functionalChannels", {})
        authorized_channels = []
        for ch_id, ch_data in channels.items():
            if ch_data.get("functionalChannelType") == "ACCESS_AUTHORIZATION_CHANNEL":
                if ch_data.get("authorized") is True:
                    authorized_channels.append(ch_id)

        if authorized_channels:
            attrs["authorized_access_channels"] = authorized_channels
            attrs["has_access_authorization"] = True
        else:
            attrs["has_access_authorization"] = False

        return attrs

    async def _set_lock_state(self, state: str) -> None:
        """Send the command to set the lock state."""
        pin = self._config_entry.data.get(CONF_PIN)

        _LOGGER.debug(
            "Setting lock state for '%s' to %s (channel: %s, device: %s)",
            self.name, state, self._channel_index, self._device_id
        )

        # Use optimistic state updates for immediate UI feedback
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            await self._client.async_set_lock_state(
                self._device_id, self._channel_index, state=state, pin=pin
            )
            _LOGGER.debug("Successfully sent lock state command for '%s'", self.name)

            # If successful and we used no PIN, mark this lock as not requiring one
            if not pin and self._pin_required is None:
                self._pin_required = False

        except HcuApiError as err:
            error_str = str(err)

            # Parse the error to check if it's a PIN issue
            if "INVALID_AUTHORIZATION_PIN" in error_str:
                _LOGGER.error(
                    "Invalid or missing PIN for lock '%s'. "
                    "To configure the PIN: Go to Settings → Devices & Services → "
                    "Homematic IP Local (HCU) → CONFIGURE → Enter your door lock's Authorization PIN. "
                    "See %s for details.",
                    self.name,
                    DOCS_URL_LOCK_PIN_CONFIG,
                )
                self._pin_required = True

                # Only trigger reauth if we already have a PIN configured (meaning it's wrong)
                # If no PIN is configured, user will see the attribute and can add it
                if pin:
                    self._config_entry.async_start_reauth(self.hass)
                else:
                    _LOGGER.warning(
                        "Lock '%s' requires a PIN to function. "
                        "Please configure it: Settings → Devices & Services → "
                        "Homematic IP Local (HCU) → CONFIGURE → Enter Authorization PIN. "
                        "See %s for details.",
                        self.name,
                        DOCS_URL_LOCK_PIN_CONFIG,
                    )

            # Check for access denied / permission errors
            elif "ACCESS_DENIED" in error_str or "INVALID_REQUEST" in error_str or "no permission" in error_str.lower():
                _LOGGER.error(
                    "Access denied for lock '%s'. The Home Assistant Integration plugin user "
                    "does not have permission to control this lock. "
                    "\n\nTo fix this issue:\n"
                    "1. Open the HomematicIP app on your phone\n"
                    "2. Go to Settings → Access Control → Access Profiles\n"
                    "3. Select or create an access profile for this lock\n"
                    "4. Try to add 'Home Assistant Integration' user to the profile\n"
                    "\nKNOWN LIMITATION: The plugin user may appear grayed out or expired in the app. "
                    "This is a known issue with the HCU firmware. The integration has properly registered with the HCU, "
                    "but the HomematicIP app may not allow assigning it to access profiles. "
                    "\nPlease check the 'has_access_authorization' attribute to verify authorization status.",
                    self.name,
                )

            # Check for motor jam errors
            elif "JAMMED" in error_str or "JAM" in error_str:
                _LOGGER.error(
                    "Lock '%s' is jammed and cannot complete the operation. "
                    "Check the lock mechanism for obstructions.",
                    self.name,
                )

            else:
                _LOGGER.error("Failed to set lock state for %s: %s", self.name, err)

        except ConnectionError as err:
            _LOGGER.error(
                "Connection failed while setting lock state for %s: %s", self.name, err
            )

        finally:
            # Reset assumed state to let coordinator updates provide actual state
            # The coordinator will update the entity state based on WebSocket events
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_lock(self, **kwargs) -> None:
        """Lock the door."""
        await self._set_lock_state("LOCKED")

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the door."""
        await self._set_lock_state("UNLOCKED")

    async def async_open(self, **kwargs) -> None:
        """Open the door latch."""
        await self._set_lock_state("OPEN")
