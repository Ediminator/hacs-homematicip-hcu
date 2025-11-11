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
        self._attr_available_tones = list(HMIP_SIREN_TONES)
        self._init_switch_state()

        # Find the ALARM_SWITCHING group for this siren
        self._alarm_group_id = self._find_alarm_switching_group()

        # Log diagnostic information for troubleshooting
        _LOGGER.debug(
            "HcuSiren initialized: device=%s, channel=%s, has_acousticAlarmActive=%s, channel_type=%s, alarm_group=%s",
            self._device_id,
            self._channel_index,
            self._state_channel_key in self._channel,
            self._channel.get("functionalChannelType"),
            self._alarm_group_id,
        )

    def _find_alarm_switching_group(self) -> str | None:
        """Find the ALARM_SWITCHING group that contains this siren channel.

        Returns:
            The group ID if found, None otherwise
        """
        # Get all groups from coordinator state
        groups = self.coordinator.data.get("groups", {})

        # Find ALARM_SWITCHING group(s) containing this device/channel
        matching_groups = []
        for group_id, group_data in groups.items():
            if group_data.get("type") == "ALARM_SWITCHING":
                # Check if this group contains our siren channel
                for channel in group_data.get("channels", []):
                    if (
                        channel.get("deviceId") == self._device_id
                        and str(channel.get("channelIndex")) == str(self._channel_index)
                    ):
                        matching_groups.append((group_id, group_data.get("label", group_id)))
                        break

        # Handle results
        if not matching_groups:
            _LOGGER.warning(
                "No ALARM_SWITCHING group found for siren %s channel %s. "
                "Siren control may not work properly.",
                self._device_id,
                self._channel_index,
            )
            return None

        if len(matching_groups) > 1:
            _LOGGER.warning(
                "Multiple ALARM_SWITCHING groups found for siren %s: %s. "
                "Using first group '%s' (%s). This may indicate a configuration issue in the HCU.",
                self._device_id,
                ", ".join(f"'{label}' ({gid})" for gid, label in matching_groups),
                matching_groups[0][1],
                matching_groups[0][0],
            )

        group_id, group_label = matching_groups[0]
        _LOGGER.info(
            "Found ALARM_SWITCHING group '%s' (%s) for siren %s",
            group_label,
            group_id,
            self._device_id,
        )
        return group_id

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
                CHANNEL_TYPE_ALARM_SIREN
            )

        # Call base implementation (which handles all availability logic correctly)
        is_available = super().available

        # Add diagnostic logging for unavailable states
        if not is_available:
            if not self._client.is_connected:
                _LOGGER.debug("Siren %s unavailable: client not connected", self._device_id)
            elif not self._device:
                _LOGGER.warning("Siren %s unavailable: device data missing from state", self._device_id)
            else:
                _LOGGER.debug(
                    "Siren %s unavailable: device unreachable (battery-powered device may be sleeping)",
                    self._device_id
                )

        return is_available

    def _validate_alarm_group_configured(self) -> None:
        """Validate that an ALARM_SWITCHING group is configured for this siren.

        Raises:
            HcuApiError: If no ALARM_SWITCHING group is found
        """
        if not self._alarm_group_id:
            _LOGGER.error(
                "Cannot control siren %s: No ALARM_SWITCHING group found. "
                "The siren may not be properly configured in the HCU.",
                self.name,
            )
            raise HcuApiError("No ALARM_SWITCHING group found for siren")

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
        # Validate ALARM_SWITCHING group is configured
        self._validate_alarm_group_configured()

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

        _LOGGER.info(
            "Activating siren %s via ALARM_SWITCHING group with tone=%s, duration=%s",
            self.name,
            tone,
            duration,
        )

        # Activate the siren via ALARM_SWITCHING group
        # Use BLINKING_ALTERNATELY_REPEATING as default optical signal (based on API docs)
        await self._async_execute_with_state_management(
            target_state=True,
            api_call=self._client.async_set_alarm_switching_group_state(
                group_id=self._alarm_group_id,
                on=True,
                signal_acoustic=tone,
                signal_optical="BLINKING_ALTERNATELY_REPEATING",
                on_time=duration,
            ),
            action="turn on",
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the siren off."""
        # Validate ALARM_SWITCHING group is configured
        self._validate_alarm_group_configured()

        _LOGGER.info("Deactivating siren %s via ALARM_SWITCHING group", self.name)

        # Deactivate the siren via ALARM_SWITCHING group
        await self._async_execute_with_state_management(
            target_state=False,
            api_call=self._client.async_set_alarm_switching_group_state(
                group_id=self._alarm_group_id,
                on=False,
            ),
            action="turn off",
        )
