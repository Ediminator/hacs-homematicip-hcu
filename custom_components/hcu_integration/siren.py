# custom_components/hcu_integration/siren.py
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.siren import (
    ATTR_DURATION,
    ATTR_TONE,
    SirenEntity,
    SirenEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .api import HcuApiClient, HcuApiError
from .const import (
    CHANNEL_TYPE_ALARM_SIREN,
    DEFAULT_SIREN_DURATION,
    DEFAULT_SIREN_TONE,
    HMIP_SIREN_TONES,
)
from .entity import HcuBaseEntity

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the siren platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.SIREN):
        async_add_entities(entities)


class HcuSiren(HcuBaseEntity, SirenEntity):
    """Representation of a Homematic IP HCU alarm siren."""

    PLATFORM = Platform.SIREN

    _attr_supported_features = (
        SirenEntityFeature.TURN_ON
        | SirenEntityFeature.TURN_OFF
        | SirenEntityFeature.TONES
        | SirenEntityFeature.DURATION
    )

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        # Set entity name using the centralized naming helper
        self._set_entity_name(channel_label=self._channel.get("label"))

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_siren"
        self._attr_available_tones = list(HMIP_SIREN_TONES)

        # Initial state sync
        self._attr_is_on = self._channel.get("acousticAlarmActive", False)

        # Timer for auto-off
        self._auto_off_timer = None

    @property
    def available(self) -> bool:
        """Return True if the entity is available.

        Override to add diagnostic logging for troubleshooting siren availability.

        ALARM_SIREN_CHANNEL often has minimal data (only metadata fields like
        functionalChannelType, groups, channelRole) or may be omitted entirely
        from HCU state updates. This is normal behavior - the channel doesn't
        need state fields when the siren is inactive. The base class now properly
        handles this by not checking for channel data presence.
        """
        # Validate channel type if present (diagnostic check only)
        channel_type = self._channel.get("functionalChannelType")
        if channel_type is not None and channel_type != CHANNEL_TYPE_ALARM_SIREN:
            _LOGGER.warning(
                "Siren %s: unexpected channel type '%s', expected '%s'",
                self._device_id,
                channel_type,
                CHANNEL_TYPE_ALARM_SIREN,
            )

        # Call base implementation (which handles all availability logic correctly)
        is_available = super().available

        # Add diagnostic logging for unavailable states
        if not is_available:
            if not self._client.is_connected:
                _LOGGER.debug(
                    "Siren %s unavailable: client not connected", self._device_id
                )
            elif not self._device:
                _LOGGER.warning(
                    "Siren %s unavailable: device data missing from state",
                    self._device_id,
                )
            else:
                _LOGGER.debug(
                    "Siren %s unavailable: device unreachable (battery-powered device may be sleeping)",
                    self._device_id,
                )

        return is_available

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if not self._attr_assumed_state:
            self._attr_is_on = self._channel.get("acousticAlarmActive", False)
        super()._handle_coordinator_update()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the siren on."""
        tone = kwargs.get(ATTR_TONE, DEFAULT_SIREN_TONE)
        duration = kwargs.get(ATTR_DURATION, DEFAULT_SIREN_DURATION)

        if tone not in self._attr_available_tones:
            _LOGGER.error("Invalid tone specified for siren %s: %s", self.name, tone)
            return

        _LOGGER.info(
            "Activating siren %s with tone '%s' for %d seconds",
            self.name,
            tone,
            duration,
        )

        # Cancel any existing auto-off timer
        if self._auto_off_timer:
            self._auto_off_timer()
            self._auto_off_timer = None

        # Set optimistic state
        self._attr_is_on = True
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            await self._client.async_set_sound_file(
                device_id=self._device_id,
                channel_index=int(self._channel_index),
                sound_file=tone,
                volume=1.0,  # Max volume
                duration=duration,
            )
            self._attr_assumed_state = False
            self.async_write_ha_state()
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to turn on siren %s: %s", self.name, err)
            # Revert state on error
            self._attr_is_on = False
            self._attr_assumed_state = False
            self.async_write_ha_state()
            raise

        # Schedule auto-off
        self._auto_off_timer = async_call_later(
            self.hass, duration, lambda _: self.hass.create_task(self.async_turn_off())
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the siren off."""
        _LOGGER.info("Deactivating siren %s", self.name)

        # Cancel any existing auto-off timer
        if self._auto_off_timer:
            self._auto_off_timer()
            self._auto_off_timer = None

        # Set optimistic state
        self._attr_is_on = False
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            await self._client.async_set_sound_file(
                device_id=self._device_id,
                channel_index=int(self._channel_index),
                sound_file="DISABLE_ACOUSTIC_SIGNAL",
                volume=0.0,
                duration=0,
            )
            self._attr_assumed_state = False
            self.async_write_ha_state()
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to turn off siren %s: %s", self.name, err)
            # Revert state on error (assume it's still on)
            self._attr_is_on = True
            self._attr_assumed_state = False
            self.async_write_ha_state()
            raise
