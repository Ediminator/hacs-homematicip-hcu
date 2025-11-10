# custom_components/hcu_integration/siren.py
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.siren import (
    SirenEntity,
    SirenEntityFeature,
    ATTR_TONE,
    ATTR_DURATION,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HcuBaseEntity, SwitchStateMixin
from .api import HcuApiClient, HcuApiError
from .const import (
    HMIP_SIREN_TONES,
    DEFAULT_SIREN_TONE,
    DEFAULT_SIREN_DURATION,
    HMIP_CHANNEL_KEY_ACOUSTIC_ALARM_ACTIVE,
    CHANNEL_TYPE_ALARM_SIREN,
)

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


class HcuSiren(SwitchStateMixin, HcuBaseEntity, SirenEntity):
    """Representation of a Homematic IP HCU alarm siren."""

    PLATFORM = Platform.SIREN

    # Alarm sirens use 'acousticAlarmActive' instead of 'on' for state
    _state_channel_key = HMIP_CHANNEL_KEY_ACOUSTIC_ALARM_ACTIVE

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
        self._attr_available_tones = HMIP_SIREN_TONES
        self._init_switch_state()

        # Log diagnostic information for troubleshooting
        _LOGGER.debug(
            "HcuSiren initialized: device=%s, channel=%s, has_acousticAlarmActive=%s, channel_type=%s",
            self._device_id,
            self._channel_index,
            self._state_channel_key in self._channel,
            self._channel.get("functionalChannelType"),
        )

    @property
    def available(self) -> bool:
        """Return True if the entity is available.

        Override to handle sparse ALARM_SIREN_CHANNEL data and add diagnostic logging.

        ALARM_SIREN_CHANNEL often has minimal data (only metadata fields like
        functionalChannelType, groups, channelRole) or may be omitted entirely
        from HCU state updates. This is normal behavior - the channel doesn't
        need state fields when the siren is inactive.
        """
        if not self._client.is_connected:
            _LOGGER.debug("Siren %s unavailable: client not connected", self._device_id)
            return False

        if not self._device:
            _LOGGER.warning(
                "Siren %s unavailable: device data missing from state",
                self._device_id
            )
            return False

        # For ALARM_SIREN_CHANNEL, the channel data may be sparse or missing entirely.
        # This is normal - the HCU may not include the channel in every update.
        # Only log warning if channel type is present but incorrect (not during sparse updates).
        channel_type = self._channel.get("functionalChannelType")
        if channel_type is not None and channel_type != CHANNEL_TYPE_ALARM_SIREN:
            _LOGGER.warning(
                "Siren %s: unexpected channel type '%s', expected '%s'",
                self._device_id,
                channel_type,
                CHANNEL_TYPE_ALARM_SIREN
            )

        # Siren availability is based on device reachability, not channel data
        # Check permanentlyReachable flag
        if self._device.get("permanentlyReachable", False):
            return True

        # For battery-powered devices, check maintenance channel reachability
        maintenance_channel = self._device.get("functionalChannels", {}).get("0", {})
        is_reachable = not maintenance_channel.get("unreach", False)

        if not is_reachable:
            _LOGGER.debug(
                "Siren %s unavailable: device unreachable (battery-powered device may be sleeping)",
                self._device_id
            )

        return is_reachable

    def _sync_switch_state_from_coordinator(self) -> None:
        """Sync switch state from coordinator data with diagnostic logging.

        The parent implementation correctly defaults to False when acousticAlarmActive
        is missing, which is the expected behavior for an inactive siren.
        """
        if self._state_channel_key not in self._channel:
            _LOGGER.debug(
                "Siren %s: '%s' field missing, defaulting to 'off'",
                self._device_id,
                self._state_channel_key,
            )
        super()._sync_switch_state_from_coordinator()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator.

        Don't sync state from coordinator when in assumed_state mode
        (i.e., we just triggered the siren and are waiting for the sound to complete).
        This prevents the coordinator from incorrectly reporting the siren as 'off'
        while it's still playing the acoustic signal.
        """
        if not self._attr_assumed_state:
            self._sync_switch_state_from_coordinator()
        super()._handle_coordinator_update()

    async def _call_switch_api(self, turn_on: bool) -> None:
        """Call the API to set the siren state."""
        on_level = 1.0 if turn_on else 0.0
        await self._client.async_set_switch_state(
            self._device_id, self._channel_index, turn_on, on_level=on_level
        )

    async def _async_execute_with_state_management(
        self, target_state: bool, api_call: Any, action: str
    ) -> None:
        """Execute API call with optimistic state management and error handling.

        Args:
            target_state: The desired state (True for on, False for off)
            api_call: Coroutine to execute for the API call
            action: Action name for logging ("turn on" or "turn off")
        """
        # Set optimistic state immediately
        self._attr_is_on = target_state
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            await api_call
            # API call succeeded - clear assumed_state to allow coordinator updates
            self._attr_assumed_state = False
            self.async_write_ha_state()
        except (HcuApiError, ConnectionError) as err:
            # Revert state on error
            _LOGGER.error("Failed to %s siren %s: %s", action, self.name, err)
            self._attr_is_on = not target_state
            self._attr_assumed_state = False
            self.async_write_ha_state()
            raise

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the siren on with optional tone and duration.

        Args:
            **kwargs: Optional parameters including:
                - tone: The acoustic signal to play (from HMIP_SIREN_TONES)
                - duration: Duration in seconds (default: 10.0)
        """
        tone = kwargs.get(ATTR_TONE, DEFAULT_SIREN_TONE)
        duration = kwargs.get(ATTR_DURATION, DEFAULT_SIREN_DURATION)

        # Validate tone
        if tone not in HMIP_SIREN_TONES:
            _LOGGER.warning(
                "Invalid tone '%s' for siren %s. Using default tone '%s'.",
                tone,
                self.name,
                DEFAULT_SIREN_TONE,
            )
            tone = DEFAULT_SIREN_TONE

        # Play the acoustic signal using the sound file API
        # Volume is set to 1.0 (100%) for siren activation
        await self._async_execute_with_state_management(
            target_state=True,
            api_call=self._client.async_set_sound_file(
                self._device_id,
                self._channel_index,
                sound_file=tone,
                volume=1.0,
                duration=duration,
            ),
            action="turn on",
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the siren off."""
        await self._async_execute_with_state_management(
            target_state=False,
            api_call=self._call_switch_api(False),
            action="turn off",
        )
