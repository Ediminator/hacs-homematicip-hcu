# custom_components/hcu_integration/switch.py
from typing import TYPE_CHECKING, Any
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import HMIP_DEVICE_TYPE_TO_DEVICE_CLASS
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
    """Set up the switch platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.SWITCH):
        async_add_entities(entities)


class HcuSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of a standard Homematic IP HCU switch."""

    PLATFORM = Platform.SWITCH

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
        **kwargs: Any,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        # REFACTOR: Correctly call the centralized naming helper.
        self._set_entity_name(channel_label=self._channel.get("label"))

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_on"

        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TYPE_TO_DEVICE_CLASS.get(device_type)

    @property
    def is_on(self) -> bool:
        return self._channel.get("on", False)

    async def _async_set_switch_state(self, turn_on: bool) -> None:
        """Set the state of the switch."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            on_level = 1.0 if turn_on else 0.0
            await self._client.async_set_switch_state(
                self._device_id, self._channel_index, turn_on, on_level=on_level
            )
        except (HcuApiError, ConnectionError) as err:
            action = "on" if turn_on else "off"
            _LOGGER.error("Failed to turn %s switch %s: %s", action, self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_switch_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_switch_state(False)

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


class HcuWateringSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of a Homematic IP HCU watering controller."""

    PLATFORM = Platform.SWITCH
    _attr_icon = "mdi:water"

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        # REFACTOR: Correctly call the centralized naming helper.
        self._set_entity_name(channel_label=self._channel.get("label"))

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_watering"

    @property
    def is_on(self) -> bool:
        return self._channel.get("wateringActive", False)

    async def _async_set_watering_state(self, turn_on: bool) -> None:
        """Set the state of the watering switch."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            await self._client.async_set_watering_switch_state(
                self._device_id, self._channel_index, turn_on
            )
        except (HcuApiError, ConnectionError) as err:
            action = "on" if turn_on else "off"
            _LOGGER.error("Failed to turn %s watering switch %s: %s", action, self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the watering on."""
        await self._async_set_watering_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the watering off."""
        await self._async_set_watering_state(False)
