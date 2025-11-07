# custom_components/hcu_integration/siren.py
from typing import TYPE_CHECKING, Any
import logging

from homeassistant.components.siren import SirenEntity, SirenEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    """Set up the siren platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.SIREN):
        async_add_entities(entities)


class HcuSiren(HcuBaseEntity, SirenEntity):
    """Representation of a Homematic IP HCU alarm siren."""

    PLATFORM = Platform.SIREN

    _attr_supported_features = SirenEntityFeature.TURN_ON | SirenEntityFeature.TURN_OFF

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

    @property
    def is_on(self) -> bool:
        """Return True if the siren is on."""
        return self._channel.get("on", False)

    async def _async_set_siren_state(self, turn_on: bool) -> None:
        """Set the state of the siren."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            on_level = 1.0 if turn_on else 0.0
            await self._client.async_set_switch_state(
                self._device_id, self._channel_index, turn_on, on_level=on_level
            )
        except (HcuApiError, ConnectionError) as err:
            action = "on" if turn_on else "off"
            _LOGGER.error("Failed to turn %s siren %s: %s", action, self.name, err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the siren on."""
        await self._async_set_siren_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the siren off."""
        await self._async_set_siren_state(False)
