# custom_components/hcu_integration/button.py
"""
Support for Homematic IP HCU action buttons.
Stateless buttons are handled via events in the coordinator.
"""
import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HcuBaseEntity
from .api import HcuApiClient, HcuApiError
from .const import CONF_PIN, LOCK_STATE_OPEN

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the button platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.BUTTON):
        async_add_entities(entities)


class HcuResetEnergyButton(HcuBaseEntity, ButtonEntity):
    """Representation of a button to reset the energy counter."""

    PLATFORM = Platform.BUTTON
    _attr_has_entity_name = True
    _attr_icon = "mdi:reload"

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        """Initialize the reset button."""
        super().__init__(coordinator, client, device_data, channel_index)

        # REFACTOR: Correctly call the centralized naming helper for feature entities.
        self._set_entity_name(
            channel_label=self._channel.get("label"), feature_name="Reset Energy Counter"
        )
        self._attr_unique_id = (
            f"{self._device_id}_{self._channel_index}_reset_energy_counter"
        )

    async def async_press(self) -> None:
        """Handle the button press action."""
        _LOGGER.info("Resetting energy counter for %s", self.entity_id)
        try:
            await self._client.async_reset_energy_counter(
                self._device_id, self._channel_index
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error(
                "Error resetting energy counter for %s: %s", self.entity_id, err
            )

class HcuDoorOpenerButton(HcuBaseEntity, ButtonEntity):
    """Representation of a button to trigger a door opener (e.g., HmIP-FDC)."""

    PLATFORM = Platform.BUTTON
    _attr_icon = "mdi:door"

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        """Initialize the door opener button."""
        super().__init__(coordinator, client, device_data, channel_index)

        # Set entity name using the centralized naming helper
        self._set_entity_name(channel_label=self._channel.get("label"), feature_name="Open")

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_open"

    async def async_press(self) -> None:
        """Trigger the door opener (sends 1s pulse to open door)."""
        _LOGGER.info("Triggering door opener for %s", self.entity_id)
        try:
            await self._client.async_send_door_command(
                self._device_id, self._channel_index, "OPEN"
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error(
                "Error triggering door opener for %s: %s", self.entity_id, err
            )
            
class HcuDoorImpulseButton(HcuBaseEntity, ButtonEntity):
    """Representation of a button to trigger a door impulse (e.g., HmIP-WGC)."""

    PLATFORM = Platform.BUTTON
    _attr_icon = "mdi:garage"

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        """Initialize the door impulse button."""
        super().__init__(coordinator, client, device_data, channel_index)

        # Set entity name using the centralized naming helper
        self._set_entity_name(channel_label=self._channel.get("label"), feature_name="Impulse")

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_impulse"

    async def async_press(self) -> None:
        """Trigger the door impulse (sends x s pulse to open garage door)."""
        _LOGGER.info("Triggering door impulse for %s", self.entity_id)
        try:
            await self._client.async_send_door_impulse(
                self._device_id, self._channel_index
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error(
                "Error triggering door impulse for %s: %s", self.entity_id, err
            )

class HcuDeviceIdentifyButton(HcuBaseEntity, ButtonEntity):
    """Representation of a button to trigger device identify (blink/beep)."""

    PLATFORM = Platform.BUTTON
    _attr_translation_key = "hcu_device_identify"
    _attr_icon = "mdi:crosshairs-gps"

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        """Initialize the identify button."""
        super().__init__(coordinator, client, device_data, channel_index)

        self._attr_device_class = None
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_identify"

    async def async_press(self) -> None:
        """Trigger identify for the device/channel (e.g., blink/beep)."""
        _LOGGER.info("Triggering identify for %s", self.entity_id)
        try:
            await self._client.async_send_identify(
                self._device_id, self._channel_index
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error(
                "Error triggering identify for %s: %s", self.entity_id, err
            )

class HcuDoorUnlatchButton(HcuBaseEntity, ButtonEntity):
    """Representation of a button to unlatch a door lock (e.g., HmIP-DLD)."""

    PLATFORM = Platform.BUTTON
    _attr_icon = "mdi:door-open"

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
        config_entry: ConfigEntry,
    ):
        """Initialize the door unlatch button."""
        super().__init__(coordinator, client, device_data, channel_index)
        self._config_entry = config_entry
        self._set_entity_name(channel_label=self._channel.get("label"), feature_name="Unlatch")
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_unlatch"

    async def async_press(self) -> None:
        """Pull the door latch to open the door."""
        pin = self._config_entry.data.get(CONF_PIN)
        _LOGGER.info("Triggering unlatch for %s", self.entity_id)
        
        try:
            await self._client.async_set_lock_state(
                self._device_id, self._channel_index, state=LOCK_STATE_OPEN, pin=pin
            )
        except (HcuApiError, ConnectionError) as err:
            error_str = str(err)
            if any(
                e in error_str for e in ("ACCESS_DENIED", "INVALID_REQUEST", "CLIENT_INVALID_AUTHORIZATION")
            ) or "no permission" in error_str.lower():
                _LOGGER.error(
                    "Access denied for lock unlatch button '%s'. The Home Assistant Integration plugin user "
                    "does not have permission to control this lock. "
                    "\n\nTo fix this issue:\n"
                    "0. CRITICAL: Ensure your HCU Firmware is updated to version 1.6.16 or higher.\n"
                    "1. Delete any old 'Home Assistant' profiles if they appear grayed out.\n"
                    "2. Open the HomematicIP app on your phone\n"
                    "3. Go to Settings → Access Control → Access Profiles\n"
                    "4. Create a new access profile for this lock and add the 'Home Assistant Integration' user.\n"
                    "\nKNOWN LIMITATION: Even on 1.6.16, the plugin user may still appear grayed out or expired in the app. "
                    "This is a known UI bug with the HCU firmware. The integration has properly registered with the HCU, "
                    "but the HomematicIP app UI often lags.\n"
                    "Please check the 'has_access_authorization' attribute on the lock entity to verify authorization status.",
                    self.entity_id,
                )
            else:
                _LOGGER.error(
                    "Error triggering unlatch for %s: %s", self.entity_id, err
                )
