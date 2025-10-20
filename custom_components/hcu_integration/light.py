# custom_components/hcu_integration/light.py
from typing import TYPE_CHECKING
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN, ATTR_HS_COLOR, ColorMode, LightEntity
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HcuBaseEntity
from .api import HcuApiClient

if TYPE_CHECKING:
    from . import HcuCoordinator


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform from a config entry."""
    coordinator: "HcuCoordinator" = hass.data[config_entry.domain][config_entry.entry_id]
    if entities := coordinator.entities.get(Platform.LIGHT):
        async_add_entities(entities)

class HcuLight(HcuBaseEntity, LightEntity):
    """Representation of a Homematic IP HCU light."""
    PLATFORM = Platform.LIGHT
    
    def __init__(self, coordinator: "HcuCoordinator", client: HcuApiClient, device_data: dict, channel_index: str, **kwargs):
        super().__init__(coordinator, client, device_data, channel_index)
        
        # Set entity name based on channel label or fallback to device name
        channel_label = self._channel.get("label")
        if channel_label:
            self._attr_name = channel_label
            self._attr_has_entity_name = False
        else:
            self._attr_name = None
            self._attr_has_entity_name = False
            
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_light"

        supported_modes = set()
        if "dimLevel" in self._channel:
            supported_modes.add(ColorMode.BRIGHTNESS)

        if self._channel.get("hue") is not None:
            supported_modes.add(ColorMode.HS)
        elif "colorTemperature" in self._channel:
            supported_modes.add(ColorMode.COLOR_TEMP)
            self._attr_min_color_temp_kelvin = self._channel.get("minimalColorTemperature", 2000)
            self._attr_max_color_temp_kelvin = self._channel.get("maximumColorTemperature", 6500)

        if not supported_modes:
            supported_modes.add(ColorMode.ONOFF)

        self._attr_supported_color_modes = supported_modes

    @property
    def color_mode(self) -> ColorMode | str | None:
        """Return the current color mode of the light."""
        if ColorMode.HS in self.supported_color_modes:
            return ColorMode.HS
        if ColorMode.COLOR_TEMP in self.supported_color_modes:
            return ColorMode.COLOR_TEMP
        if ColorMode.BRIGHTNESS in self.supported_color_modes:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def is_on(self) -> bool:
        dim_level = self._channel.get("dimLevel")
        # Check if dim_level is not None before comparing
        if dim_level is not None:
            return dim_level > 0.0
        return self._channel.get("on", False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness, scaled from HCU's 0.0-1.0 to HA's 0-255."""
        dim_level = self._channel.get("dimLevel")
        return int(dim_level * 255) if dim_level is not None else None

    @property
    def color_temp_kelvin(self) -> int | None:
        return self._channel.get("colorTemperature")

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value."""
        hue = self._channel.get("hue")
        saturation = self._channel.get("saturationLevel")
        if hue is None or saturation is None:
            return None
        return (float(hue), float(saturation) * 100)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on and adjust brightness or color."""
        dim_level = kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255) / 255.0

        if ATTR_HS_COLOR in kwargs and ColorMode.HS in self.supported_color_modes:
            hs_color = kwargs[ATTR_HS_COLOR]
            hue = int(hs_color[0])
            saturation = hs_color[1] / 100.0
            await self._client.async_set_hue_saturation(self._device_id, self._channel_index, hue, saturation, dim_level)
        elif ATTR_COLOR_TEMP_KELVIN in kwargs and ColorMode.COLOR_TEMP in self.supported_color_modes:
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            await self._client.async_set_color_temperature(self._device_id, self._channel_index, color_temp, dim_level)
        else:
            await self._client.async_set_dim_level(self._device_id, self._channel_index, dim_level)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off by setting its dim level to 0."""
        await self._client.async_set_dim_level(self._device_id, self._channel_index, 0.0)