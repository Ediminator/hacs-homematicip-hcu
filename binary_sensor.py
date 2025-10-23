# custom_components/hcu_integration/binary_sensor.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import HcuApiClient
from .entity import HcuBaseEntity, HcuHomeBaseEntity

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

        # REFACTOR: Correctly call the centralized naming helper for feature entities.
        self._set_entity_name(
            channel_label=self._channel.get("label"), feature_name=mapping["name"]
        )

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


class HcuVacationModeBinarySensor(HcuHomeBaseEntity, BinarySensorEntity):
    """Representation of the HCU's system-wide Vacation Mode."""

    PLATFORM = Platform.BINARY_SENSOR
    _attr_has_entity_name = False
    _attr_name = "Vacation Mode"
    _attr_icon = "mdi:palm-tree"

    def __init__(self, coordinator: "HcuCoordinator", client: HcuApiClient):
        """Initialize the Vacation Mode sensor."""
        super().__init__(coordinator, client)
        self._attr_unique_id = f"{self._hcu_device_id}_vacation_mode"
        self._update_attributes()

    @property
    def is_on(self) -> bool:
        """Return true if vacation mode is active."""
        heating_home = self._home.get("functionalHomes", {}).get("HEATING", {})
        return heating_home.get("absenceType") == "VACATION"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the vacation mode sensor."""
        return {
            "end_time": self._attr_extra_state_attributes.get("end_time"),
            "target_temperature": self._attr_extra_state_attributes.get(
                "target_temperature"
            ),
        }

    def _update_attributes(self) -> None:
        """Update the entity's attributes."""
        heating_home = self._home.get("functionalHomes", {}).get("HEATING", {})
        end_time_ts = heating_home.get("absenceEndTime")

        end_time = None
        if end_time_ts and end_time_ts > 0:
            end_time = dt_util.utc_from_timestamp(end_time_ts / 1000)

        self._attr_extra_state_attributes = {
            "end_time": end_time.isoformat() if end_time else None,
            "target_temperature": heating_home.get("setPointTemperature"),
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_attributes()
        super()._handle_coordinator_update()