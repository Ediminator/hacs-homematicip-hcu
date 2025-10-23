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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            await self._client.async_set_switch_state(
                self._device_id, self._channel_index, True, on_level=1.0
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to turn on switch %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            await self._client.async_set_switch_state(
                self._device_id, self._channel_index, False, on_level=0.0
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to turn off switch %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

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
        **kwargs: Any,
    ):
        super().__init__(coordinator, client, device_data, channel_index)

        # REFACTOR: Correctly call the centralized naming helper.
        self._set_entity_name(channel_label=self._channel.get("label"))

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_watering"

    @property
    def is_on(self) -> bool:
        return self._channel.get("wateringActive", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the watering on."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            await self._client.async_set_watering_switch_state(
                self._device_id, self._channel_index, True
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to turn on watering switch %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the watering off."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            await self._client.async_set_watering_switch_state(
                self._device_id, self._channel_index, False
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to turn off watering switch %s: %s", self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()