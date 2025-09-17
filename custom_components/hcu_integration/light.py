# custom_components/hcu_integration/light.py
"""Light platform for the Homematic IP HCU integration."""
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HMIP_DEVICE_PLATFORM_MAP
from .entity import HcuBaseEntity
from .api import HcuApiClient

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = data["client"]
    coordinator = data["coordinator"]
    devices = coordinator.data.get("devices", {})
    
    new_lights = []
    for device_data in devices.values():
        if HMIP_DEVICE_PLATFORM_MAP.get(device_data.get("type")) == "light":
            for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
                if "dimLevel" in channel_data and channel_data.get("functionalChannelType") in ("DIMMER_CHANNEL", "SWITCH_CHANNEL"):
                    new_lights.append(HcuLight(client, coordinator, device_data, channel_index))
    if new_lights: async_add_entities(new_lights)

class HcuLight(HcuBaseEntity, LightEntity):
    """Representation of an HCU Light."""
    def __init__(self, client, coordinator, device_data, channel_index):
        """Initialize the light."""
        super().__init__(coordinator, device_data, channel_index)
        self._client = client
        self._attr_name = self._device.get("label") or "Unknown Light"
        self._attr_unique_id = f"{self._device.get('id')}_{self._channel_index}_light"
        
        # Determine supported color modes
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        if "colorTemperature" in self._channel:
            self._attr_supported_color_modes.add(ColorMode.COLOR_TEMP)
            # Add color temp range from device if available
            self._attr_min_color_temp_kelvin = self._channel.get("minimalColorTemperature", 2000)
            self._attr_max_color_temp_kelvin = self._channel.get("maximumColorTemperature", 6500)
        # TODO: Add HS color support here if device supports it (feature "color")
        
    @property
    def color_mode(self) -> ColorMode:
        """Return the color mode of the light."""
        if "colorTemperature" in self._updated_channel:
            return ColorMode.COLOR_TEMP
        return ColorMode.BRIGHTNESS

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._updated_channel.get("on", False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 0..255."""
        dim_level = self._updated_channel.get("dimLevel")
        return int(dim_level * 255) if dim_level is not None else None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        return self._updated_channel.get("colorTemperature")

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on."""
        device_id = self._device.get("id")
        channel_index = self._channel.get("index")
        
        dim_level = kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255) / 255.0
        
        if ATTR_COLOR_TEMP_KELVIN in kwargs and ColorMode.COLOR_TEMP in self.supported_color_modes:
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            await self._client.async_set_color_temperature_dim_level(device_id, channel_index, color_temp, dim_level)
        elif ATTR_BRIGHTNESS in kwargs:
            await self._client.async_set_dim_level(device_id, channel_index, dim_level)
        else: # If no attributes are specified, just turn on
            await self._client.async_set_switch_state(device_id, channel_index, True)
            
        # No manual refresh needed with event-driven updates.

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        await self._client.async_set_switch_state(self._device.get("id"), self._channel.get("index"), False)
        # No manual refresh needed with event-driven updates.