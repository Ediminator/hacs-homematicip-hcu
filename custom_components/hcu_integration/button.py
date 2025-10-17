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

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the button platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][config_entry.entry_id]
    if entities := coordinator.entities.get(Platform.BUTTON):
        async_add_entities(entities)


class HcuResetEnergyButton(HcuBaseEntity, ButtonEntity):
    """Representation of a button to reset the energy counter."""
    PLATFORM = Platform.BUTTON
    _attr_has_entity_name = True
    _attr_icon = "mdi:reload"
    _attr_name = "Reset Energy Counter"

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
    ):
        """Initialize the reset button."""
        super().__init__(coordinator, client, device_data, channel_index)
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_reset_energy_counter"

    async def async_press(self) -> None:
        """Handle the button press action."""
        _LOGGER.info("Resetting energy counter for %s", self.entity_id)
        try:
            await self._client.async_reset_energy_counter(
                self._device_id, self._channel_index
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Error resetting energy counter for %s: %s", self.entity_id, err)
