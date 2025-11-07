# custom_components/hcu_integration/const.py
"""Constants for the Homematic IP Local (HCU) integration."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    DEGREE,
    LIGHT_LUX,
    PERCENTAGE,
    Platform,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolume,
    UnitOfElectricPotential,
    UnitOfFrequency,
)

# Domain of the integration
DOMAIN = "hcu_integration"

# Platforms to be set up by this integration
PLATFORMS: list[Platform] = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.LIGHT,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
]

# --- Configuration Constants ---
CONF_PIN = "pin"
CONF_AUTH_PORT = "auth_port"
CONF_WEBSOCKET_PORT = "websocket_port"
CONF_ENTITY_PREFIX = "entity_prefix"
DEFAULT_HCU_AUTH_PORT = 6969
DEFAULT_HCU_WEBSOCKET_PORT = 9001
CONF_COMFORT_TEMPERATURE = "comfort_temperature"
DEFAULT_COMFORT_TEMPERATURE = 21.0
DEFAULT_MIN_TEMP = 5.0
DEFAULT_MAX_TEMP = 30.0

# --- API and Plugin Constants ---
PLUGIN_ID = "de.homeassistant.hcu.integration"
PLUGIN_FRIENDLY_NAME = {
    "de": "Home Assistant Integration",
    "en": "Home Assistant Integration",
}

# --- Timing Constants ---
WEBSOCKET_CONNECT_TIMEOUT = 10
WEBSOCKET_RECONNECT_INITIAL_DELAY = 5
WEBSOCKET_RECONNECT_MAX_DELAY = 60
WEBSOCKET_RECONNECT_JITTER_MAX = 5
WEBSOCKET_HEARTBEAT_INTERVAL = 25
WEBSOCKET_RECEIVE_TIMEOUT = 30
API_REQUEST_TIMEOUT = 10
API_MAX_RETRIES = 3
API_RETRY_BASE_DELAY = 1.0

# --- Service Constants ---
SERVICE_PLAY_SOUND = "play_sound"
SERVICE_SET_RULE_STATE = "set_rule_state"
SERVICE_SET_DISPLAY_CONTENT = "set_display_content"
SERVICE_ACTIVATE_PARTY_MODE = "activate_party_mode"
SERVICE_ACTIVATE_VACATION_MODE = "activate_vacation_mode"
SERVICE_ACTIVATE_ECO_MODE = "activate_eco_mode"
SERVICE_DEACTIVATE_ABSENCE_MODE = "deactivate_absence_mode"

# --- Preset Constants ---
PRESET_ECO = "Eco"
PRESET_PARTY = "Party"

# --- Service Attribute Constants ---
ATTR_SOUND_FILE = "sound_file"
ATTR_DURATION = "duration"
ATTR_VOLUME = "volume"
ATTR_RULE_ID = "rule_id"
ATTR_ENABLED = "enabled"
ATTR_END_TIME = "end_time"

# --- API Path Constants ---
API_PATHS = {
    "GET_SYSTEM_STATE": "/hmip/home/getSystemState",
    "SET_SWITCH_STATE": "/hmip/device/control/setSwitchState",
    "SET_WATERING_SWITCH_STATE": "/hmip/device/control/setWateringSwitchState",
    "SET_DIM_LEVEL": "/hmip/device/control/setDimLevel",
    "SET_COLOR_TEMP": "/hmip/device/control/setColorTemperatureDimLevel",
    "SET_HUE": "/hmip/device/control/setHueSaturationDimLevel",
    "SET_SHUTTER_LEVEL": "/hmip/device/control/setShutterLevel",
    "SET_SLATS_LEVEL": "/hmip/device/control/setSlatsLevel",
    "STOP_COVER": "/hmip/device/control/stop",
    "SEND_DOOR_COMMAND": "/hmip/device/control/sendDoorCommand",
    "TOGGLE_GARAGE_DOOR_STATE": "/hmip/device/control/toggleGarageDoorState",
    "SET_LOCK_STATE": "/hmip/device/control/setLockState",
    "SET_SOUND_FILE": "/hmip/device/control/setSoundFileVolumeLevelWithTime",
    "RESET_ENERGY_COUNTER": "/hmip/device/control/resetEnergyCounter",
    "ENABLE_SIMPLE_RULE": "/hmip/rule/enableSimpleRule",
    "ACTIVATE_VACATION": "/hmip/home/heating/activateVacation",
    "DEACTIVATE_VACATION": "/hmip/home/heating/deactivateVacation",
    "ACTIVATE_ABSENCE_PERMANENT": "/hmip/home/heating/activateAbsencePermanent",
    "DEACTIVATE_ABSENCE": "/hmip/home/heating/deactivateAbsence",
    "SET_GROUP_BOOST": "/hmip/group/heating/setBoost",
    "SET_GROUP_CONTROL_MODE": "/hmip/group/heating/setControlMode",
    "SET_GROUP_SET_POINT_TEMP": "/hmip/group/heating/setSetPointTemperature",
    "SET_GROUP_ACTIVE_PROFILE": "/hmip/group/heating/setActiveProfile",
    "SET_ZONES_ACTIVATION": "/hmip/home/security/setExtendedZonesActivation",
    "SET_EPAPER_DISPLAY": "/hmip/device/control/setEpaperDisplay",
    "ACTIVATE_PARTY_MODE": "/hmip/group/heating/activatePartyMode",
    "SET_GROUP_SHUTTER_LEVEL": "/hmip/group/switching/setPrimaryShadingLevel",
    "SET_GROUP_SLATS_LEVEL": "/hmip/group/switching/setSecondaryShadingLevel",
    "STOP_GROUP_COVER": "/hmip/group/switching/stop",
}

# --- Device Identification Constants ---
HCU_DEVICE_TYPES = {
    "HOME_CONTROL_ACCESS_POINT",
    "WIRED_ACCESS_POINT",
    "ACCESS_POINT",
    "WIRED_DIN_RAIL_ACCESS_POINT",
}
HCU_MODEL_TYPES = {"HmIP-HAP", "HmIP-HCU-1"}

DEACTIVATED_BY_DEFAULT_DEVICES = {
    "FLOOR_TERMINAL_BLOCK_12",
    "FLOOR_TERMINAL_BLOCK_6",
    "DIN_RAIL_SWITCH_4",
    "DIN_RAIL_BLIND_4",
    "DIN_RAIL_DIMMER_3",
    "WIRED_DIN_RAIL_SWITCH_8",
    "WIRED_DIN_RAIL_BLIND_4",
    "WIRED_DIN_RAIL_DIMMER_3",
    "OPEN_COLLECTOR_MODULE_8",
}

# --- Entity Mapping Dictionaries ---
HMIP_DEVICE_TYPE_TO_DEVICE_CLASS = {
    "BLIND_ACTUATOR": CoverDeviceClass.BLIND,
    "BRAND_BLIND": CoverDeviceClass.BLIND,
    "HUNTER_DOUGLAS_BLIND": CoverDeviceClass.BLIND,
    "GARAGE_DOOR_CONTROLLER": CoverDeviceClass.GARAGE,
    "GARAGE_DOOR_MODULE": CoverDeviceClass.GARAGE,
    "HOERMANN_DRIVES_MODULE": CoverDeviceClass.GARAGE,
    "SHUTTER_ACTUATOR": CoverDeviceClass.SHUTTER,
    "PLUGABLE_SWITCH": SwitchDeviceClass.OUTLET,
    "PLUGABLE_SWITCH_MEASURING": SwitchDeviceClass.OUTLET,
    "BRAND_SWITCH_MEASURING": SwitchDeviceClass.SWITCH,
    "FULL_FLUSH_SWITCH_16": SwitchDeviceClass.SWITCH,
    "BRAND_SWITCH_16": SwitchDeviceClass.SWITCH,
    "BRAND_SWITCH_2": SwitchDeviceClass.SWITCH,
    "WALL_MOUNTED_GLASS_SWITCH": SwitchDeviceClass.SWITCH,
    "WIRED_DIN_RAIL_SWITCH_8": SwitchDeviceClass.SWITCH,
    "WIRED_DIN_RAIL_BLIND_4": CoverDeviceClass.BLIND,
    "WIRED_DIN_RAIL_DIMMER_3": None,
    "BRAND_DIMMER": None,
    "OPEN_COLLECTOR_MODULE_8": SwitchDeviceClass.SWITCH,
    "DIN_RAIL_SWITCH_1": SwitchDeviceClass.SWITCH,
    "FLUSH_MOUNT_DIMMER": None,
    "CONTACT_INTERFACE_6": None,
    "ENERGY_SENSING_INTERFACE": None,
    "ENERGY_SENSORS_INTERFACE": None,
    "MAINS_FAILURE_SENSOR": None,
    "BRAND_REMOTE_CONTROL_2": None,
    "PUSH_BUTTON_2": None,
    "DOOR_LOCK_DRIVE": None,
    "TEMPERATURE_HUMIDITY_SENSOR_OUTDOOR": None,
    "TILT_VIBRATION_SENSOR": None,
    "GLASS_WALL_THERMOSTAT_CARBON": None,
    "SOIL_MOUNTURE_SENSOR_INTERFACE": None,
    "FLUSH_MOUNT_CONTACT_INTERFACE_1": None,
    "SHUTTER_CONTACT_MAGNETIC": None,
    "WALL_MOUNTED_GLASS_SWITCH_2": None,
    "RADIATOR_THERMOSTAT": None,
    "SHUTTER_CONTACT": None,
    "BRAND_WALL_THERMOSTAT": None,
    "FLOOR_TERMINAL_BLOCK_MOTOR": None,
    "PRESENCE_DETECTOR_INDOOR": None,
    "ALARM_SIREN_INDOOR": None,
    "LIGHT_SENSOR_OUTDOOR": None,
    "PLUGABLE_DIMMER": None,
    "FLUSH_MOUNT_SWITCH_1": SwitchDeviceClass.SWITCH,
    "COMBINATION_SIGNALLING_DEVICE": None,
    "SHUTTER_CONTACT_INVISIBLE": None,
}

HMIP_FEATURE_TO_ENTITY = {
    # Sensor Features
    "actualTemperature": {
        "class": "HcuTemperatureSensor",
        "name": "Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "valveActualTemperature": {
        "class": "HcuTemperatureSensor",
        "name": "Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "humidity": {
        "class": "HcuGenericSensor",
        "name": "Humidity",
        "unit": PERCENTAGE,
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "vaporAmount": {
        "class": "HcuGenericSensor",
        "name": "Absolute Humidity",
        "unit": "g/m³",
        "icon": "mdi:water",
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "illumination": {
        "class": "HcuGenericSensor",
        "name": "Illumination",
        "unit": LIGHT_LUX,
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "currentIllumination": {
        "class": "HcuGenericSensor",
        "name": "Illumination",
        "unit": LIGHT_LUX,
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "averageIllumination": {
        "class": "HcuGenericSensor",
        "name": "Average Illumination",
        "unit": LIGHT_LUX,
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "energyCounter": {
        "class": "HcuGenericSensor",
        "name": "Energy Counter",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "energyCounterOne": {
        "class": "HcuGenericSensor",
        "name": "Energy Counter One",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "energyCounterTwo": {
        "class": "HcuGenericSensor",
        "name": "Energy Counter Two",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "energyCounterThree": {
        "class": "HcuGenericSensor",
        "name": "Energy Counter Three",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "powerProduction": {
        "class": "HcuGenericSensor",
        "name": "Power Production",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "energyProduction": {
        "class": "HcuGenericSensor",
        "name": "Energy Production",
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "currentPowerConsumption": {
        "class": "HcuGenericSensor",
        "name": "Power Consumption",
        "unit": UnitOfPower.WATT,
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "gasVolume": {
        "class": "HcuGenericSensor",
        "name": "Gas Volume",
        "unit": UnitOfVolume.CUBIC_METERS,
        "device_class": SensorDeviceClass.GAS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "currentGasFlow": {
        "class": "HcuGenericSensor",
        "name": "Current Gas Flow",
        "unit": "m³/h",
        "icon": "mdi:meter-gas",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "valvePosition": {
        "class": "HcuGenericSensor",
        "name": "Valve Position",
        "unit": PERCENTAGE,
        "icon": "mdi:pipe-valve",
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "windSpeed": {
        "class": "HcuGenericSensor",
        "name": "Wind Speed",
        "unit": UnitOfSpeed.KILOMETERS_PER_HOUR,
        "device_class": SensorDeviceClass.WIND_SPEED,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "windDirection": {
        "class": "HcuGenericSensor",
        "name": "Wind Direction",
        "unit": DEGREE,
        "icon": "mdi:weather-windy",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "windDirectionVariation": {
        "class": "HcuGenericSensor",
        "name": "Wind Direction Variation",
        "unit": DEGREE,
        "icon": "mdi:weather-windy-variant",
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "moistureLevel": {
        "class": "HcuGenericSensor",
        "name": "Moisture Level",
        "unit": PERCENTAGE,
        "device_class": SensorDeviceClass.MOISTURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "carrierSense": {
        "class": "HcuHomeSensor",
        "name": "Radio Traffic",
        "unit": PERCENTAGE,
        "icon": "mdi:radio-tower",
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "rssiDeviceValue": {
        "class": "HcuGenericSensor",
        "name": "RSSI Device",
        "unit": "dBm",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "rssiPeerValue": {
        "class": "HcuGenericSensor",
        "name": "RSSI Peer",
        "unit": "dBm",
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "accelerationSensorMode": {
        "class": "HcuGenericSensor",
        "name": "Acceleration Sensor Mode",
        "icon": "mdi:axis-arrow",
    },
    "accelerationSensorValueX": {
        "class": "HcuGenericSensor",
        "name": "Acceleration X",
        "icon": "mdi:axis-x-arrow",
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "accelerationSensorValueY": {
        "class": "HcuGenericSensor",
        "name": "Acceleration Y",
        "icon": "mdi:axis-y-arrow",
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "accelerationSensorValueZ": {
        "class": "HcuGenericSensor",
        "name": "Acceleration Z",
        "icon": "mdi:axis-z-arrow",
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "accelerationSensorEventCounter": {
        "class": "HcuGenericSensor",
        "name": "Acceleration Events",
        "icon": "mdi:counter",
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "entity_registry_enabled_default": False,
    },
    "mainsVoltage": {
        "class": "HcuGenericSensor",
        "name": "Mains Voltage",
        "unit": UnitOfElectricPotential.VOLT,
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "supplyVoltage": {
        "class": "HcuGenericSensor",
        "name": "Supply Voltage",
        "unit": UnitOfElectricPotential.VOLT,
        "device_class": SensorDeviceClass.VOLTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "frequency": {
        "class": "HcuGenericSensor",
        "name": "Frequency",
        "unit": UnitOfFrequency.HERTZ,
        "device_class": SensorDeviceClass.FREQUENCY,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "carbonDioxideConcentration": {
        "class": "HcuGenericSensor",
        "name": "CO2 Concentration",
        "unit": CONCENTRATION_PARTS_PER_MILLION,
        "device_class": SensorDeviceClass.CO2,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "temperatureExternalOne": {
        "class": "HcuTemperatureSensor",
        "name": "Temperature External 1",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "temperatureExternalTwo": {
        "class": "HcuTemperatureSensor",
        "name": "Temperature External 2",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "temperatureExternalDelta": {
        "class": "HcuGenericSensor",
        "name": "Temperature Delta",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:thermometer-chevron-up",
    },
    # Binary Sensor Features
    "lowBat": {
        "class": "HcuBinarySensor",
        "name": "Low Battery",
        "device_class": BinarySensorDeviceClass.BATTERY,
    },
    "unreach": {
        "class": "HcuUnreachBinarySensor",
        "name": "Connectivity",
        "device_class": BinarySensorDeviceClass.CONNECTIVITY,
        "entity_category": "diagnostic",
    },
    "windowState": {
        "class": "HcuWindowBinarySensor",
        "name": "Window",
        "device_class": BinarySensorDeviceClass.WINDOW,
    },
    "motionDetected": {
        "class": "HcuBinarySensor",
        "name": "Motion",
        "device_class": BinarySensorDeviceClass.MOTION,
    },
    "presenceDetected": {
        "class": "HcuBinarySensor",
        "name": "Presence",
        "device_class": BinarySensorDeviceClass.OCCUPANCY,
    },
    "illuminationDetected": {
        "class": "HcuBinarySensor",
        "name": "Illumination Detected",
        "device_class": BinarySensorDeviceClass.LIGHT,
    },
    "mainsFailureActive": {
        "class": "HcuBinarySensor",
        "name": "Mains Failure",
        "device_class": BinarySensorDeviceClass.PROBLEM,
    },
    "sabotage": {
        "class": "HcuBinarySensor",
        "name": "Sabotage",
        "device_class": BinarySensorDeviceClass.TAMPER,
    },
    "waterlevelDetected": {
        "class": "HcuBinarySensor",
        "name": "Water Level",
        "device_class": BinarySensorDeviceClass.MOISTURE,
    },
    "smokeDetectorAlarmType": {
        "class": "HcuSmokeBinarySensor",
        "name": "Smoke",
        "device_class": BinarySensorDeviceClass.SMOKE,
    },
    "moistureDetected": {
        "class": "HcuBinarySensor",
        "name": "Moisture",
        "device_class": BinarySensorDeviceClass.MOISTURE,
    },
    "sunshine": {
        "class": "HcuBinarySensor",
        "name": "Sunshine",
        "device_class": BinarySensorDeviceClass.LIGHT,
    },
    "storm": {
        "class": "HcuBinarySensor",
        "name": "Storm",
        "device_class": BinarySensorDeviceClass.SAFETY,
        "entity_registry_enabled_default": False,
    },
    "raining": {
        "class": "HcuBinarySensor",
        "name": "Raining",
        "device_class": BinarySensorDeviceClass.MOISTURE,
    },
    "processing": {
        "class": "HcuBinarySensor",
        "name": "Activity",
        "device_class": BinarySensorDeviceClass.RUNNING,
        "entity_registry_enabled_default": False,
    },
}

EVENT_CHANNEL_TYPES = {
    "WALL_MOUNTED_TRANSMITTER_CHANNEL",
    "KEY_REMOTE_CONTROL_CHANNEL",
    "SWITCH_INPUT_CHANNEL",
    "SINGLE_KEY_CHANNEL",
    "MULTI_MODE_INPUT_CHANNEL",
}

DEVICE_CHANNEL_EVENT_TYPES = frozenset({
    "KEY_PRESS_SHORT",
    "KEY_PRESS_LONG",
    "KEY_PRESS_LONG_START",
    "KEY_PRESS_LONG_STOP",
})

HMIP_CHANNEL_TYPE_TO_ENTITY = {
    "DIMMER_CHANNEL": {"class": "HcuLight"},
    "RGBW_AUTOMATION_CHANNEL": {"class": "HcuLight"},
    "UNIVERSAL_LIGHT_CHANNEL": {"class": "HcuLight"},
    "NOTIFICATION_LIGHT_CHANNEL": {"class": "HcuLight"},
    "NOTIFICATION_MP3_SOUND_CHANNEL": {"class": "HcuNotificationLight"},
    "BACKLIGHT_CHANNEL": {"class": "HcuLight"},
    "ALARM_SIREN_CHANNEL": {"class": "HcuSwitch"},
    "SWITCH_CHANNEL": {"class": "HcuSwitch"},
    "SWITCH_MEASURING_CHANNEL": {"class": "HcuSwitch"},
    "WIRED_SWITCH_CHANNEL": {"class": "HcuSwitch"},
    "MULTI_MODE_INPUT_SWITCH_CHANNEL": {"class": "HcuSwitch"},
    "WATERING_CONTROLLER_CHANNEL": {"class": "HcuWateringSwitch"},
    "CONDITIONAL_SWITCH_CHANNEL": {"class": "HcuSwitch"},
    "OPEN_COLLECTOR_CHANNEL_8": {"class": "HcuSwitch"},
    "SHUTTER_CHANNEL": {"class": "HcuCover"},
    "BLIND_CHANNEL": {"class": "HcuCover"},
    "GARAGE_DOOR_CHANNEL": {"class": "HcuGarageDoorCover"},
    "DOOR_CHANNEL": {"class": "HcuGarageDoorCover"},
    "DOOR_LOCK_CHANNEL": {"class": "HcuLock"},
    "LIGHT_SENSOR_CHANNEL": None,
    "MOTION_DETECTION_CHANNEL": None,
    "CLIMATE_CONTROL_INPUT_CHANNEL": None,
    "CLIMATE_SENSOR_CHANNEL": None,
    "ACCELERATION_SENSOR_CHANNEL": None,
    "WALL_MOUNTED_THERMOSTAT_CARBON_CHANNEL": None,
    "SOIL_MOISTURE_SENSOR_CHANNEL": None,
    "ENERGY_SENSORS_INTERFACE_CHANNEL": None,
    "MAINS_FAILURE_SENSOR_CHANNEL": None,
    "CLIMATE_CONTROL_CHANNEL": None,
    "HEATING_CHANNEL": None,
    "WALL_MOUNTED_THERMOSTAT_CHANNEL": None,
    "SHUTTER_CONTACT_CHANNEL": None,
    "GAS_CHANNEL": None,
    "PRESENCE_DETECTION_CHANNEL": None,
}

# RGB Color mappings for HmIP-MP3P (simpleRGBColorState to HS color)
HMIP_RGB_COLOR_MAP = {
    "BLACK": (0, 0),        # Off/Black
    "BLUE": (240, 100),     # Blue
    "GREEN": (120, 100),    # Green
    "TURQUOISE": (180, 100), # Cyan/Turquoise
    "RED": (0, 100),        # Red
    "PURPLE": (300, 100),   # Purple/Magenta
    "YELLOW": (60, 100),    # Yellow
    "WHITE": (0, 0),        # White (will be handled separately with brightness)
}
