# custom_components/hcu_integration/sensor.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import HcuApiClient
from .entity import HcuBaseEntity, HcuHomeBaseEntity

if TYPE_CHECKING:
    from . import HcuCoordinator


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

        prefix = self._entity_prefix
        base_name = f"Homematic IP HCU {mapping['name']}"
        self._attr_name = f"{prefix} {base_name}" if prefix else base_name
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
        self._base_mapping = mapping

        # ENHANCED: Smart naming for energy counters based on type
        feature_name = self._get_smart_feature_name()
        
        self._set_entity_name(
            channel_label=self._channel.get("label"),
            feature_name=feature_name
        )

        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_{self._feature}"
        self._attr_device_class = mapping.get("device_class")
        self._attr_native_unit_of_measurement = mapping.get("unit")
        self._attr_state_class = mapping.get("state_class")
        self._attr_icon = mapping.get("icon")

        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping[
                "entity_registry_enabled_default"
            ]

    def _get_smart_feature_name(self) -> str:
        """Generate smart feature name based on channel data."""
        # For energy counters, use the type information if available
        if self._feature.startswith("energyCounter"):
            counter_type_key = f"{self._feature}Type"
            counter_type = self._channel.get(counter_type_key, "UNKNOWN")
            
            # Map API counter types to user-friendly names
            type_name_map = {
                "ENERGY_COUNTER_USAGE_HIGH_TARIFF": "Energy Usage (High Tariff)",
                "ENERGY_COUNTER_USAGE_LOW_TARIFF": "Energy Usage (Low Tariff)",
                "ENERGY_COUNTER_INPUT_SINGLE_TARIFF": "Energy Feed-in",
                "ENERGY_COUNTER_INPUT_HIGH_TARIFF": "Energy Feed-in (High Tariff)",
                "ENERGY_COUNTER_INPUT_LOW_TARIFF": "Energy Feed-in (Low Tariff)",
                "UNKNOWN": self._base_mapping["name"],
            }
            
            return type_name_map.get(counter_type, self._base_mapping["name"])
        
        return self._base_mapping["name"]

    @property
    def native_value(self) -> float | str | None:
        """Return the sensor value, with special handling for certain features."""
        value = self._channel.get(self._feature)
        if value is None:
            return None

        if self._feature == "valvePosition":
            return round(value * 100.0, 1)
        if self._feature == "vaporAmount":
            return round(value, 2)

        return value


class HcuTemperatureSensor(HcuGenericSensor):
    """
    Representation of an HCU temperature sensor.
    This class is designed to handle temperature readings from both
    wall-mounted thermostats (`actualTemperature`) and radiator thermostats
    (`valveActualTemperature`).
    """

    @property
    def native_value(self) -> float | str | None:
        """Return the temperature, checking both possible keys."""
        return self._channel.get("actualTemperature") or self._channel.get(
            "valveActualTemperature"
        )