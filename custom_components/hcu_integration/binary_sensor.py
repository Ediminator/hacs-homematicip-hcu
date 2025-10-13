from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import HcuApiClient
from .entity import HcuBaseEntity

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.BINARY_SENSOR):
        async_add_entities(entities)


class HcuBinarySensor(HcuBaseEntity, BinarySensorEntity):
    """
    Representation of a generic Homematic IP HCU binary sensor.
    This class is the foundation for all binary sensors in the integration.
    """

    PLATFORM = Platform.BINARY_SENSOR
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
        feature: str,
        mapping: dict,
    ):
        super().__init__(coordinator, client, device_data, channel_index)
        self._feature = feature
        self._on_state = mapping.get("on_state")

        self._attr_name = mapping["name"]
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_{self._feature}"
        self._attr_device_class = mapping.get("device_class")

        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping[
                "entity_registry_enabled_default"
            ]

    @property
    def is_on(self) -> bool:
        """
        Return true if the binary sensor is on.
        """
        value = self._channel.get(self._feature)
        if self._on_state:
            return value == self._on_state
        return bool(value)


class HcuWindowBinarySensor(HcuBinarySensor):
    """
    Representation of a Homematic IP HCU window sensor.
    This class provides specialized logic for window sensors.
    """

    @property
    def is_on(self) -> bool:
        """
        Return true if the window is open or tilted.
        """
        return self._channel.get(self._feature) in ("OPEN", "TILTED")


class HcuSmokeBinarySensor(HcuBinarySensor):
    """
    Representation of a Homematic IP HCU smoke detector.
    This class provides specialized logic for smoke detectors.
    """

    @property
    def is_on(self) -> bool:
        """
        Return true if the smoke detector alarm is active.
        """
        return self._channel.get(self._feature) in ("PRIMARY_ALARM", "SECONDARY_ALARM")


class HcuUnreachBinarySensor(HcuBinarySensor):
    """
    Representation of a Homematic IP HCU device's reachability.
    This class provides specialized logic for the 'unreach' status.
    """

    @property
    def is_on(self) -> bool:
        """
        Return true if the device is connected.
        The API's 'unreach' property is `True` when the device is unreachable.
        For Home Assistant's `connectivity` device class, `is_on` should be
        `True` when the device is connected, so we must invert the value.
        """
        return not self._channel.get(self._feature, False)