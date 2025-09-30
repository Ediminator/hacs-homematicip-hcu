# custom_components/hcu_integration/light.py
"""
Light platform for the Homematic IP HCU integration.

This platform creates light entities for Homematic IP devices that support brightness control.
It also handles color temperature control for lights that support it.
"""
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN, ColorMode, LightEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_FEATURE_TO_ENTITY, API_PATHS
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform from a config entry."""
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

            if "dimLevel" in channel_data:
                mapping = HMIP_FEATURE_TO_ENTITY.get("dimLevel", {})
                if mapping.get("class") == "HcuLight":
                    unique_id = f"{device_data['id']}_{channel_index}_light"
                    if unique_id not in created_entity_ids:
                        new_entities.append(HcuLight(client, device_data, channel_index))
                        created_entity_ids.add(unique_id)

    if new_entities:
        async_add_entities(new_entities)

class HcuLight(HcuBaseEntity, LightEntity):
    """Representation of a Homematic IP HCU light."""
    
    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the light entity."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = self._device.get("label") or "Unknown Light"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_light"
        
        # Start with brightness support, which is guaranteed if this entity is created.
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        # Add color temperature support if the device reports the feature.
        if "colorTemperature" in self._channel:
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_min_color_temp_kelvin = self._channel.get("minimalColorTemperature", 2000)
            self._attr_max_color_temp_kelvin = self._channel.get("maximumColorTemperature", 6500)
        
    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode of the light."""
        if "colorTemperature" in self._channel and ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return ColorMode.COLOR_TEMP
        return ColorMode.BRIGHTNESS

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._channel.get("on", False)

    @property
    def brightness(self) -> int | None:
        """
        Return the brightness of this light.
        The value is scaled from HCU's 0.0-1.0 to Home Assistant's 0-255.
        """
        dim_level = self._channel.get("dimLevel")
        return int(dim_level * 255) if dim_level is not None else None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        return self._channel.get("colorTemperature")

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on and adjust brightness or color temperature."""
        self._attr_assumed_state = True
        self.async_write_ha_state()

        dim_level = kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255) / 255.0
        
        if ATTR_COLOR_TEMP_KELVIN in kwargs and self.color_mode == ColorMode.COLOR_TEMP:
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            await self._client.async_device_control(
                API_PATHS.SET_COLOR_TEMP,
                self._device_id, self._channel_index, 
                {"colorTemperature": color_temp, "dimLevel": dim_level}
            )
        else:
            await self._client.async_device_control(
                API_PATHS.SET_DIM_LEVEL,
                self._device_id, self._channel_index, {"dimLevel": dim_level}
            )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off by setting its dim level to 0."""
        self._attr_assumed_state = True
        self.async_write_ha_state()
        await self._client.async_device_control(
            API_PATHS.SET_DIM_LEVEL,
            self._device_id, self._channel_index, {"dimLevel": 0.0}
        )