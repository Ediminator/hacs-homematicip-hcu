# custom_components/hcu_integration/const.py
"""Constants for the Homematic IP Local (HCU) integration."""

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.const import (
    PERCENTAGE, UnitOfPower, UnitOfEnergy, UnitOfTemperature, UnitOfSpeed, LIGHT_LUX,
    CONCENTRATION_PARTS_PER_MILLION,
)

DOMAIN = "hcu_integration"
PLATFORMS = ["binary_sensor", "climate", "cover", "light", "lock", "sensor", "switch"]

# Dispatcher signal for entity updates
SIGNAL_UPDATE_ENTITY = f"{DOMAIN}_update"

# Maps HCU device archetypes from the documentation to HA platforms
HMIP_DEVICE_PLATFORM_MAP = {
    # Switch
    "SWITCH": "switch",
    "PLUGABLE_SWITCH": "switch",
    
    # Light
    "LIGHT": "light",
    "DIMMER": "light",
    
    # Cover
    "WINDOW_COVERING": "cover",
    
    # Lock
    "DOOR_LOCK": "lock",
    
    # Sensor / Binary Sensor
    "TEMPERATURE_HUMIDITY_SENSOR": "sensor",
    "TEMPERATURE_HUMIDITY_SENSOR_OUTDOOR": "sensor",
    "CONTACT_SENSOR": "binary_sensor",
    "SMOKE_ALARM": "binary_sensor",
    "OCCUPANCY_SENSOR": "binary_sensor",
    "WATER_SENSOR": ["sensor", "binary_sensor"],
    "CLIMATE_SENSOR": ["sensor", "binary_sensor"],
    "ENERGY_METER": "sensor",
    "PARTICULATE_MATTER_SENSOR": "sensor",
    "BATTERY": "sensor",
    "INVERTER": "sensor",
    "GRID_CONNECTION_POINT": "sensor",
    "VEHICLE": ["sensor"],
    "EV_CHARGER": "sensor",

    # Climate
    "WALL_MOUNTED_THERMOSTAT_PRO": ["sensor", "climate"],
    "THERMOSTAT": ["sensor", "climate"],
    "HEAT_PUMP": "climate",
    "HVAC": "climate",
}

# --- NEW MAPPING FOR DEVICE ICONS ---
HMIP_DEVICE_TO_DEVICE_CLASS = {
    "PLUGABLE_SWITCH": SwitchDeviceClass.OUTLET,
    "SWITCH": SwitchDeviceClass.SWITCH,
    "WINDOW_COVERING": CoverDeviceClass.SHUTTER,
}

# Maps individual data points ("features") to their specific entity configuration
HMIP_FEATURE_MAP = {
    # === SENSOR ===
    "actualTemperature": {"platform": "sensor", "name": "Temperature", "unit": UnitOfTemperature.CELSIUS, "device_class": SensorDeviceClass.TEMPERATURE, "state_class": SensorStateClass.MEASUREMENT},
    "humidity": {"platform": "sensor", "name": "Humidity", "unit": PERCENTAGE, "device_class": SensorDeviceClass.HUMIDITY, "state_class": SensorStateClass.MEASUREMENT},
    "illumination": {"platform": "sensor", "name": "Illuminance", "unit": LIGHT_LUX, "device_class": SensorDeviceClass.ILLUMINANCE, "state_class": SensorStateClass.MEASUREMENT},
    "currentPower": {"platform": "sensor", "name": "Power", "unit": UnitOfPower.WATT, "device_class": SensorDeviceClass.POWER, "state_class": SensorStateClass.MEASUREMENT},
    "energyCounter": {"platform": "sensor", "name": "Energy", "unit": UnitOfEnergy.KILO_WATT_HOUR, "device_class": SensorDeviceClass.ENERGY, "state_class": SensorStateClass.TOTAL_INCREASING},
    "windSpeed": {"platform": "sensor", "name": "Wind Speed", "unit": UnitOfSpeed.KILOMETERS_PER_HOUR, "device_class": SensorDeviceClass.WIND_SPEED, "state_class": SensorStateClass.MEASUREMENT},
    "co2": {"platform": "sensor", "name": "CO2", "unit": CONCENTRATION_PARTS_PER_MILLION, "device_class": SensorDeviceClass.CO2, "state_class": SensorStateClass.MEASUREMENT},
    "batteryLevel": {"platform": "sensor", "name": "Battery Level", "unit": PERCENTAGE, "device_class": SensorDeviceClass.BATTERY, "state_class": SensorStateClass.MEASUREMENT},
    "sunshineDuration": {"platform": "sensor", "name": "Sunshine Duration", "unit": "h", "icon": "mdi:timer-sand", "state_class": SensorStateClass.TOTAL_INCREASING},
    "valvePosition": {"platform": "sensor", "name": "Valve Position", "unit": PERCENTAGE, "icon": "mdi:valve", "state_class": SensorStateClass.MEASUREMENT},
    "rssiDeviceValue": {"platform": "sensor", "name": "Signal Strength", "unit": "dBm", "device_class": SensorDeviceClass.SIGNAL_STRENGTH, "state_class": SensorStateClass.MEASUREMENT},

    # === BINARY_SENSOR ===
    "lowBat": {"platform": "binary_sensor", "name": "Battery", "device_class": BinarySensorDeviceClass.BATTERY},
    "presenceDetected": {"platform": "binary_sensor", "name": "Presence", "device_class": BinarySensorDeviceClass.MOTION},
    "windowState": {"platform": "binary_sensor", "name": "Window", "on_state": "OPEN", "device_class": BinarySensorDeviceClass.WINDOW},
    "smokeAlarm": {"platform": "binary_sensor", "name": "Smoke Alarm", "on_state": "SMOKE_DETECTED", "device_class": BinarySensorDeviceClass.SMOKE},
    "waterlevelDetected": {"platform": "binary_sensor", "name": "Water Level", "device_class": BinarySensorDeviceClass.MOISTURE},
    "moistureDetected": {"platform": "binary_sensor", "name": "Moisture", "device_class": BinarySensorDeviceClass.MOISTURE},
    "raining": {"platform": "binary_sensor", "name": "Raining", "device_class": BinarySensorDeviceClass.MOISTURE},
    "sunshine": {"platform": "binary_sensor", "name": "Sunshine", "device_class": BinarySensorDeviceClass.LIGHT},
    "storm": {"platform": "binary_sensor", "name": "Storm", "device_class": BinarySensorDeviceClass.PROBLEM},

    # === Primary feature check for discovery in platform files ===
    "on": {"platform": "switch"},
    "dimLevel": {"platform": "light"},
    "shutterLevel": {"platform": "cover"},
    "lockState": {"platform": "lock"},
}