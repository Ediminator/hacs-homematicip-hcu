import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
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
    """Set up the binary_sensor platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][
        config_entry.entry_id
    ]
    if entities := coordinator.entities.get(Platform.BINARY_SENSOR):
        async_add_entities(entities)


class HcuBinarySensor(HcuBaseEntity, BinarySensorEntity):
    """Representation of an HCU binary sensor."""

    PLATFORM = Platform.BINARY_SENSOR

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
        feature: str,
        mapping: dict,
    ):
        """Initialize the binary sensor."""
        super().__init__(coordinator, client, device_data, channel_index)
        self._feature = feature
        self._on_state = mapping.get("on_state", True)

        self._attr_name = mapping.get("name")
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_{self._feature}"
        self._attr_device_class = mapping.get("device_class")

        if "entity_registry_enabled_default" in mapping:
            self._attr_entity_registry_enabled_default = mapping[
                "entity_registry_enabled_default"
            ]

    @property
    def available(self) -> bool:
        """
        Return availability of the entity.

        The connectivity sensor must be available even when the device is unreachable.
        """
        if self.device_class == BinarySensorDeviceClass.CONNECTIVITY:
            return self.coordinator.last_update_success
        return super().available

    @property
    def is_on(self) -> bool | None:
        """Return the state of the binary sensor."""
        value = self._channel.get(self._feature)
        if value is None:
            return None

        # The 'connectivity' device class expects 'on' for connected and 'off' for disconnected.
        # The HCU API's 'unreach' property is 'true' for disconnected and 'false' for connected.
        # Therefore, we must invert the logic for this specific device class.
        if self.device_class == BinarySensorDeviceClass.CONNECTIVITY:
            return not value

        # Special handling for inverted logic sensors
        if self.device_class == BinarySensorDeviceClass.LOCK:
            return not value

        # Window sensors have multiple states (OPEN, TILTED, CLOSED)
        if self._feature == "windowState":
            return value in ("OPEN", "TILTED")

        return value == self._on_state