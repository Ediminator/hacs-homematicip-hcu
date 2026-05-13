# custom_components/hcu_integration/text.py
"""Text entities for the HCU integration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_PINS
from .entity import HcuBaseEntity

if TYPE_CHECKING:
    from .api import HcuApiClient
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Set up the text platform from a config entry."""
        coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
            config_entry.entry_id
        ]
        if entities := coordinator.entities.get(Platform.TEXT):
            async_add_entities(entities)
    
class HcuDevicePin(HcuBaseEntity, TextEntity):
    """PIN input field for a Pull Latch button."""

    PLATFORM = Platform.TEXT
    _attr_translation_key = "hcu_Device_pin"
    _attr_icon = "mdi:lock-outline"
    _attr_mode = TextMode.PASSWORD
    _attr_native_min = 0
    _attr_native_max = 20
    _attr_entity_category = EntityCategory.CONFIG


    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: "HcuApiClient",
        device_data: dict,
        channel_index: str,
    ) -> None:
        super().__init__(coordinator, client, device_data, channel_index)
        self._config_entry = coordinator.config_entry
        self._set_entity_name(
            channel_label=self._channel.get("label"), feature_name="Device PIN"
        )
        self._attr_unique_id = f"{self._device_id}_{channel_index}_device_pin"
        self._pin_key = f"{self._device_id}_{channel_index}_device_latch"
        
    @property
    def native_value(self) -> str:
        return self._config_entry.options.get(CONF_DEVICE_PINS, {}).get(
            self._pin_key, ""
        )

    async def async_set_value(self, value: str) -> None:
        new_pins = dict(self._config_entry.options.get(CONF_DEVICE_PINS, {}))
        if value:
            new_pins[self._pin_key] = value
        else:
            new_pins.pop(self._pin_key, None)
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            options={**self._config_entry.options, CONF_DEVICE_PINS: new_pins},
        )
        self.async_write_ha_state()