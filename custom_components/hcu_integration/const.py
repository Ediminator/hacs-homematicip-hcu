# custom_components/hcu_integration/const.py
"""Constants for the Homematic IP Local (HCU) integration."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.const import (
    PERCENTAGE, CONCENTRATION_PARTS_PER_MILLION, LIGHT_LUX, UnitOfEnergy, UnitOfPower, UnitOfTemperature, UnitOfSpeed
)

# Domain and platforms for the integration.
DOMAIN = "hcu_integration"
PLATFORMS = [
    "alarm_control_panel", "binary_sensor", "climate", "cover", 
    "light", "lock", "sensor", "switch"
]

# Signal used to dispatch entity updates from the coordinator.
SIGNAL_UPDATE_ENTITY = f"{DOMAIN}_update"

# HCU connection and authentication constants.
HCU_AUTH_PORT = 6969
HCU_WEBSOCKET_PORT = 9001
PLUGIN_ID = "de.homeassistant.hcu.integration"
PLUGIN_FRIENDLY_NAME = {"de": "Home Assistant Integration", "en": "Home Assistant Integration"}
API_REQUEST_TIMEOUT = 10  # Seconds

# Known device types and model types that identify the HCU itself.
# This is used to correctly associate entities with the central HCU device.
HCU_DEVICE_TYPES = ("HOME_CONTROL_ACCESS_POINT", "WIRED_ACCESS_POINT", "ACCESS_POINT", "WIRED_DIN_RAIL_ACCESS_POINT")
HCU_MODEL_TYPES = ("HmIP-HAP", "HmIP-HCU1-A", "HmIPW-DRAP")

# Configuration keys for config and options flows.
CONF_PIN = "pin"
CONF_COMFORT_TEMPERATURE = "comfort_temperature"

# Default values
DEFAULT_COMFORT_TEMPERATURE = 21.0

# API Paths for HCU control, centralized for maintainability.
class API_PATHS:
    """A class to hold all API paths as constants."""
    # Device Control
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
    SET_SOUND_FILE = "/hmip/device/control/setSoundFileVolumeLevelWithTime"
    
    # Group Control
    SET_GROUP_BOOST = "/hmip/group/heating/setBoost"
    SET_GROUP_SET_POINT_TEMP = "/hmip/group/heating/setSetPointTemperature"
    SET_GROUP_CONTROL_MODE = "/hmip/group/heating/setControlMode"
    
    # Home Control
    SET_ZONES_ACTIVATION = "/hmip/home/security/setZonesActivation"
    GET_SYSTEM_STATE = "/hmip/home/getSystemState"


# Mappings to determine the correct Home Assistant device class from the HCU device type.
HMIP_DEVICE_TYPE_TO_DEVICE_CLASS = {
    "PLUGABLE_SWITCH": SwitchDeviceClass.OUTLET,
    "PRINTED_SWITCH": SwitchDeviceClass.SWITCH,
    "WALL_MOUNTED_SWITCH": SwitchDeviceClass.SWITCH,
    "WINDOW_COVERING": CoverDeviceClass.SHUTTER,
    "DIN_RAIL_SWITCH": SwitchDeviceClass.SWITCH,
    "WIRED_SWITCH_8": SwitchDeviceClass.SWITCH,
    "WIRED_SWITCH_4": SwitchDeviceClass.SWITCH,
    "HOERMANN_DRIVES_MODULE": CoverDeviceClass.GARAGE,
    "PLUGABLE_SWITCH_MEASURING": SwitchDeviceClass.OUTLET,
}

# This dictionary maps a specific feature key from the HCU API to an entity class and its configuration.
HMIP_FEATURE_TO_ENTITY = {
    # --- SENSOR ---
    "actualTemperature": {"class": "HcuTemperatureSensor", "name": "Temperature", "unit": UnitOfTemperature.CELSIUS, "device_class": SensorDeviceClass.TEMPERATURE, "state_class": SensorStateClass.MEASUREMENT},
    "valveActualTemperature": {"class": "HcuTemperatureSensor", "name": "Temperature", "unit": UnitOfTemperature.CELSIUS, "device_class": SensorDeviceClass.TEMPERATURE, "state_class": SensorStateClass.MEASUREMENT},
    "temperatureExternalOne": {"class": "HcuGenericSensor", "name": "Temperature Sensor 1", "unit": UnitOfTemperature.CELSIUS, "device_class": SensorDeviceClass.TEMPERATURE, "state_class": SensorStateClass.MEASUREMENT},
    "temperatureExternalTwo": {"class": "HcuGenericSensor", "name": "Temperature Sensor 2", "unit": UnitOfTemperature.CELSIUS, "device_class": SensorDeviceClass.TEMPERATURE, "state_class": SensorStateClass.MEASUREMENT},
    "temperatureExternalDelta": {"class": "HcuGenericSensor", "name": "Temperature Delta", "unit": UnitOfTemperature.CELSIUS, "device_class": SensorDeviceClass.TEMPERATURE, "state_class": SensorStateClass.MEASUREMENT},
    "humidity": {"class": "HcuGenericSensor", "name": "Humidity", "unit": PERCENTAGE, "device_class": SensorDeviceClass.HUMIDITY, "state_class": SensorStateClass.MEASUREMENT},
    "vaporAmount": {"class": "HcuGenericSensor", "name": "Absolute Humidity", "unit": "g/m³", "icon": "mdi:water", "state_class": SensorStateClass.MEASUREMENT},
    "illumination": {"class": "HcuGenericSensor", "name": "Illuminance", "unit": LIGHT_LUX, "device_class": SensorDeviceClass.ILLUMINANCE, "state_class": SensorStateClass.MEASUREMENT},
    "currentPowerConsumption": {"class": "HcuGenericSensor", "name": "Current Power", "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT},
    "energyCounter": {"class": "HcuGenericSensor", "name": "Energy", "unit": UnitOfEnergy.KILO_WATT_HOUR, "device_class": SensorDeviceClass.ENERGY, "state_class": SensorStateClass.TOTAL_INCREASING},
    "windSpeed": {"class": "HcuGenericSensor", "name": "Wind Speed", "unit": UnitOfSpeed.KILOMETERS_PER_HOUR, "device_class": SensorDeviceClass.WIND_SPEED, "state_class": SensorStateClass.MEASUREMENT},
    "co2": {"class": "HcuGenericSensor", "name": "CO2", "unit": CONCENTRATION_PARTS_PER_MILLION, "device_class": SensorDeviceClass.CO2, "state_class": SensorStateClass.MEASUREMENT},
    "batteryLevel": {"class": "HcuGenericSensor", "name": "Battery Level", "unit": PERCENTAGE, "device_class": SensorDeviceClass.BATTERY, "state_class": SensorStateClass.MEASUREMENT},
    "sunshineDuration": {"class": "HcuGenericSensor", "name": "Sunshine Duration", "unit": "h", "icon": "mdi:timer-sand", "state_class": SensorStateClass.TOTAL_INCREASING},
    "valvePosition": {"class": "HcuGenericSensor", "name": "Valve Position", "unit": PERCENTAGE, "icon": "mdi:valve", "state_class": SensorStateClass.MEASUREMENT},
    "valveState": {"class": "HcuGenericSensor", "name": "Valve State", "icon": "mdi:valve-closed", "entity_registry_enabled_default": False},
    "rssiDeviceValue": {"class": "HcuGenericSensor", "name": "Signal Strength", "unit": "dBm", "device_class": SensorDeviceClass.SIGNAL_STRENGTH, "state_class": SensorStateClass.MEASUREMENT, "entity_registry_enabled_default": False},
    "carrierSense": {"class": "HcuHomeSensor", "name": "Radio Traffic", "unit": PERCENTAGE, "icon": "mdi:radio-tower", "state_class": SensorStateClass.MEASUREMENT, "entity_registry_enabled_default": False},
    "mountingOrientation": {"class": "HcuGenericSensor", "name": "Mounting Orientation", "icon": "mdi:axis-arrow", "entity_registry_enabled_default": False},
    "soilMoisture": {"class": "HcuGenericSensor", "name": "Soil Moisture", "unit": PERCENTAGE, "device_class": SensorDeviceClass.MOISTURE, "state_class": SensorStateClass.MEASUREMENT},
    "soilTemperature": {"class": "HcuGenericSensor", "name": "Soil Temperature", "unit": UnitOfTemperature.CELSIUS, "device_class": SensorDeviceClass.TEMPERATURE, "state_class": SensorStateClass.MEASUREMENT},

    # --- BINARY_SENSOR ---
    "lowBat": {"class": "HcuBinarySensor", "name": "Battery Low", "device_class": BinarySensorDeviceClass.BATTERY, "entity_registry_enabled_default": False},
    "unreach": {"class": "HcuBinarySensor", "name": "Unreachable", "device_class": BinarySensorDeviceClass.CONNECTIVITY, "entity_registry_enabled_default": False},
    "presenceDetected": {"class": "HcuBinarySensor", "name": "Presence", "device_class": BinarySensorDeviceClass.MOTION},
    "windowState": {"class": "HcuBinarySensor", "name": "Window", "on_state": "OPEN", "device_class": BinarySensorDeviceClass.WINDOW},
    "smokeAlarm": {"class": "HcuBinarySensor", "name": "Smoke Alarm", "on_state": "SMOKE_DETECTED", "device_class": BinarySensorDeviceClass.SMOKE},
    "waterlevelDetected": {"class": "HcuBinarySensor", "name": "Water Level", "device_class": BinarySensorDeviceClass.MOISTURE},
    "moistureDetected": {"class": "HcuBinarySensor", "name": "Moisture", "device_class": BinarySensorDeviceClass.MOISTURE},
    "raining": {"class": "HcuBinarySensor", "name": "Raining", "device_class": BinarySensorDeviceClass.MOISTURE},
    "sunshine": {"class": "HcuBinarySensor", "name": "Sunshine", "device_class": BinarySensorDeviceClass.LIGHT},
    "storm": {"class": "HcuBinarySensor", "name": "Storm", "device_class": BinarySensorDeviceClass.PROBLEM},
    "operationLockActive": {"class": "HcuBinarySensor", "name": "Controls Locked", "device_class": BinarySensorDeviceClass.LOCK},
    "frostProtectionActive": {"class": "HcuBinarySensor", "name": "Frost Protection", "device_class": BinarySensorDeviceClass.SAFETY},
    "dewPointAlarmActive": {"class": "HcuBinarySensor", "name": "Dew Point Alarm", "device_class": BinarySensorDeviceClass.MOISTURE},
    "accelerationSensorTriggered": {"class": "HcuBinarySensor", "name": "Vibration", "device_class": BinarySensorDeviceClass.VIBRATION},
    "powerMainsFailure": {"class": "HcuBinarySensor", "name": "Mains Power", "device_class": BinarySensorDeviceClass.POWER, "on_state": False},

    # --- OTHER PLATFORMS (used for discovery logic) ---
    "on": {"class": "HcuSwitch"},
    "wateringActive": {"class": "HcuWateringSwitch"},
    "dimLevel": {"class": "HcuLight"},
    "shutterLevel": {"class": "HcuCover"},
    "doorState": {"class": "HcuGarageDoorCover"},
    "lockState": {"class": "HcuLock"},
}

# This dictionary maps a specific channel type from the HCU API to event-based entities.
HMIP_CHANNEL_TYPE_TO_ENTITY = {
    "ACOUSTIC_SIGNAL_VIRTUAL_RECEIVER": {"class": "HcuSoundButton"},
    "SWITCH_INPUT": {"class": "HcuButtonPressSensor"},
    "WALL_MOUNTED_REMOTE_CONTROL_CHANNEL": {"class": "HcuButtonPressSensor"},
    "KEY_REMOTE_CONTROL_CHANNEL": {"class": "HcuButtonPressSensor"},
    "MULTI_MODE_INPUT_CHANNEL": {"class": "HcuButtonPressSensor"},
}