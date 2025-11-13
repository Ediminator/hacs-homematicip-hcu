# custom_components/hcu_integration/switch.py
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import HMIP_DEVICE_TYPE_TO_DEVICE_CLASS
from .entity import HcuBaseEntity, SwitchStateMixin, HcuSwitchingGroupBase
from .api import HcuApiClient

if TYPE_CHECKING:
    from . import HcuCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.SWITCH):
        async_add_entities(entities)


class HcuSwitch(SwitchStateMixin, HcuBaseEntity, SwitchEntity):
    """Representation of a standard Homematic IP HCU switch."""

    PLATFORM = Platform.SWITCH

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        self._set_entity_name(channel_label=self._channel.get("label"))

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_on"

        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TYPE_TO_DEVICE_CLASS.get(device_type)
        self._init_switch_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._sync_switch_state_from_coordinator()
        super()._handle_coordinator_update()

    async def _call_switch_api(self, turn_on: bool) -> None:
        """Call the API to set the switch state."""
        await self._client.async_set_switch_state(
            self._device_id, self._channel_index, turn_on
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_optimistic_state(True, "switch")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_optimistic_state(False, "switch")

    async def async_play_sound(
        self, sound_file: str, volume: float, duration: float
    ) -> None:
        """Service call to play a sound on this device."""
        await self._client.async_set_sound_file(
            device_id=self._device_id,
            channel_index=self._channel_index,
            sound_file=sound_file,
            volume=volume,
            duration=duration,
        )


class HcuWateringSwitch(SwitchStateMixin, HcuBaseEntity, SwitchEntity):
    """Representation of a Homematic IP HCU watering controller."""

    PLATFORM = Platform.SWITCH
    _attr_icon = "mdi:water"
    _state_channel_key = "wateringActive"

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        self._set_entity_name(channel_label=self._channel.get("label"))

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_watering"
        self._init_switch_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._sync_switch_state_from_coordinator()
        super()._handle_coordinator_update()

    async def _call_switch_api(self, turn_on: bool) -> None:
        """Call the API to set the watering switch state."""
        await self._client.async_set_watering_switch_state(
            self._device_id, self._channel_index, turn_on
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the watering on."""
        await self._async_set_optimistic_state(True, "watering switch")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the watering off."""
        await self._async_set_optimistic_state(False, "watering switch")


class HcuSwitchGroup(HcuSwitchingGroupBase, SwitchEntity):
    """Representation of a Homematic IP HCU switching group."""

    PLATFORM = Platform.SWITCH
