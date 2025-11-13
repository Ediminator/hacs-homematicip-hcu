"""Support for Homematic IP light entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HcuBaseEntity, HcuSwitchingGroupBase
from .api import HcuApiClient
from .const import (
    API_PATHS,
    HMIP_RGB_COLOR_MAP,
    HMIP_COLOR_BLACK,
    HMIP_COLOR_WHITE,
    HMIP_COLOR_RED,
    HMIP_COLOR_BLUE,
    HMIP_COLOR_GREEN,
    HMIP_COLOR_YELLOW,
    HMIP_COLOR_PURPLE,
    HMIP_COLOR_TURQUOISE,
    HMIP_COLOR_ORANGE,
    HMIP_OPTICAL_SIGNAL_BEHAVIOURS,
)

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the light platform from a config entry."""
    coordinator: HcuCoordinator = hass.data[config_entry.domain][config_entry.entry_id]
    if entities := coordinator.entities.get(Platform.LIGHT):
        async_add_entities(entities)


class HcuLight(HcuBaseEntity, LightEntity):
    """Representation of a Homematic IP light."""

    PLATFORM = Platform.LIGHT

    def __init__(
        self,
        coordinator: HcuCoordinator,
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
        **kwargs,
    ):
        """Initialize the light entity."""
        super().__init__(coordinator, client, device_data, channel_index)

        self._set_entity_name(channel_label=self._channel.get("label"))
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_light"

        # Determine supported color modes based on channel capabilities
        supported_modes = set()

        # Check for RGB color support (BSL backlight uses simpleRGBColorState)
        self._has_simple_rgb = "simpleRGBColorState" in self._channel
        has_dim_level = "dimLevel" in self._channel

        # Check for color modes first (HS color takes precedence over simple brightness)
        if self._channel.get("hue") is not None or self._has_simple_rgb:
            # HS color mode implicitly includes brightness control
            supported_modes.add(ColorMode.HS)
        elif "colorTemperature" in self._channel:
            # Color temperature mode implicitly includes brightness control
            supported_modes.add(ColorMode.COLOR_TEMP)
            self._attr_min_color_temp_kelvin = self._channel.get("minimalColorTemperature", 2000)
            self._attr_max_color_temp_kelvin = self._channel.get("maximumColorTemperature", 6500)
        elif has_dim_level:
            # Only use BRIGHTNESS mode if no color mode is supported
            supported_modes.add(ColorMode.BRIGHTNESS)
        else:
            # Simple on/off light with no dimming or color
            supported_modes.add(ColorMode.ONOFF)

        self._attr_supported_color_modes = supported_modes

        # Add transition support for all dimmable modes (HS, COLOR_TEMP, BRIGHTNESS)
        if has_dim_level:
            self._attr_supported_features |= LightEntityFeature.TRANSITION

        # Check for optical signal behavior support (HmIP-BSL and similar devices)
        optional_features = self._channel.get("supportedOptionalFeatures", {})
        self._supports_optical_signal = optional_features.get("IFeatureOpticalSignalBehaviourState", False)
        if self._supports_optical_signal:
            self._attr_supported_features |= LightEntityFeature.EFFECT
            self._attr_effect_list = list(HMIP_OPTICAL_SIGNAL_BEHAVIOURS)

    @property
    def color_mode(self) -> ColorMode | str | None:
        """Return the current active color mode."""
        if ColorMode.HS in self.supported_color_modes:
            return ColorMode.HS
        if ColorMode.COLOR_TEMP in self.supported_color_modes:
            return ColorMode.COLOR_TEMP
        if ColorMode.BRIGHTNESS in self.supported_color_modes:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def is_on(self) -> bool:
        """Return True if the light is on."""
        dim_level = self._channel.get("dimLevel")
        if dim_level is not None:
            return dim_level > 0.0
        return self._channel.get("on", False)

    @property
    def brightness(self) -> int | None:
        """Return the brightness (0-255)."""
        dim_level = self._channel.get("dimLevel")
        return int(dim_level * 255) if dim_level is not None else None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        return self._channel.get("colorTemperature")

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation."""
        # For devices with simpleRGBColorState (e.g., BSL backlight)
        if self._has_simple_rgb:
            rgb_state = self._channel.get("simpleRGBColorState")
            if rgb_state and rgb_state in HMIP_RGB_COLOR_MAP:
                return HMIP_RGB_COLOR_MAP[rgb_state]
            return None

        # For devices with hue/saturation (e.g., RGBW lights)
        hue = self._channel.get("hue")
        saturation = self._channel.get("saturationLevel")
        if hue is None or saturation is None:
            return None
        return (float(hue), float(saturation) * 100)

    @property
    def effect(self) -> str | None:
        """Return the current optical signal behavior effect."""
        if self._supports_optical_signal:
            return self._channel.get("opticalSignalBehaviour")
        return None

    def _hs_to_simple_rgb(self, hs_color: tuple[float, float]) -> str:
        """Convert HS color to the closest Homematic IP simple RGB color."""
        hue, sat = hs_color

        # If saturation is very low, it's white
        if sat < 20:
            return HMIP_COLOR_WHITE

        # Map hue ranges to 8 colors: WHITE, RED, ORANGE, YELLOW, GREEN, TURQUOISE, BLUE, PURPLE
        if hue < 15 or hue >= 345:
            return HMIP_COLOR_RED
        elif 15 <= hue < 45:
            return HMIP_COLOR_ORANGE
        elif 45 <= hue < 90:
            return HMIP_COLOR_YELLOW
        elif 90 <= hue < 150:
            return HMIP_COLOR_GREEN
        elif 150 <= hue < 210:
            return HMIP_COLOR_TURQUOISE
        elif 210 <= hue < 270:
            return HMIP_COLOR_BLUE
        else:  # 270 <= hue < 345
            return HMIP_COLOR_PURPLE

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the light on with optional color, temperature, brightness, or effect adjustments."""
        dim_level = kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255) / 255.0
        ramp_time = kwargs.get(ATTR_TRANSITION)
        effect = kwargs.get(ATTR_EFFECT)

        # Handle color mode specific commands
        if ATTR_HS_COLOR in kwargs and ColorMode.HS in self.supported_color_modes:
            hs_color = kwargs[ATTR_HS_COLOR]

            # For devices with simpleRGBColorState (e.g., BSL backlight)
            if self._has_simple_rgb:
                rgb_color = self._hs_to_simple_rgb(hs_color)

                # Build payload with color only (dimLevel must be sent separately)
                payload = {"simpleRGBColorState": rgb_color}

                # Add optical signal behavior if effect is specified
                if effect and self._supports_optical_signal:
                    payload["opticalSignalBehaviour"] = effect

                # Send color/effect command
                await self._client.async_device_control(
                    API_PATHS["SET_SIMPLE_RGB_COLOR_STATE"],
                    self._device_id,
                    self._channel_index,
                    payload
                )

                # Always send dimLevel command to ensure light is on
                # (dim_level is already calculated from kwargs or current brightness)
                await self._client.async_set_dim_level(
                    self._device_id, self._channel_index, dim_level, ramp_time
                )
            else:
                # For devices with hue/saturation (e.g., RGBW lights)
                hue = int(hs_color[0])
                saturation = hs_color[1] / 100.0
                await self._client.async_set_hue_saturation(
                    self._device_id, self._channel_index, hue, saturation, dim_level, ramp_time
                )
        elif ATTR_COLOR_TEMP_KELVIN in kwargs and ColorMode.COLOR_TEMP in self.supported_color_modes:
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            await self._client.async_set_color_temperature(
                self._device_id, self._channel_index, color_temp, dim_level, ramp_time
            )
        elif effect and self._supports_optical_signal and self._has_simple_rgb:
            # Effect-only change (no color change) for simpleRGBColorState devices
            current_color = self._channel.get("simpleRGBColorState", HMIP_COLOR_WHITE)
            payload = {
                "simpleRGBColorState": current_color,
                "opticalSignalBehaviour": effect
            }
            await self._client.async_device_control(
                API_PATHS["SET_SIMPLE_RGB_COLOR_STATE"],
                self._device_id,
                self._channel_index,
                payload
            )

            # Always send dimLevel command to ensure light is on
            # (dim_level is already calculated from kwargs or current brightness)
            await self._client.async_set_dim_level(
                self._device_id, self._channel_index, dim_level, ramp_time
            )
        else:
            await self._client.async_set_dim_level(
                self._device_id, self._channel_index, dim_level, ramp_time
            )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the light off."""
        ramp_time = kwargs.get(ATTR_TRANSITION)
        await self._client.async_set_dim_level(self._device_id, self._channel_index, 0.0, ramp_time)


class HcuNotificationLight(HcuBaseEntity, LightEntity):
    """Representation of a Homematic IP notification light (e.g., HmIP-MP3P)."""

    PLATFORM = Platform.LIGHT
    _attr_supported_color_modes = {ColorMode.HS}
    _attr_color_mode = ColorMode.HS

    # RGB color mappings for Homematic IP notification devices
    _COLOR_MAP = {
        HMIP_COLOR_BLACK: (0, 0, 0),
        HMIP_COLOR_BLUE: (240, 100, 50),
        HMIP_COLOR_GREEN: (120, 100, 50),
        HMIP_COLOR_TURQUOISE: (180, 100, 50),
        HMIP_COLOR_RED: (0, 100, 50),
        HMIP_COLOR_PURPLE: (300, 100, 50),
        HMIP_COLOR_YELLOW: (60, 100, 50),
        HMIP_COLOR_WHITE: (0, 0, 100),
        HMIP_COLOR_ORANGE: (30, 100, 50),
    }

    def __init__(
        self,
        coordinator: HcuCoordinator,
        client: HcuApiClient,
        device_data: dict,
        channel_index: str,
        **kwargs,
    ):
        """Initialize the notification light entity."""
        super().__init__(coordinator, client, device_data, channel_index)
        self._set_entity_name(channel_label=self._channel.get("label"))
        self._attr_unique_id = f"{self._device_id}_{self._channel_index}_light"

    @property
    def is_on(self) -> bool:
        """Return True if the notification light is on."""
        rgb_state = self._channel.get("simpleRGBColorState")
        return rgb_state is not None and rgb_state != HMIP_COLOR_BLACK

    @property
    def brightness(self) -> int:
        """Return the brightness (notification lights are always full brightness when on)."""
        return 255 if self.is_on else 0

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation based on the current RGB color state."""
        rgb_state = self._channel.get("simpleRGBColorState")
        if not rgb_state or rgb_state == HMIP_COLOR_BLACK:
            return None

        if rgb_state in self._COLOR_MAP:
            h, s, _ = self._COLOR_MAP[rgb_state]
            return (float(h), float(s))

        return None

    def _hs_to_simple_rgb(self, hs_color: tuple[float, float]) -> str:
        """Convert HS color to the closest Homematic IP simple RGB color."""
        hue, sat = hs_color

        # If saturation is very low, it's white
        if sat < 20:
            return HMIP_COLOR_WHITE

        # Map hue ranges to colors
        if hue < 15 or hue >= 345:
            return HMIP_COLOR_RED
        elif 15 <= hue < 45:
            return HMIP_COLOR_ORANGE
        elif 45 <= hue < 75:
            return HMIP_COLOR_YELLOW
        elif 75 <= hue < 165:
            return HMIP_COLOR_GREEN
        elif 165 <= hue < 195:
            return HMIP_COLOR_TURQUOISE
        elif 195 <= hue < 270:
            return HMIP_COLOR_BLUE
        else:  # 270 <= hue < 345
            return HMIP_COLOR_PURPLE

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the notification light on."""
        color = HMIP_COLOR_WHITE

        if ATTR_HS_COLOR in kwargs:
            hs_color = kwargs[ATTR_HS_COLOR]
            color = self._hs_to_simple_rgb(hs_color)

        await self._client.async_device_control(
            API_PATHS["SET_SIMPLE_RGB_COLOR_STATE"],
            self._device_id,
            self._channel_index,
            {"simpleRGBColorState": color}
        )

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the notification light off."""
        await self._client.async_device_control(
            API_PATHS["SET_SIMPLE_RGB_COLOR_STATE"],
            self._device_id,
            self._channel_index,
            {"simpleRGBColorState": HMIP_COLOR_BLACK}
        )

    async def async_play_sound(
        self, sound_file: str, volume: float, duration: float
    ) -> None:
        """Play a sound on this notification device (service call handler)."""
        await self._client.async_set_sound_file(
            device_id=self._device_id,
            channel_index=self._channel_index,
            sound_file=sound_file,
            volume=volume,
            duration=duration,
        )


class HcuLightGroup(HcuSwitchingGroupBase, LightEntity):
    """Representation of a Homematic IP HCU light group."""

    PLATFORM = Platform.LIGHT

    def __init__(
        self,
        coordinator: "HcuCoordinator",
        client: HcuApiClient,
        group_data: dict[str, Any],
    ) -> None:
        """Initialize the HCU light group."""
        super().__init__(coordinator, client, group_data)

        # Light groups typically only support on/off for the group
        self._attr_supported_color_modes = {ColorMode.ONOFF}
        self._attr_color_mode = ColorMode.ONOFF
