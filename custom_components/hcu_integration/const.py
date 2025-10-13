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
CONF_COMFORT_TEMPERATURE = "comfort_temperature"
DEFAULT_COMFORT_TEMPERATURE = 21.0
CONF_AUTH_PORT = "auth_port"
CONF_WEBSOCKET_PORT = "websocket_port"
DEFAULT_HCU_AUTH_PORT = 6969
DEFAULT_HCU_WEBSOCKET_PORT = 9001

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
API_RETRY_DELAY = 2

# --- Service Constants ---
SERVICE_PLAY_SOUND = "play_sound"
SERVICE_SET_RULE_STATE = "set_rule_state"

# --- Service Attribute Constants ---
ATTR_SOUND_FILE = "sound_file"
ATTR_DURATION = "duration"
ATTR_VOLUME = "volume"
ATTR_RULE_ID = "rule_id"
ATTR_ENABLED = "enabled"


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
    "SET_GROUP_BOOST": "/hmip/group/heating/setBoost",
    "SET_GROUP_CONTROL_MODE": "/hmip/group/heating/setControlMode",
    "SET_GROUP_SET_POINT_TEMP": "/hmip/group/heating/setSetPointTemperature",
    "SET_ZONES_ACTIVATION": "/hmip/home/security/setExtendedZonesActivation",
    "SET_EPAPER_DISPLAY": "/hmip/device/control/setEpaperDisplay",
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
}

# --- Entity Mapping Dictionaries ---
HMIP_DEVICE_TYPE_TO_DEVICE_CLASS = {
    "BLIND_ACTUATOR": CoverDeviceClass.BLIND,
    "GARAGE_DOOR_CONTROLLER": CoverDeviceClass.GARAGE,
    "SHUTTER_ACTUATOR": CoverDeviceClass.SHUTTER,
    "PLUGABLE_SWITCH": SwitchDeviceClass.OUTLET,
    "PLUGABLE_SWITCH_MEASURING": SwitchDeviceClass.OUTLET,
}

HMIP_FEATURE_TO_ENTITY = {
    # Sensor Features
    "actualTemperature": {
        "class": "HcuGenericSensor",
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
    "energyCounter": {
        "class": "HcuGenericSensor",
        "name": "Energy Counter",
        "unit": UnitOfEnergy.WATT_HOUR,
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
    "rainCounter": {
        "class": "HcuGenericSensor",
        "name": "Rain Counter",
        "unit": UnitOfLength.MILLIMETERS,
        "device_class": SensorDeviceClass.PRECIPITATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "entity_registry_enabled_default": False,
    },
    "co2Concentration": {
        "class": "HcuGenericSensor",
        "name": "CO2 Concentration",
        "unit": CONCENTRATION_PARTS_PER_MILLION,
        "device_class": SensorDeviceClass.CO2,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "passageCounterValue": {
        "class": "HcuGenericSensor",
        "name": "Passage Counter",
        "icon": "mdi:counter",
        "state_class": SensorStateClass.TOTAL_INCREASING,
    },
    "lastPassageDirection": {
        "class": "HcuGenericSensor",
        "name": "Last Passage Direction",
        "icon": "mdi:arrow-left-right",
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
    },
    "sabotage": {
        "class": "HcuBinarySensor",
        "name": "Sabotage",
        "device_class": BinarySensorDeviceClass.TAMPER,
    },
    "smokeDetectorAlarmType": {
        "class": "HcuSmokeBinarySensor",
        "name": "Smoke Alarm",
        "device_class": BinarySensorDeviceClass.SMOKE,
    },
    "motionDetected": {
        "class": "HcuBinarySensor",
        "name": "Motion",
        "device_class": BinarySensorDeviceClass.MOTION,
    },
    "presenceDetected": {
        "class": "HcuBinarySensor",
        "name": "Presence",
        "device_class": BinarySensorDeviceClass.PRESENCE,
    },
    "windowState": {
        "class": "HcuWindowBinarySensor",
        "name": "Window",
        "device_class": BinarySensorDeviceClass.WINDOW,
    },
    "waterlevelDetected": {
        "class": "HcuBinarySensor",
        "name": "Water",
        "device_class": BinarySensorDeviceClass.MOISTURE,
    },
    "moistureDetected": {
        "class": "HcuBinarySensor",
        "name": "Moisture",
        "device_class": BinarySensorDeviceClass.MOISTURE,
    },
    "dewPointAlarmActive": {
        "class": "HcuBinarySensor",
        "name": "Dew Point Alarm",
        "device_class": BinarySensorDeviceClass.MOISTURE,
    },
    "frostProtectionActive": {
        "class": "HcuBinarySensor",
        "name": "Frost Protection",
        "device_class": BinarySensorDeviceClass.COLD,
    },
    "acousticAlarmActive": {
        "class": "HcuSwitch",
        "name": "Siren",
        "device_class": SwitchDeviceClass.SWITCH,
    },
}

HMIP_CHANNEL_TYPE_TO_ENTITY = {
    "DIMMER_CHANNEL": {"class": "HcuLight"},
    "ALARM_SIREN_CHANNEL": {"class": "HcuSwitch"},
    "SWITCH_CHANNEL": {"class": "HcuSwitch"},
    "WATERING_CONTROLLER_CHANNEL": {"class": "HcuWateringSwitch"},
    "SHUTTER_CHANNEL": {"class": "HcuCover"},
    "BLIND_CHANNEL": {"class": "HcuCover"},
    "GARAGE_DOOR_CHANNEL": {"class": "HcuGarageDoorCover"},
    "DOOR_LOCK_CHANNEL": {"class": "HcuLock"},
    "WALL_MOUNTED_TRANSMITTER_CHANNEL": {"class": "HcuButton"},
    "KEY_REMOTE_CONTROL_CHANNEL": {"class": "HcuButton"},
    "NOTIFICATION_LIGHT_CHANNEL": {"class": "HcuLight"},
}