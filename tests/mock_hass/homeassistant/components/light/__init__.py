class LightEntity:
    pass

class LightEntityFeature:
    TRANSITION = 32
    EFFECT = 4

class ColorMode:
    UNKNOWN = "unknown"
    ONOFF = "onoff"
    BRIGHTNESS = "brightness"
    COLOR_TEMP = "color_temp"
    HS = "hs"
    XY = "xy"
    RGB = "rgb"
    RGBW = "rgbw"
    RGBWW = "rgbww"
    WHITE = "white"

ATTR_BRIGHTNESS = "brightness"
ATTR_COLOR_TEMP_KELVIN = "color_temp_kelvin"
ATTR_EFFECT = "effect"
ATTR_HS_COLOR = "hs_color"
ATTR_TRANSITION = "transition"
