# custom_components/hcu_integration/button.py
"""
Support for Homematic IP HCU action buttons.
Stateless buttons are handled via events in the coordinator.
"""
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HcuBaseEntity
from .api import HcuApiClient, HcuApiError
from .util import handle_lock_api_error
from .const import (
    CONF_PIN,
    CONF_DEVICE_PINS,
    CONF_CLIENT_ID,
    DOMAIN,
    LOCK_STATE_OPEN,
)

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

class HcuResetWaterVolume(HcuBaseEntity, ButtonEntity):
    """Representation of a button to reset the water volume."""

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
            channel_label=self._channel.get("label"), feature_name="Reset Water Volume"
        )
        self._attr_unique_id = (
            f"{self._device_id}_{self._channel_index}_reset_water_volume"
        )

    async def async_press(self) -> None:
        """Handle the button press action."""
        _LOGGER.info("Resetting water volume for %s", self.entity_id)
        try:
            await self._client.async_reset_water_volume(
                self._device_id, self._channel_index
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error(
                "Error resetting water volume for %s: %s", self.entity_id, err
            )

class HcuDoorPullLatchButton(HcuBaseEntity, ButtonEntity):
    """Representation of a button to trigger a door opener (e.g., HmIP-FDC)."""

    PLATFORM = Platform.BUTTON
    _attr_translation_key = "hcu_pull_latch"
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
        self._config_entry = coordinator.config_entry
        # Set entity name using the centralized naming helper
        self._set_entity_name(channel_label=self._channel.get("label"), feature_name="Pull Latch")
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_pull_latch"

        self._authorization_channel_index = None
        self._authorization_profile_label = None
    
    async def async_added_to_hass(self) -> None:
        """Run when entity is added to HA – now self.hass is available."""
        await super().async_added_to_hass()
        result = self._find_authorization_channel()
        if result is not None:
            self._authorization_channel_index, self._authorization_profile_label = result
    
    def _get_pin(self) -> str | None:
        """First device specified PIN, then global PIN as fallback."""
        config_entry = self.coordinator.config_entry
        pins = config_entry.options.get(CONF_DEVICE_PINS, {})
        if code := pins.get(self._attr_unique_id):
            _LOGGER.debug("Device '%s': using specified device pin", self.name)
            return code
        if global_pin := config_entry.data.get(CONF_PIN):
            _LOGGER.debug("Device '%s': using global PIN from config entry", self.name)
            return global_pin
        _LOGGER.debug("Device '%s': no PIN available", self.name)
        return None
        
    def _find_authorization_channel(self) -> tuple[int, str] | None:
        """Find the ACCESS_AUTHORIZATION_CHANNEL index that belongs to this switch channel."""
        client_id = self._config_entry.data.get(CONF_CLIENT_ID)
        client_id = self._config_entry.data.get(CONF_CLIENT_ID)
        if not client_id:
            _LOGGER.error(
                "No clientId found for this integration. Triggering reconfiguration flow.",
            )
            self._config_entry.async_start_reauth(self.hass)
            return None

        channels = self._device.get("functionalChannels", {})
        switch_group_index = self._channel.get("groupIndex")

        candidates: list[tuple[int, list[str]]] = []
        for ch_idx, ch_data in channels.items():
            if (
                ch_data.get("functionalChannelType") == "ACCESS_AUTHORIZATION_CHANNEL"
                and ch_data.get("groupIndex") == switch_group_index
            ):
                candidates.append((int(ch_idx), list(ch_data.get("groups") or [])))

        if not candidates:
            return None

        profiled: list[tuple[int, str]] = []
        client_authorized = False
        for ch_idx, group_ids in candidates:
            for group_id in group_ids:
                group = self._client.get_group_by_id(str(group_id)) or {}
                if (
                    group.get("type") == "ACCESS_AUTHORIZATION_PROFILE"
                    and group.get("authorizationPinAssigned") is True
                ):
                    authorized_clients = group.get("clientIds", [])
                    if client_id in authorized_clients:
                        client_authorized = True
                        profiled.append((ch_idx, group.get("label", "")))

        if not client_authorized:
            _LOGGER.error(
                "The Home Assistant Integration is not authorized to control device '%s' channel %s. "
                "Either the integration is not added to an Access Authorization Profile, "
                "or no PIN is stored in the profile. "
                "Please open the Homematic IP app, go to → More → Access authorisations, "
                "add the 'Home Assistant Integration' user to the authorisation profile and ensure a PIN is set, "
                "then reload the integration in Home Assistant.",
                self._device_id,
                self._channel_index,
            )
            return None
        
        ir.async_delete_issue(
            hass=self.hass,
            domain=DOMAIN,
            issue_id=f"access_authorization_{self._device_id}_{self._channel_index}",
        )    

        if len(profiled) > 1:
            _LOGGER.warning(
                "Multiple ACCESS_AUTHORIZATION_PROFILEs found for %s channel %s. "
                "Using first match.",
                self._device_id,
                self._channel_index,
            )

        return profiled[0]
    
    async def async_press(self) -> None:
        """Pull the door latch."""
        pin = self._get_pin()
        
        client_id = self._config_entry.data.get(CONF_CLIENT_ID)
        
        if not client_id:
            _LOGGER.error(
                "No clientId found for this integration. "
                "Please go to Settings → Integrations → Homematic IP HCU → Configure"
                "and re-authorize the integration.",
            )
            return
            
        if self._authorization_channel_index is None: 
            _LOGGER.error(
                "The Home Assistant Integration is not authorized to control device '%s' channel %s. "
                "Either the integration is not added to an Access Authorization Profile, "
                "or no PIN is stored in the profile. "
                "Please open the Homematic IP app, go to → More → Access authorisations, "
                "add the 'Home Assistant Integration' user to the authorisation profile and ensure a PIN is set, "
                "then reload the integration in Home Assistant.",
                self._device_id,
                self._channel_index,
            )
            ir.async_create_issue(
                hass=self.hass,
                domain=DOMAIN,
                issue_id=f"access_authorization_{self._device_id}_{self._channel_index}",
                is_fixable=True,
                severity=ir.IssueSeverity.ERROR,
                translation_key="access_authorization",
                translation_placeholders={
                    "device_name": self._device.get("label", self._device_id),
                    "channel_index": str(self._channel_index),
                },
                data={
                    "device_name": self._device.get("label", self._device_id),
                    "channel_index": self._channel_index,
                },
            )
            return

        ir.async_delete_issue(
            hass=self.hass,
            domain=DOMAIN,
            issue_id=f"access_authorization_{self._device_id}_{self._channel_index}",
        )        
            
        _LOGGER.debug("Triggering pull latch for %s with ACCESS_AUTHORIZATION_PROFILE %s", self.entity_id, self._authorization_profile_label)
        try:
            await self._client.async_pull_latch(
                self._device_id, self._authorization_channel_index, pin=pin
            )
        except HcuApiError as err:
            err_type = handle_lock_api_error(err, self.name, pin)
            if err_type == "invalid_pin" and pin:
                ir.async_create_issue(
                    hass=self.hass,
                    domain=DOMAIN,
                    issue_id=f"pin_failed_{self._device_id}",
                    is_fixable=True,
                    severity=ir.IssueSeverity.ERROR,
                    translation_key="pin_failed",
                    data={
                        "entry_id": self._config_entry.entry_id,
                        "device_name": self.name,
                    },
                    translation_placeholders={"device_name": self.name},
                )
        
            if not err_type:
                _LOGGER.error(
                    "Error triggering pull latch for %s: %s", self.name, err
                )
        except ConnectionError as err:
            _LOGGER.error(
                "Connection failed while triggering pull latch for %s: %s", self.name, err
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
        except HcuApiError as err:
            _LOGGER.error(
                "Error triggering door impulse for %s: %s", self.entity_id, err
            )
        except ConnectionError as err:
            _LOGGER.error(
                "Connection failed while triggering door impulse for %s: %s", self.entity_id, err
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
        except HcuApiError as err:
            _LOGGER.error(
                "Error triggering identify for %s: %s", self.entity_id, err
            )
        except ConnectionError as err:
            _LOGGER.error(
                "Connection failed while triggering identify for %s: %s", self.entity_id, err
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
        **kwargs: Any,
    ):
        """Initialize the door unlatch button."""
        super().__init__(coordinator, client, device_data, channel_index, **kwargs)
        self._config_entry = coordinator.config_entry
        self._set_entity_name(channel_label=self._channel.get("label"), feature_name="Unlatch")
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_unlatch"
    
    def _get_pin_from_lock(self) -> str | None:
        """Get PIN from associated lock entity, then global PIN as fallback."""
        for lock in self.coordinator.entities.get(Platform.LOCK, []):
            if lock._device_id == self._device_id and lock._channel_index == self._channel_index:
                if pin := lock._get_pin():
                    _LOGGER.debug("Device '%s': using PIN from associated lock", self.name)
                    return pin
        if global_pin := self._config_entry.data.get(CONF_PIN):
            _LOGGER.debug("Device '%s': using global PIN from config entry", self.name)
            return global_pin
        _LOGGER.debug("Device '%s': no PIN available", self.name)
        return None
    
    async def async_press(self) -> None:
        """Pull the door latch to open the door."""
        pin = self._get_pin_from_lock()
        _LOGGER.info("Triggering unlatch for %s", self.name)
        
        try:
            await self._client.async_set_lock_state(
                self._device_id, self._channel_index, state=LOCK_STATE_OPEN, pin=pin
            )
        except HcuApiError as err:
            err_type = handle_lock_api_error(err, self.name, pin)
            if err_type == "invalid_pin" and pin:
                ir.async_create_issue(
                    hass=self.hass,
                    domain=DOMAIN,
                    issue_id=f"pin_failed_{self._device_id}",
                    is_fixable=True,
                    severity=ir.IssueSeverity.ERROR,
                    translation_key="pin_failed",
                    data={
                        "entry_id": self._config_entry.entry_id,
                        "device_name": self.name,
                    },
                    translation_placeholders={"device_name": self.name},
                )
            
            if not err_type:
                _LOGGER.error(
                    "Error triggering unlatch for %s: %s", self.name, err
                )
        except ConnectionError as err:
            _LOGGER.error(
                "Connection failed while triggering unlatch for %s: %s", self.name, err
            )
