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
    UnitOfPrecipitationDepth,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
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
    Platform.EVENT,
    Platform.LIGHT,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SIREN,
    Platform.SWITCH,
]

# --- Configuration Constants ---
CONF_PIN = "pin"
CONF_AUTH_PORT = "auth_port"
CONF_WEBSOCKET_PORT = "websocket_port"
CONF_ENTITY_PREFIX = "entity_prefix"
CONF_PLATFORM_OVERRIDES = "platform_overrides"  # Dict mapping entity unique_id to platform override
DEFAULT_HCU_AUTH_PORT = 6969
DEFAULT_HCU_WEBSOCKET_PORT = 9001
CONF_ADVANCED_DEBUGGING = "advanced_debugging"
CONF_COMFORT_TEMPERATURE = "comfort_temperature"
CONF_SELECTED_OEMS = "selected_oems"
CONF_DISABLED_OEMS = "disabled_oems"
CONF_DISABLED_GROUPS = "disabled_groups"
DEFAULT_ADVANCED_DEBUGGING = False
DEFAULT_COMFORT_TEMPERATURE = 21.0
DEFAULT_MIN_TEMP = 5.0
DEFAULT_MAX_TEMP = 30.0

# --- Manufacturer Constants ---
MANUFACTURER_EQ3 = "eQ-3"
MANUFACTURER_HUE = "Philips Hue"
MANUFACTURER_3RD_PARTY = "3rd Party"

# --- Device Identification Constants ---
PLUGIN_ID_HUE = "de.eq3.plugin.hue"
DEVICE_TYPE_PLUGIN_EXTERNAL = "PLUGIN_EXTERNAL"
HUE_MODEL_TOKEN = "Hue"
HOMEMATIC_MODEL_PREFIXES = ("HmIP-", "HM-", "ALPHA-", "ELV")

# --- Documentation URLs ---
DOCS_URL_LOCK_PIN_CONFIG = "https://github.com/Ediminator/hacs-homematicip-hcu#step-4-configure-door-lock-pin-optional"

# --- Channel Type Constants ---
CHANNEL_TYPE_MULTI_MODE_INPUT_TRANSMITTER = "MULTI_MODE_INPUT_TRANSMITTER"
CHANNEL_TYPE_MULTI_MODE_INPUT = "MULTI_MODE_INPUT_CHANNEL"
CHANNEL_TYPE_ALARM_SIREN = "ALARM_SIREN_CHANNEL"

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
SERVICE_SWITCH_ON_WITH_TIME = "switch_on_with_time"
SERVICE_SEND_API_COMMAND = "send_api_command"

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
ATTR_ON_TIME = "on_time"
ATTR_PATH = "path"
ATTR_BODY = "body"

# --- API Path Constants ---
API_PATHS = {
    "ACTIVATE_ABSENCE_PERMANENT": "/hmip/home/heating/activateAbsencePermanent",
    "ACTIVATE_PARTY_MODE": "/hmip/group/heating/activatePartyMode",
    "ACTIVATE_VACATION": "/hmip/home/heating/activateVacation",
    "DEACTIVATE_ABSENCE": "/hmip/home/heating/deactivateAbsence",
    "DEACTIVATE_VACATION": "/hmip/home/heating/deactivateVacation",
    "ENABLE_SIMPLE_RULE": "/hmip/rule/enableSimpleRule",
    "GET_SYSTEM_STATE": "/hmip/home/getSystemState",
    "RESET_ENERGY_COUNTER": "/hmip/device/control/resetEnergyCounter",
    "SEND_DOOR_COMMAND": "/hmip/device/control/sendDoorCommand",
    "SEND_DOOR_IMPULSE": "/hmip/device/control/startImpulse",
    "DEVICE_IDENTIFY": "/hmip/device/control/setIdentify",
    "SET_COLOR_TEMP": "/hmip/device/control/setColorTemperatureDimLevel",
    "SET_COLOR_TEMP_WITH_TIME": "/hmip/device/control/setColorTemperatureDimLevelWithTime",
    "SET_DIM_LEVEL": "/hmip/device/control/setDimLevel",
    "SET_DIM_LEVEL_WITH_TIME": "/hmip/device/control/setDimLevelWithTime",
    "SET_EPAPER_DISPLAY": "/hmip/device/control/setEpaperDisplay",
    "SET_GROUP_ACTIVE_PROFILE": "/hmip/group/heating/setActiveProfile",
    "SET_GROUP_BOOST": "/hmip/group/heating/setBoost",
    "SET_GROUP_CONTROL_MODE": "/hmip/group/heating/setControlMode",
    "SET_GROUP_SET_POINT_TEMP": "/hmip/group/heating/setSetPointTemperature",
    "SET_GROUP_SHUTTER_LEVEL": "/hmip/group/switching/setPrimaryShadingLevel",
    "SET_GROUP_SECONDARY_SHADING_LEVEL": "/hmip/group/switching/setSecondaryShadingLevel",
    "SET_HUE": "/hmip/device/control/setHueSaturationDimLevel",
    "SET_HUE_WITH_TIME": "/hmip/device/control/setHueSaturationDimLevelWithTime",
    "SET_LOCK_STATE": "/hmip/device/control/setLockState",
    "SET_OPTICAL_SIGNAL_BEHAVIOUR": "/hmip/device/control/setOpticalSignal",
    "SET_OPTICAL_SIGNAL_BEHAVIOUR_WITH_TIME": "/hmip/device/control/setOpticalSignalWithTime",
    "SET_PRIMARY_SHADING_LEVEL": "/hmip/device/control/setPrimaryShadingLevel",  # For SHADING_CHANNEL devices (e.g., HmIP-HDM1)
    "SET_SHUTTER_LEVEL": "/hmip/device/control/setShutterLevel",
    "SET_SIMPLE_RGB_COLOR_STATE": "/hmip/device/control/setSimpleRGBColorDimLevel",
    "SET_SIMPLE_RGB_COLOR_STATE_WITH_TIME": "/hmip/device/control/setSimpleRGBColorDimLevelWithTime",
    "SET_SLATS_LEVEL": "/hmip/device/control/setSlatsLevel",
    "SET_SOUND_FILE": "/hmip/device/control/setSoundFileVolumeLevelWithTime",
    "SET_SWITCH_STATE": "/hmip/device/control/setSwitchState",
    "SET_SWITCH_STATE_WITH_TIME": "/hmip/device/control/setSwitchStateWithTime",
    "SET_SWITCHING_GROUP_STATE": "/hmip/group/switching/setState",
    "SET_WATERING_SWITCH_STATE": "/hmip/device/control/setWateringSwitchState",
    "SET_ZONES_ACTIVATION": "/hmip/home/security/setExtendedZonesActivation",
    "STOP_COVER": "/hmip/device/control/stop",
    "STOP_GROUP_COVER": "/hmip/group/switching/stop",
    "TOGGLE_GARAGE_DOOR_STATE": "/hmip/device/control/toggleGarageDoorState",
}

# --- Device Identification Constants ---
HCU_DEVICE_TYPES = {
    "HOME_CONTROL_ACCESS_POINT",
    "WIRED_ACCESS_POINT",
    "ACCESS_POINT",
    "WIRED_DIN_RAIL_ACCESS_POINT",
}
HCU_MODEL_TYPES = {"HmIP-HCU-1", "HmIP-HCU1-A", "HmIPW-DRAP"}

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
    "DIGITAL_RADIO_INPUT_32",  # HmIP-DRI32 - Input-only device
}

# Devices with multi-function channels that serve dual purposes
# Maps device type to a dict of channel types that have multiple functions
# For HmIP-BSL: NOTIFICATION_LIGHT_CHANNEL serves as BOTH button input AND backlight control
MULTI_FUNCTION_CHANNEL_DEVICES = {
    "BRAND_SWITCH_NOTIFICATION_LIGHT": {
        "NOTIFICATION_LIGHT_CHANNEL": {
            "functions": ["button", "light"],
            "description": "Button input with backlight LED (channels 2-3 on HmIP-BSL)",
        }
    }
}

# --- Entity Mapping Dictionaries ---
# This mapping is used by discovery.py to create Event entities
HMIP_DEVICE_HAS_EVENT = {
    "HmIP-WRC2": {"channels": [1, 2]},
    "HmIP-BRC2": {"channels": [1, 2, 3, 4]},
    "HmIP-WRC6-A": {"channels": [1, 2, 3, 4, 5, 6]},
    "HmIP-FCI6": {"channels": [1, 2, 3, 4, 5, 6]},
    "HmIPW-DRI16": {
        "channels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    },
}

# Devices that require a generic button event entity
GENERIC_BUTTON_DEVICES = {
    "HmIP-WRC2": {"channels": [1, 2]},
    "HmIP-BRC2": {"channels": [1, 2, 3, 4]},
    "HmIP-WRC6-A": {"channels": [1, 2, 3, 4, 5, 6]},
    "HmIP-FCI6": {"channels": [1, 2, 3, 4, 5, 6]},
    "HmIPW-DRI16": {
        "channels": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    },
}


HMIP_OPTIONAL_FEATURE_TO_ENTITY = {
    "IFeatureDeviceIdentify": {
        "class": "HcuDeviceIdentifyButton",
        "requires_data_key": False,
        "simple_init": True,
    }
}


HMIP_DEVICE_TYPE_TO_DEVICE_CLASS = {
    "BLIND_ACTUATOR": CoverDeviceClass.BLIND,
    "BLIND_MODULE": CoverDeviceClass.BLIND,  # HmIP-HDM1 HunterDouglas
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
    "DIGITAL_RADIO_INPUT_32": None,  # HmIP-DRI32 - Input-only device with 32 channels
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
    "TILT_VIBRATION_SENSOR": None,  # Binary sensors handle this
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

UOM_HPA = "hPa"
UOM_UG_M3 = "µg/m³"
UOM_1_CM3 = "1/cm³"
UOM_UM = "µm"

HMIP_FEATURE_TO_ENTITY = {
    # Sensor Features
    "actualTemperature": {
        "class": "HcuTemperatureSensor",
        "name": "Temperature",
        "unit": UnitOfTemperature.CELSIUS,
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    "airPressure": {
        "class": "HcuGenericSensor",
        "name": "Air Pressure",
        "unit": UOM_HPA,
        "device_class": SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:gauge",
    },
    "particulateMassConcentrationOne": {
        "class": "HcuGenericSensor",
        "name": "PM1 Concentration",
        "unit": UOM_UG_M3,
        "device_class": SensorDeviceClass.PM1,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:blur",
    },
    "particulateMassConcentrationOneAverage": {
        "class": "HcuGenericSensor",
        "name": "PM1 Concentration (Average)",
        "unit": UOM_UG_M3,
        "device_class": SensorDeviceClass.PM1,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:blur",
    },
    "particulateNumberConcentrationOne": {
        "class": "HcuGenericSensor",
        "name": "PM1 Number Concentration",
        "unit": UOM_1_CM3,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:counter",
    },
    "particulateMassConcentrationTwoPointFive": {
        "class": "HcuGenericSensor",
        "name": "PM2.5 Concentration",
        "unit": UOM_UG_M3,
        "device_class": SensorDeviceClass.PM25,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:blur",
    },
    "particulateMassConcentrationTwoPointFiveAverage": {
        "class": "HcuGenericSensor",
        "name": "PM2.5 Concentration (Average)",
        "unit": UOM_UG_M3,
        "device_class": SensorDeviceClass.PM25,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:blur",
    },
    "particulateNumberConcentrationTwoPointFive": {
        "class": "HcuGenericSensor",
        "name": "PM2.5 Number Concentration",
        "unit": UOM_1_CM3,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:counter",
    },
    "particulateNumberConcentrationTwoPointFiveAverage": {
        "class": "HcuGenericSensor",
        "name": "PM2.5 Number Concentration (Average)",
        "unit": UOM_1_CM3,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:counter",
    },
    "airQualityIndexTwoPointFive": {
        "class": "HcuGenericSensor",
        "name": "AQI (PM2.5)",
        "device_class": SensorDeviceClass.AQI,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:air-filter",
    },
    "particulateMassConcentrationTen": {
        "class": "HcuGenericSensor",
        "name": "PM10 Concentration",
        "unit": UOM_UG_M3,
        "device_class": SensorDeviceClass.PM10,
        "state_class": SensorStateClass.MEASUREMENT,
        "icon": "mdi:blur",
    },
    "particulateMassConcentrationTenAverage": {
        "class": "HcuGenericSensor",
        "name": "PM10 Concentration (Average)",
        "unit": UOM_UG_M3,
        "device_class": SensorDeviceClass.PM10,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:blur",
    },
    "particulateNumberConcentrationTen": {
        "class": "HcuGenericSensor",
        "name": "PM10 Number Concentration",
        "unit": UOM_1_CM3,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:counter",
    },
    "particulateNumberConcentrationTenAverage": {
        "class": "HcuGenericSensor",
        "name": "PM10 Number Concentration (Average)",
        "unit": UOM_1_CM3,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:counter",
    },
    "airQualityIndexTen": {
        "class": "HcuGenericSensor",
        "name": "AQI (PM10)",
        "device_class": SensorDeviceClass.AQI,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:air-filter",
    },
    "particulateTypicalSize": {
        "class": "HcuGenericSensor",
        "name": "Typical Particle Size",
        "unit": UOM_UM,
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
        "icon": "mdi:ruler",
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
    "totalRainCounter": {
        "class": "HcuGenericSensor",
        "name": "Total Rain",
        "unit": UnitOfPrecipitationDepth.MILLIMETERS,
        "device_class": SensorDeviceClass.PRECIPITATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:weather-pouring",
    },
    "todayRainCounter": {
        "class": "HcuGenericSensor",
        "name": "Today's Rain",
        "unit": UnitOfPrecipitationDepth.MILLIMETERS,
        "device_class": SensorDeviceClass.PRECIPITATION,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:weather-rainy",
    },
    "yesterdayRainCounter": {
        "class": "HcuGenericSensor",
        "name": "Yesterday's Rain",
        "unit": UnitOfPrecipitationDepth.MILLIMETERS,
        "device_class": SensorDeviceClass.PRECIPITATION,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:weather-rainy",
    },
    "totalSunshineDuration": {
        "class": "HcuGenericSensor",
        "name": "Total Sunshine Duration",
        "unit": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "icon": "mdi:weather-sunny",
    },
    "todaySunshineDuration": {
        "class": "HcuGenericSensor",
        "name": "Today's Sunshine Duration",
        "unit": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:weather-partly-cloudy",
    },
    "yesterdaySunshineDuration": {
        "class": "HcuGenericSensor",
        "name": "Yesterday's Sunshine Duration",
        "unit": UnitOfTime.MINUTES,
        "device_class": SensorDeviceClass.DURATION,
        "state_class": SensorStateClass.TOTAL,
        "icon": "mdi:weather-sunset",
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
    "dutyCycle": {
        "class": "HcuHomeSensor",
        "name": "Duty Cycle",
        "unit": PERCENTAGE,
        "icon": "mdi:radio-tower",
        "state_class": SensorStateClass.MEASUREMENT,
        "entity_registry_enabled_default": False,
    },
    "dutyCycleLevel": {
        "class": "HcuGenericSensor",
        "name": "Duty Cycle Level",
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
    "accelerationSensorTriggered": {
        "class": "HcuBinarySensor",
        "name": "Acceleration Sensor Triggered",
        "icon": "mdi:accelerometer",
        "device_class": BinarySensorDeviceClass.VIBRATION,
    },
    "accelerationSensorEventCounter": {
        "class": "HcuGenericSensor",
        "name": "Acceleration Events",
        "icon": "mdi:counter",
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "entity_registry_enabled_default": False,
    },
    "tiltState": {
        "class": "HcuGenericSensor",
        "name": "Tilt State",
        "icon": "mdi:axis-z-rotate-clockwise",
    },
    "absoluteAngle": {
        "class": "HcuGenericSensor",
        "name": "Absolute Angle",
        "icon": "mdi:angle-acute",
        "unit": DEGREE,
        "state_class": SensorStateClass.MEASUREMENT,
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

# Special mapping for dutyCycle binary sensor (device-level warning flag)
# Note: dutyCycle exists in both home object (as percentage) and device channels (as boolean)
# This mapping is used for device channels to avoid key collision in HMIP_FEATURE_TO_ENTITY
DUTY_CYCLE_BINARY_SENSOR_MAPPING = {
    "class": "HcuBinarySensor",
    "name": "Duty Cycle Limit",
    "device_class": BinarySensorDeviceClass.PROBLEM,
    "entity_category": "diagnostic",
    "entity_registry_enabled_default": False,
}

# Channel types that send DEVICE_CHANNEL_EVENT messages exclusively
# These should NOT use timestamp-based detection to avoid false positives from configuration changes
DEVICE_CHANNEL_EVENT_ONLY_TYPES = {
    "SINGLE_KEY_CHANNEL",  # HmIP-BRC2, HmIP-WRC2 - sends explicit DEVICE_CHANNEL_EVENT
    "KEY_CHANNEL",  # Modern remote controls - sends explicit DEVICE_CHANNEL_EVENT
    CHANNEL_TYPE_MULTI_MODE_INPUT,  # HmIP-FCI1/6 etc. - sends explicit DEVICE_CHANNEL_EVENT
    CHANNEL_TYPE_MULTI_MODE_INPUT_TRANSMITTER,  # HmIP-FCI1/6 etc. - sends explicit DEVICE_CHANNEL_EVENT
}

# Channel types for timestamp-based button detection
# Note: DEVICE_CHANNEL_EVENT_ONLY_TYPES are intentionally excluded from this set
# to prevent false positives from configuration changes
EVENT_CHANNEL_TYPES = {
    "WALL_MOUNTED_TRANSMITTER_CHANNEL",
    "KEY_REMOTE_CONTROL_CHANNEL",
    "SWITCH_INPUT_CHANNEL",
    # Channel types that were missing from the v1.17.0 fix:
    "BRAND_REMOTE_CONTROL",  # Used by some button devices
    "BRAND_WALL_MOUNTED_TRANSMITTER",  # Used by some wall-mounted switches
    "REMOTE_CONTROL_TRANSMITTER",  # Used by some remote controls
    # Note: HmIP-BSL uses NOTIFICATION_LIGHT_CHANNEL for button inputs (channels 2-3)
    # These are multi-function channels that serve as BOTH button inputs AND backlight LEDs
    # Button events are handled via DEVICE_CHANNEL_EVENT, not timestamp-based detection
}

DEVICE_CHANNEL_EVENT_TYPES = frozenset({
    "KEY_PRESS_SHORT",
    "KEY_PRESS_LONG",
    "KEY_PRESS_LONG_START",
    "KEY_PRESS_LONG_STOP",
    # Some devices (e.g., HmIP-BSL KEY_CHANNEL) may use shorter event names
    "PRESS_SHORT",
    "PRESS_LONG",
    "PRESS_LONG_START",
    "PRESS_LONG_STOP",
})

HMIP_CHANNEL_TYPE_TO_ENTITY = {
    "DIMMER_CHANNEL": {"class": "HcuLight"},
    "RGBW_AUTOMATION_CHANNEL": {"class": "HcuLight"},
    "UNIVERSAL_LIGHT_CHANNEL": {"class": "HcuLight"},
    "NOTIFICATION_LIGHT_CHANNEL": {"class": "HcuLight"},
    "OPTICAL_SIGNAL_CHANNEL": {"class": "HcuLight"},
    "NOTIFICATION_MP3_SOUND_CHANNEL": {"class": "HcuNotificationLight"},
    "BACKLIGHT_CHANNEL": {"class": "HcuLight"},
    "ALARM_SIREN_CHANNEL": {"class": "HcuSiren"},
    "SWITCH_CHANNEL": {"class": "HcuSwitch"},
    "SWITCH_MEASURING_CHANNEL": {"class": "HcuSwitch"},
    "WIRED_SWITCH_CHANNEL": {"class": "HcuSwitch"},
    "MULTI_MODE_INPUT_SWITCH_CHANNEL": {"class": "HcuSwitch"},
    CHANNEL_TYPE_MULTI_MODE_INPUT_TRANSMITTER: {"class": "HcuDoorbellEvent"},
    "WATERING_CONTROLLER_CHANNEL": {"class": "HcuWateringSwitch"},
    "CONDITIONAL_SWITCH_CHANNEL": {"class": "HcuSwitch"},
    "OPEN_COLLECTOR_CHANNEL_8": {"class": "HcuSwitch"},
    "SHUTTER_CHANNEL": {"class": "HcuCover"},
    "BLIND_CHANNEL": {"class": "HcuCover"},
    "BRAND_BLIND_CHANNEL": {"class": "HcuCover"},  # For HmIP-HDM1 HunterDouglas blinds
    "SHADING_CHANNEL": {"class": "HcuCover"},  # For HmIP-HDM1 HunterDouglas shading actuators
    "GARAGE_DOOR_CHANNEL": {"class": "HcuGarageDoorCover"},
    "DOOR_CHANNEL": {"class": "HcuGarageDoorCover"},
    "DOOR_SWITCH_CHANNEL": {"class": "HcuDoorOpenerButton"},
    "IMPULSE_OUTPUT_CHANNEL": {"class": "HcuDoorImpulseButton"},
    "DOOR_LOCK_CHANNEL": {"class": "HcuLock"},
    "ROTARY_HANDLE_CHANNEL": {"class": "HcuWindowStateSensor"},
    # Event channel types - create HcuButtonEvent entities for button devices
    "KEY_CHANNEL": {"class": "HcuButtonEvent"},  # For HmIP-WRC2, HmIP-BRC2, HmIP-WRC6-A, HmIP-WKP
    "WALL_MOUNTED_TRANSMITTER_CHANNEL": {"class": "HcuButtonEvent"},
    "KEY_REMOTE_CONTROL_CHANNEL": {"class": "HcuButtonEvent"},
    "SWITCH_INPUT_CHANNEL": {"class": "HcuButtonEvent"},
    "SINGLE_KEY_CHANNEL": {"class": "HcuButtonEvent"},
    CHANNEL_TYPE_MULTI_MODE_INPUT: {"class": "HcuButtonEvent"},
    # Channel types that were missing from the v1.17.0 fix - now restored:
    "BRAND_REMOTE_CONTROL": {"class": "HcuButtonEvent"},
    "BRAND_WALL_MOUNTED_TRANSMITTER": {"class": "HcuButtonEvent"},
    "REMOTE_CONTROL_TRANSMITTER": {"class": "HcuButtonEvent"},
    "ACCELERATION_SENSOR_CHANNEL": None,
    "CLIMATE_CONTROL_CHANNEL": None,
    "CLIMATE_CONTROL_INPUT_CHANNEL": None,
    "CLIMATE_SENSOR_CHANNEL": None,
    "ENERGY_SENSORS_INTERFACE_CHANNEL": None,
    "GAS_CHANNEL": None,
    "HEATING_CHANNEL": None,
    "LIGHT_SENSOR_CHANNEL": None,
    "MAINS_FAILURE_SENSOR_CHANNEL": None,
    "MOTION_DETECTION_CHANNEL": None,
    "PRESENCE_DETECTION_CHANNEL": None,
    "SHUTTER_CONTACT_CHANNEL": None,
    "SOIL_MOISTURE_SENSOR_CHANNEL": None,
    "TEMPERATURE_SENSOR_2_EXTERNAL_DELTA_CHANNEL": None,
    "WALL_MOUNTED_THERMOSTAT_CARBON_CHANNEL": None,
    "WALL_MOUNTED_THERMOSTAT_CHANNEL": None,
    "EXTERNAL_SWITCH_CHANNEL": {"class": "HcuSwitch"},
}

# --- Simple RGB Color State Constants ---
# Color values for simpleRGBColorState (HmIP-BSL, HmIP-MP3P, etc.)
# Only the 8 colors officially supported by the HCU API are defined here.
# Note: ORANGE is NOT supported by the API despite appearing in some device specs.
HMIP_COLOR_BLACK = "BLACK"
HMIP_COLOR_WHITE = "WHITE"
HMIP_COLOR_RED = "RED"
HMIP_COLOR_BLUE = "BLUE"
HMIP_COLOR_GREEN = "GREEN"
HMIP_COLOR_YELLOW = "YELLOW"
HMIP_COLOR_PURPLE = "PURPLE"
HMIP_COLOR_TURQUOISE = "TURQUOISE"

# RGB Color mappings for devices with simpleRGBColorState (e.g., HmIP-BSL backlight)
# Maps simpleRGBColorState values to HS color tuples (hue, saturation)
# Based on official HCU API documentation - only 8 colors supported:
# BLACK, BLUE, GREEN, TURQUOISE, RED, PURPLE, YELLOW, WHITE
HMIP_RGB_COLOR_MAP = {
    HMIP_COLOR_BLACK: (0, 0),        # Off/Black
    HMIP_COLOR_BLUE: (240, 100),     # Blue
    HMIP_COLOR_GREEN: (120, 100),    # Green
    HMIP_COLOR_TURQUOISE: (180, 100), # Cyan/Turquoise
    HMIP_COLOR_RED: (0, 100),        # Red
    HMIP_COLOR_PURPLE: (300, 100),   # Purple/Magenta
    HMIP_COLOR_YELLOW: (60, 100),    # Yellow
    HMIP_COLOR_WHITE: (0, 0),        # White (will be handled separately with brightness)
    # Note: Hues in the orange range (15-45°) are mapped to RED or YELLOW depending on proximity.
}

# Optical signal behavior values for HmIP-BSL and similar notification lights
# These control visual effects like blinking, flashing, etc.
HMIP_OPTICAL_SIGNAL_BEHAVIOURS = (
    "off",
    "on",
    "blinking_middle",
    "flash_middle",
    "billow_middle",
)

# Siren tone options for HmIP-ASIR2 and compatible devices
# These acoustic signals can be used with the siren.turn_on service
# Based on official HomematicIP API documentation and HmIP-ASIR2 device specification
HMIP_SIREN_TONES = frozenset({
    # Frequency pattern tones (alarm sounds) - alphabetically sorted
    "FREQUENCY_ALTERNATING_LOW_HIGH",
    "FREQUENCY_ALTERNATING_LOW_MID_HIGH",
    "FREQUENCY_FALLING",
    "FREQUENCY_HIGHON_LONGOFF",
    "FREQUENCY_HIGHON_OFF",
    "FREQUENCY_LOWON_LONGOFF_HIGHON_LONGOFF",
    "FREQUENCY_LOWON_OFF_HIGHON_OFF",
    "FREQUENCY_RISING",
    "FREQUENCY_RISING_AND_FALLING",
    # Status and alert tones - alphabetically sorted
    "DELAYED_EXTERNALLY_ARMED",
    "DELAYED_INTERNALLY_ARMED",
    "DISABLE_ACOUSTIC_SIGNAL",
    "DISARMED",
    "ERROR",
    "EVENT",
    "EXTERNALLY_ARMED",
    "INTERNALLY_ARMED",
    "LOW_BATTERY",
})

# Default siren settings
DEFAULT_SIREN_TONE = "FREQUENCY_RISING"
DEFAULT_SIREN_DURATION = 10.0  # seconds
DEFAULT_SIREN_OPTICAL_SIGNAL = "BLINKING_ALTERNATELY_REPEATING"

# Custom attribute for siren optical signal (not a standard Home Assistant attribute)
ATTR_OPTICAL_SIGNAL = "optical_signal"

# Absence Types
ABSENCE_TYPE_NOT_ABSENT = "NOT_ABSENT"
ABSENCE_TYPE_PARTY = "PARTY"
ABSENCE_TYPE_PERIOD = "PERIOD"
ABSENCE_TYPE_PERMANENT = "PERMANENT"
ABSENCE_TYPE_VACATION = "VACATION"

