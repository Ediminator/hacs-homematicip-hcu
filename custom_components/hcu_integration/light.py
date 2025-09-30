# custom_components/hcu_integration/light.py
"""
Light platform for the Homematic IP HCU integration.

This platform creates light entities for Homematic IP devices that support brightness control.
It also handles color temperature and HS color control for lights that support it.
"""
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN, ATTR_HS_COLOR, ColorMode, LightEntity
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
            continue

        oem = device_data.get("oem")
        if oem and oem != "eQ-3":
            option_key = f"import_{oem.lower().replace(' ', '_')}"
            if not config_entry.options.get(option_key, True):
                continue

        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
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
        """Initialize the light entity and determine its supported color modes."""
        super().__init__(client, device_data, channel_index)
        self._attr_name = self._device.get("label") or "Unknown Light"
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_light"
        
        supported_modes = set()
        if "dimLevel" in self._channel:
            supported_modes.add(ColorMode.BRIGHTNESS)
        
        # Check for color support, prioritizing HS over color temperature if both are present.
        if self._channel.get("hue") is not None:
            supported_modes.add(ColorMode.HS)
        elif "colorTemperature" in self._channel:
            supported_modes.add(ColorMode.COLOR_TEMP)
            self._attr_min_color_temp_kelvin = self._channel.get("minimalColorTemperature", 2000)
            self._attr_max_color_temp_kelvin = self._channel.get("maximumColorTemperature", 6500)
        
        # If no dimming or color features are found, it's a simple on/off light.
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
        if ColorMode.ONOFF in self.supported_color_modes:
            return ColorMode.ONOFF
        return super().color_mode

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        # A dim level > 0 means the light is on. Fallback to 'on' state if dimLevel is not present.
        return self._channel.get("dimLevel", 0.0) > 0.0 or self._channel.get("on", False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness, scaled from HCU's 0.0-1.0 to HA's 0-255."""
        dim_level = self._channel.get("dimLevel")
        return int(dim_level * 255) if dim_level is not None else None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        return self._channel.get("colorTemperature")

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value."""
        hue = self._channel.get("hue")
        saturation = self._channel.get("saturationLevel")
        if hue is None or saturation is None:
            return None
        # HCU saturation is 0.0-1.0, HA is 0-100.
        return (float(hue), float(saturation) * 100)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on and adjust brightness or color."""
        self._attr_assumed_state = True
        self.async_write_ha_state()

        dim_level = kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255) / 255.0
        
        if ATTR_HS_COLOR in kwargs and ColorMode.HS in self.supported_color_modes:
            hs_color = kwargs[ATTR_HS_COLOR]
            await self._client.async_device_control(
                API_PATHS.SET_HUE,
                self._device_id, self._channel_index, 
                {
                    "hue": int(hs_color[0]), 
                    "saturationLevel": hs_color[1] / 100.0,
                    "dimLevel": dim_level,
                }
            )
        elif ATTR_COLOR_TEMP_KELVIN in kwargs and ColorMode.COLOR_TEMP in self.supported_color_modes:
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            await self._client.async_device_control(
                API_PATHS.SET_COLOR_TEMP,
                self._device_id, self._channel_index, 
                {"colorTemperature": color_temp, "dimLevel": dim_level}
            )
        else:
            # Default to setting brightness if no color is specified.
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