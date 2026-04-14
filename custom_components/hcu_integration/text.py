# custom_components/hcu_integration/text.py
"""Text entities for Homematic IP HCU."""
from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PIN

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)

_PIN_PATTERN = re.compile(r"^\d{4}$")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the text platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]

    async_add_entities([HcuPinTextEntity(coordinator)])


class HcuPinTextEntity(TextEntity):
    """Representation of a text entity to store a 4-digit PIN."""

    _attr_has_entity_name = True
    _attr_name = "PIN"
    _attr_icon = "mdi:form-textbox-password"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = "password"
    _attr_native_min = 4
    _attr_native_max = 4
    _attr_pattern = r"^\d{4}$"
    _attr_should_poll = False

    def __init__(self, coordinator: "HcuCoordinator") -> None:
        """Initialize the PIN text entity."""
        self._coordinator = coordinator
        self._config_entry = coordinator.config_entry

        self._attr_unique_id = f"{self._config_entry.entry_id}_pin"
        self._attr_native_value = self._config_entry.data.get(CONF_PIN, "")

    async def async_set_value(self, value: str) -> None:
        """Set and persist the PIN in the config entry."""
        value = value.strip()

        if not _PIN_PATTERN.fullmatch(value):
            raise HomeAssistantError("PIN must consist of exactly 4 digits.")

        new_data = {
            **self._config_entry.data,
            CONF_PIN: value,
        }

        self.hass.config_entries.async_update_entry(
            self._config_entry,
            data=new_data,
        )

        self._attr_native_value = value
        self.async_write_ha_state()

        _LOGGER.info(
            "PIN for config entry %s updated via text entity",
            self._config_entry.entry_id,
        )