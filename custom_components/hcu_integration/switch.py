from typing import TYPE_CHECKING
import logging

from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import HMIP_DEVICE_TYPE_TO_DEVICE_CLASS
from .entity import HcuBaseEntity, HcuHomeBaseEntity
from .api import HcuApiClient, HcuApiError

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][config_entry.entry_id]
    if entities := coordinator.entities.get(Platform.SWITCH):
        async_add_entities(entities)

class HcuSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of a standard Homematic IP HCU switch."""
    PLATFORM = Platform.SWITCH
    _attr_has_entity_name = False
    _attr_name = None # Use device name

    def __init__(self, coordinator: "HcuCoordinator", client: HcuApiClient, device_data: dict, channel_index: str, **kwargs):
        super().__init__(coordinator, client, device_data, channel_index)
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_on"

        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TYPE_TO_DEVICE_CLASS.get(device_type)

    @property
    def is_on(self) -> bool:
        return self._channel.get("on", False)

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_set_switch_state(self._device_id, self._channel_index, True)


    async def async_turn_off(self, **kwargs) -> None:
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_set_switch_state(self._device_id, self._channel_index, False)


class HcuWateringSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of a Homematic IP HCU watering controller."""
    PLATFORM = Platform.SWITCH
    _attr_icon = "mdi:water"
    _attr_has_entity_name = False
    _attr_name = None # Use device name

    def __init__(self, coordinator: "HcuCoordinator", client: HcuApiClient, device_data: dict, channel_index: str, **kwargs):
        super().__init__(coordinator, client, device_data, channel_index)
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_watering"

    @property
    def is_on(self) -> bool:
        return self._channel.get("wateringActive", False)

    async def async_turn_on(self, **kwargs) -> None:
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_set_watering_switch_state(self._device_id, self._channel_index, True)


    async def async_turn_off(self, **kwargs) -> None:
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_set_watering_switch_state(self._device_id, self._channel_index, False)


class HcuHomeSwitch(HcuHomeBaseEntity, SwitchEntity):
    """A switch entity tied to the HCU 'home' object, for features like Vacation Mode."""
    PLATFORM = Platform.SWITCH
    _attr_has_entity_name = False
    _attr_name = "Vacation Mode"
    _attr_icon = "mdi:palm-tree"
    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coordinator: "HcuCoordinator", client: HcuApiClient):
        super().__init__(coordinator, client)
        self._attr_unique_id = f"{self._hcu_device_id}_vacation_mode"

    @property
    def is_on(self) -> bool:
        """Return true if vacation mode is active."""
        heating_home = self._home.get("functionalHomes", {}).get("HEATING", {})
        return heating_home.get("vacationMode", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on vacation mode."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            # The API requires an end time and temperature to activate vacation mode.
            # We'll set it for a very long time into the future as a proxy for "indefinite".
            # Users can turn it off manually.
            await self._client.async_activate_vacation(
                temperature=5.0, # Use minimum eco temperature
                end_time="2038_01_01 00:00" # A far-future date
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to turn on vacation mode: %s", err)
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off vacation mode."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        try:
            await self._client.async_deactivate_vacation()
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to turn off vacation mode: %s", err)
            self._attr_assumed_state = False
            self.async_write_ha_state()