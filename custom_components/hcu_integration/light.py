# custom_components/hcu_integration/light.py
"""Light platform for the Homematic IP HCU integration."""
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN, ColorMode, LightEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    devices = data["initial_state"].get("devices", {})
    
    new_lights = []
    for device_data in devices.values():
        if not device_data.get("PARENT"):
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                # A channel is considered a light if it has a 'dimLevel' feature.
                if "dimLevel" in channel_data:
                    new_lights.append(HcuLight(client, device_data, channel_index))
    if new_lights:
        async_add_entities(new_lights)

class HcuLight(HcuBaseEntity, LightEntity):
    """Representation of a Homematic IP HCU light."""
    
    def __init__(self, client: HcuApiClient, device_data: dict, channel_index: str):
        """Initialize the light."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = self._device.get("label") or "Unknown Light"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_light"
        
        # Determine supported color modes based on available features in the channel data.
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        if "colorTemperature" in self._channel:
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            self._attr_min_color_temp_kelvin = self._channel.get("minimalColorTemperature", 2000)
            self._attr_max_color_temp_kelvin = self._channel.get("maximumColorTemperature", 6500)
        
    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode of the light."""
        # This logic prioritizes color temp if available, otherwise defaults to brightness.
        if "colorTemperature" in self._channel and ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return ColorMode.COLOR_TEMP
        return ColorMode.BRIGHTNESS

    @property
    def is_on(self) -> bool:
        """Return true if the light's brightness level is greater than 0."""
        return self._channel.get("dimLevel", 0.0) > 0

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light, scaled from 0-1.0 (HCU) to 0-255 (HA)."""
        dim_level = self._channel.get("dimLevel")
        return int(dim_level * 255) if dim_level is not None else None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        return self._channel.get("colorTemperature")

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        # Use current brightness if not provided, or default to full brightness if state is unknown.
        dim_level = kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255) / 255.0
        
        if ATTR_COLOR_TEMP_KELVIN in kwargs and ColorMode.COLOR_TEMP in self.supported_color_modes:
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            await self._client.async_set_color_temperature_dim_level(self._device_id, self._channel_index, color_temp, dim_level)
        else:
            await self._client.async_set_dim_level(self._device_id, self._channel_index, dim_level)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off by setting its dim level to 0."""
        await self._client.async_set_dim_level(self._device_id, self._channel_index, 0.0)