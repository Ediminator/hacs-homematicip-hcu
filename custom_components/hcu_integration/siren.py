# custom_components/hcu_integration/siren.py
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
from .api import HcuApiClient
from .const import HMIP_SIREN_TONES, DEFAULT_SIREN_TONE, DEFAULT_SIREN_DURATION

if TYPE_CHECKING:
    from . import HcuCoordinator


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

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._sync_switch_state_from_coordinator()
        super()._handle_coordinator_update()

    async def _call_switch_api(self, turn_on: bool) -> None:
        """Call the API to set the siren state."""
        on_level = 1.0 if turn_on else 0.0
        await self._client.async_set_switch_state(
            self._device_id, self._channel_index, turn_on, on_level=on_level
        )

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
            tone = DEFAULT_SIREN_TONE

        # Play the acoustic signal using the sound file API
        # Volume is set to 1.0 (100%) for siren activation
        await self._client.async_set_sound_file(
            self._device_id,
            self._channel_index,
            sound_file=tone,
            volume=1.0,
            duration=duration,
        )

        # Update optimistic state
        await self._async_set_optimistic_state(True, "siren")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the siren off."""
        await self._async_set_optimistic_state(False, "siren")
