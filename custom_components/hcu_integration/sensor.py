from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceAction

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
    """Set up the sensor platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.SENSOR):
        async_add_entities(entities)


class HcuHomeSensor(HcuHomeBaseEntity, SensorEntity):
    """Representation of a sensor tied to the HCU 'home' object."""

    PLATFORM = Platform.SENSOR
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        feature: str,
        mapping: dict,
    ):
        super().__init__(coordinator, client)
        self._feature = feature

        self._attr_name = f"Homematic IP HCU {mapping['name']}"
        self._attr_unique_id = f"{self._hcu_device_id}_{self._feature}"
        self._attr_device_class = mapping.get("device_class")
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_state_class = mapping.get("state_class")
        self._attr_icon = mapping.get("icon")

        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping[
                "entity_registry_enabled_default"
            ]

    @property
    def native_value(self) -> float | str | None:
        value = self._home.get(self._feature)
        if value is None:
            return None

        if self._feature == "carrierSense":
            return round(value * 100.0, 1)

        return value


class HcuGenericSensor(HcuBaseEntity, SensorEntity):
    """Representation of a generic HCU sensor for a physical device."""

    PLATFORM = Platform.SENSOR
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

        self._attr_name = mapping["name"]
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_{self._feature}"
        self._attr_device_class = mapping.get("device_class")
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_state_class = mapping.get("state_class")
        self._attr_icon = mapping.get("icon")

        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping[
                "entity_registry_enabled_default"
            ]

    @property
    def native_value(self) -> float | str | None:
        """Return the sensor value, with special handling for certain features."""
        if self._feature in ("actualTemperature", "valveActualTemperature"):
            return self._channel.get("actualTemperature") or self._channel.get(
                "valveActualTemperature"
            )

        value = self._channel.get(self._feature)
        if value is None:
            return None
            
        if self._feature == "valvePosition":
            return round(value * 100.0, 1)
        if self._feature == "vaporAmount":
            return round(value, 2)

        return value

    async def async_get_entity_actions(self) -> list[DeviceAction]:
        """Return the available actions for this entity."""
        if self._feature == "energyCounter":
            return [
                DeviceAction(
                    key="reset_energy",
                    translation_key="reset_energy",
                )
            ]
        return []

    async def async_run_entity_action(self, key: str, **kwargs: Any) -> None:
        """Run an action on the entity."""
        if key == "reset_energy":
            _LOGGER.info("Resetting energy counter for %s", self.entity_id)
            await self._client.async_reset_energy_counter(
                self._device_id, self._channel_index
            )
        else:
            _LOGGER.warning("Unknown action %s called for %s", key, self.entity_id)