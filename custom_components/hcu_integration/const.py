# custom_components/hcu_integration/const.py
"""Constants for the Homematic IP Local (HCU) integration."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.const import (
    PERCENTAGE, CONCENTRATION_PARTS_PER_MILLION, LIGHT_LUX, UnitOfEnergy, UnitOfPower, UnitOfTemperature, UnitOfSpeed
)

# Backward-compatible import for UnitOfPrecipitation to support multiple Home Assistant versions.
try:
    # Modern location for units (preferred)
    from homeassistant.const import UnitOfPrecipitation
except ImportError:
    try:
        # Older location for units
        from homeassistant.components.sensor import UnitOfPrecipitation
    except ImportError:
        # Fallback for very old Home Assistant versions that do not have the constant
        UnitOfPrecipitation = "mm"


DOMAIN = "hcu_integration"
PLATFORMS = [
    "alarm_control_panel", "binary_sensor", "button", "climate", "cover",
    "light", "lock", "sensor", "switch"
]

# HCU Connection Configuration
DEFAULT_HCU_AUTH_PORT = 6969
DEFAULT_HCU_WEBSOCKET_PORT = 9001
PLUGIN_ID = "de.homeassistant.hcu.integration"
PLUGIN_FRIENDLY_NAME = {"de": "Home Assistant Integration", "en": "Home Assistant Integration"}

# API Timeouts and Retry Configuration
API_REQUEST_TIMEOUT = 10
API_RETRY_DELAY = 2

# WebSocket Connection Configuration
WEBSOCKET_CONNECT_TIMEOUT = 30
WEBSOCKET_RECONNECT_INITIAL_DELAY = 1
WEBSOCKET_RECONNECT_MAX_DELAY = 60
WEBSOCKET_RECONNECT_JITTER_MAX = 2
WEBSOCKET_HEARTBEAT_INTERVAL = 30.0
WEBSOCKET_RECEIVE_TIMEOUT = 60.0

# Misc Configuration
BUTTON_PULSE_DURATION = 0.3

# HCU Device Type Identification
HCU_DEVICE_TYPES = ("HOME_CONTROL_ACCESS_POINT", "WIRED_ACCESS_POINT", "ACCESS_POINT", "WIRED_DIN_RAIL_ACCESS_POINT")
HCU_MODEL_TYPES = ("HmIP-HAP", "HmIP-HCU1-A", "HmIPW-DRAP")

# Configuration Keys
CONF_PIN = "pin"
CONF_COMFORT_TEMPERATURE = "comfort_temperature"
CONF_AUTH_PORT = "auth_port"
CONF_WEBSOCKET_PORT = "websocket_port"

DEFAULT_COMFORT_TEMPERATURE = 21.0


class API_PATHS:
    """API endpoint paths for HCU communication."""
    
    # Device Control Endpoints
    SET_SWITCH_STATE = "/hmip/device/control/setSwitchState"
    SET_WATERING_SWITCH_STATE = "/hmip/device/control/setWateringSwitchState"
    SET_DIM_LEVEL = "/hmip/device/control/setDimLevel"
    SET_COLOR_TEMP = "/hmip/device/control/setColorTemperatureDimLevel"
    SET_HUE = "/hmip/device/control/setHueSaturationDimLevel"
    SET_SHUTTER_LEVEL = "/hmip/device/control/setShutterLevel"
    SET_SLATS_LEVEL = "/hmip/device/control/setSlatsLevel"
    STOP_COVER = "/hmip/device/control/stop"
    SET_LOCK_STATE = "/hmip/device/control/setLockState"
    SEND_DOOR_COMMAND = "/hmip/device/control/sendDoorCommand"
    TOGGLE_GARAGE_DOOR_STATE = "/hmip/device/control/toggleGarageDoorState"
    SET_SOUND_FILE = "/hmip/device/control/setSoundFileVolumeLevelWithTime"
    RESET_ENERGY_COUNTER = "/hmip/device/control/resetEnergyCounter"

    # Group Control Endpoints
    SET_GROUP_BOOST = "/hmip/group/heating/setBoost"
    SET_GROUP_SET_POINT_TEMP = "/hmip/group/heating/setSetPointTemperature"
    SET_GROUP_CONTROL_MODE = "/hmip/group/heating/setControlMode"

    # Home Control Endpoints
    SET_ZONES_ACTIVATION = "/hmip/home/security/setZonesActivation"
    GET_SYSTEM_STATE = "/hmip/home/getSystemState"
    ENABLE_SIMPLE_RULE = "/hmip/rule/enableSimpleRule"


# Device Class Mappings
HMIP_DEVICE_TYPE_TO_DEVICE_CLASS = {
    "PLUGABLE_SWITCH": SwitchDeviceClass.OUTLET,
    "PRINTED_SWITCH": SwitchDeviceClass.SWITCH,
    "WALL_MOUNTED_SWITCH": SwitchDeviceClass.SWITCH,
    "WINDOW_COVERING": CoverDeviceClass.SHUTTER,
    "DIN_RAIL_SWITCH": SwitchDeviceClass.SWITCH,
    "WIRED_SWITCH_8": SwitchDeviceClass.SWITCH,
    "WIRED_SWITCH_4": SwitchDeviceClass.SWITCH,
    "HOERMANN_DRIVES_MODULE": CoverDeviceClass.GARAGE,
    "TORMATIC_MODULE": CoverDeviceClass.GARAGE,
    "PLUGABLE_SWITCH_MEASURING": SwitchDeviceClass.OUTLET,
}

# Feature to Entity Mappings
HMIP_FEATURE_TO_ENTITY = {
    # Sensor Features
    "actualTemperature": {
        "class": "HcuTemperatureSensor", 
        "name": "Temperature", 
        "unit": UnitOfTemperature.CELSIUS, 
        "device_class": SensorDeviceClass.TEMPERATURE, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "valveActualTemperature": {
        "class": "HcuTemperatureSensor", 
        "name": "Temperature", 
        "unit": UnitOfTemperature.CELSIUS, 
        "device_class": SensorDeviceClass.TEMPERATURE, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "temperatureExternalOne": {
        "class": "HcuGenericSensor", 
        "name": "Temperature Sensor 1", 
        "unit": UnitOfTemperature.CELSIUS, 
        "device_class": SensorDeviceClass.TEMPERATURE, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "temperatureExternalTwo": {
        "class": "HcuGenericSensor", 
        "name": "Temperature Sensor 2", 
        "unit": UnitOfTemperature.CELSIUS, 
        "device_class": SensorDeviceClass.TEMPERATURE, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "temperatureExternalDelta": {
        "class": "HcuGenericSensor", 
        "name": "Temperature Delta", 
        "unit": UnitOfTemperature.CELSIUS, 
        "device_class": SensorDeviceClass.TEMPERATURE, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "humidity": {
        "class": "HcuGenericSensor", 
        "name": "Humidity", 
        "unit": PERCENTAGE, 
        "device_class": SensorDeviceClass.HUMIDITY, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "vaporAmount": {
        "class": "HcuGenericSensor", 
        "name": "Absolute Humidity", 
        "unit": "g/m³", 
        "icon": "mdi:water", 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "illumination": {
        "class": "HcuGenericSensor", 
        "name": "Illuminance", 
        "unit": LIGHT_LUX, 
        "device_class": SensorDeviceClass.ILLUMINANCE, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "currentPowerConsumption": {
        "class": "HcuGenericSensor", 
        "name": "Current Power", 
        "unit": UnitOfPower.WATT, 
        "device_class": SensorDeviceClass.POWER, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "energyCounter": {
        "class": "HcuEnergySensor", 
        "name": "Energy", 
        "unit": UnitOfEnergy.KILO_WATT_HOUR, 
        "device_class": SensorDeviceClass.ENERGY, 
        "state_class": SensorStateClass.TOTAL_INCREASING
    },
    "windSpeed": {
        "class": "HcuGenericSensor", 
        "name": "Wind Speed", 
        "unit": UnitOfSpeed.KILOMETERS_PER_HOUR, 
        "device_class": SensorDeviceClass.WIND_SPEED, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "rainCounter": {
        "class": "HcuGenericSensor",
        "name": "Rain Counter",
        "unit": UnitOfPrecipitation,
        "device_class": SensorDeviceClass.PRECIPITATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "todayRainCounter": {
        "class": "HcuGenericSensor",
        "name": "Today's Rain",
        "unit": UnitOfPrecipitation,
        "device_class": SensorDeviceClass.PRECIPITATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "yesterdayRainCounter": {
        "class": "HcuGenericSensor",
        "name": "Yesterday's Rain",
        "unit": UnitOfPrecipitation,
        "device_class": SensorDeviceClass.PRECIPITATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "co2": {
        "class": "HcuGenericSensor", 
        "name": "CO2", 
        "unit": CONCENTRATION_PARTS_PER_MILLION, 
        "device_class": SensorDeviceClass.CO2, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "batteryLevel": {
        "class": "HcuGenericSensor", 
        "name": "Battery Level", 
        "unit": PERCENTAGE, 
        "device_class": SensorDeviceClass.BATTERY, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "sunshineDuration": {
        "class": "HcuGenericSensor", 
        "name": "Sunshine Duration", 
        "unit": "h", 
        "icon": "mdi:timer-sand", 
        "state_class": SensorStateClass.TOTAL_INCREASING
    },
    "valvePosition": {
        "class": "HcuGenericSensor", 
        "name": "Valve Position", 
        "unit": PERCENTAGE, 
        "icon": "mdi:valve", 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "valveState": {
        "class": "HcuGenericSensor", 
        "name": "Valve State", 
        "icon": "mdi:valve-closed", 
        "entity_registry_enabled_default": False
    },
    "rssiDeviceValue": {
        "class": "HcuGenericSensor", 
        "name": "Signal Strength", 
        "unit": "dBm", 
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH, 
        "state_class": SensorStateClass.MEASUREMENT, 
        "entity_registry_enabled_default": False
    },
    "carrierSense": {
        "class": "HcuHomeSensor", 
        "name": "Radio Traffic", 
        "unit": PERCENTAGE, 
        "icon": "mdi:radio-tower", 
        "state_class": SensorStateClass.MEASUREMENT, 
        "entity_registry_enabled_default": False
    },
    "mountingOrientation": {
        "class": "HcuGenericSensor", 
        "name": "Mounting Orientation", 
        "icon": "mdi:axis-arrow", 
        "entity_registry_enabled_default": False
    },
    "soilMoisture": {
        "class": "HcuGenericSensor", 
        "name": "Soil Moisture", 
        "unit": PERCENTAGE, 
        "device_class": SensorDeviceClass.MOISTURE, 
        "state_class": SensorStateClass.MEASUREMENT
    },
    "soilTemperature": {
        "class": "HcuGenericSensor", 
        "name": "Soil Temperature", 
        "unit": UnitOfTemperature.CELSIUS, 
        "device_class": SensorDeviceClass.TEMPERATURE, 
        "state_class": SensorStateClass.MEASUREMENT
    },

    # Binary Sensor Features
    "lowBat": {
        "class": "HcuBinarySensor", 
        "name": "Battery Low", 
        "device_class": BinarySensorDeviceClass.BATTERY, 
        "entity_registry_enabled_default": False
    },
    "unreach": {
        "class": "HcuBinarySensor", 
        "name": "Unreachable", 
        "device_class": BinarySensorDeviceClass.CONNECTIVITY, 
        "entity_registry_enabled_default": False
    },
    "presenceDetected": {
        "class": "HcuBinarySensor", 
        "name": "Presence", 
        "device_class": BinarySensorDeviceClass.MOTION
    },
    "windowState": {
        "class": "HcuBinarySensor", 
        "name": "Window", 
        "on_state": "OPEN", 
        "device_class": BinarySensorDeviceClass.WINDOW
    },
    "smokeAlarm": {
        "class": "HcuBinarySensor", 
        "name": "Smoke Alarm", 
        "on_state": True, 
        "device_class": BinarySensorDeviceClass.SMOKE
    },
    "waterlevelDetected": {
        "class": "HcuBinarySensor", 
        "name": "Water Level", 
        "device_class": BinarySensorDeviceClass.MOISTURE
    },
    "moistureDetected": {
        "class": "HcuBinarySensor", 
        "name": "Moisture", 
        "device_class": BinarySensorDeviceClass.MOISTURE
    },
    "raining": {
        "class": "HcuBinarySensor", 
        "name": "Raining", 
        "device_class": BinarySensorDeviceClass.MOISTURE
    },
    "sunshine": {
        "class": "HcuBinarySensor", 
        "name": "Sunshine", 
        "device_class": BinarySensorDeviceClass.LIGHT
    },
    "storm": {
        "class": "HcuBinarySensor", 
        "name": "Storm", 
        "device_class": BinarySensorDeviceClass.PROBLEM
    },
    "operationLockActive": {
        "class": "HcuBinarySensor", 
        "name": "Controls Locked", 
        "device_class": BinarySensorDeviceClass.LOCK
    },
    "frostProtectionActive": {
        "class": "HcuBinarySensor", 
        "name": "Frost Protection", 
        "device_class": BinarySensorDeviceClass.SAFETY
    },
    "dewPointAlarmActive": {
        "class": "HcuBinarySensor", 
        "name": "Dew Point Alarm", 
        "device_class": BinarySensorDeviceClass.MOISTURE
    },
    "accelerationSensorTriggered": {
        "class": "HcuBinarySensor", 
        "name": "Vibration", 
        "device_class": BinarySensorDeviceClass.VIBRATION
    },
    "powerMainsFailure": {
        "class": "HcuBinarySensor", 
        "name": "Mains Power", 
        "device_class": BinarySensorDeviceClass.POWER, 
        "on_state": False
    },

    # Control Features (used for discovery only)
    "on": {"class": "HcuSwitch"},
    "wateringActive": {"class": "HcuWateringSwitch"},
    "dimLevel": {"class": "HcuLight"},
    "shutterLevel": {"class": "HcuCover"},
    "doorState": {"class": "HcuGarageDoorCover"},
    "lockState": {"class": "HcuLock"},
}

# Channel Type to Entity Mappings (for button/remote controls)
HMIP_CHANNEL_TYPE_TO_ENTITY = {
    "SWITCH_INPUT": {"class": "HcuButton"},
    "WALL_MOUNTED_REMOTE_CONTROL_CHANNEL": {"class": "HcuButton"},
    "KEY_REMOTE_CONTROL_CHANNEL": {"class": "HcuButton"},
    "MULTI_MODE_INPUT_CHANNEL": {"class": "HcuButton"},
    "DOOR_CHANNEL": {"class": "HcuGarageDoorCover"},
}