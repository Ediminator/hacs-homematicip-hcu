# custom_components/hcu_integration/switch.py
"""
Switch platform for the Homematic IP HCU integration.

This platform creates switch entities for standard switches, outlets, and watering controllers.
"""
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_DEVICE_TYPE_TO_DEVICE_CLASS, HMIP_FEATURE_TO_ENTITY
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = coordinator.client
    
    new_entities = []
    created_entity_ids = set()

    for device_data in client.state.get("devices", {}).values():
        if device_data.get("PARENT"):
            continue # Skip child devices as they are handled by their parent.

        oem = device_data.get("oem")
        if oem and oem != "eQ-3":
            # Check if importing devices from this third-party manufacturer is enabled.
            option_key = f"import_{oem.lower().replace(' ', '_')}"
            if not config_entry.options.get(option_key, True):
                continue

        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            # Do not create controls for the HCU's internal channels.
            if channel_data.get("functionalChannelType") == "ACCESS_CONTROLLER_CHANNEL":
                continue

            for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
                if feature in channel_data and mapping.get("class", "").endswith("Switch"):
                    # For dimmers, a light entity is created, which includes switch functionality.
                    # This check prevents creating a duplicate switch entity for the same channel.
                    if "dimLevel" in channel_data:
                        continue

                    unique_id = f"{device_data['id']}_{channel_index}_{feature}"
                    if unique_id not in created_entity_ids:
                        entity_class = globals()[mapping["class"]]
                        new_entities.append(entity_class(client, device_data, channel_index))
                        created_entity_ids.add(unique_id)

    if new_entities:
        async_add_entities(new_entities)

class HcuSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of a standard Homematic IP HCU switch."""

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the switch entity."""
        super().__init__(client, device_data, channel_index)
        device_label = self._device.get("label", "Unknown Switch")
        # For simple switches, the device label is sufficient.
        self._attr_name = device_label
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_on" # Suffix matches the feature key.
        
        device_type = self._device.get("type")
        self._attr_device_class = HMIP_DEVICE_TYPE_TO_DEVICE_CLASS.get(device_type)

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self._channel.get("on", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_device_control(
            path="/hmip/device/control/setSwitchState",
            device_id=self._device_id,
            channel_index=self._channel_index,
            body={"on": True}
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_device_control(
            path="/hmip/device/control/setSwitchState",
            device_id=self._device_id,
            channel_index=self._channel_index,
            body={"on": False}
        )

class HcuWateringSwitch(HcuBaseEntity, SwitchEntity):
    """Representation of a Homematic IP HCU watering controller."""
    _attr_icon = "mdi:water"

    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the watering switch entity."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = self._device.get("label") or "Watering"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_watering"

    @property
    def is_on(self) -> bool:
        """Return true if watering is active."""
        return self._channel.get("wateringActive", False)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the watering on."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_device_control(
            path="/hmip/device/control/setWateringSwitchState",
            device_id=self._device_id,
            channel_index=self._channel_index,
            body={"wateringActive": True},
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the watering off."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_device_control(
            path="/hmip/device/control/setWateringSwitchState",
            device_id=self._device_id,
            channel_index=self._channel_index,
            body={"wateringActive": False},
        )