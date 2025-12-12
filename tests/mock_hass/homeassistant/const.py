class Platform:
    COVER = "cover"
    BINARY_SENSOR = "binary_sensor"
    SENSOR = "sensor"
    SWITCH = "switch"
    LIGHT = "light"
    ALARM_CONTROL_PANEL = "alarm_control_panel"
    CLIMATE = "climate"
    BUTTON = "button"
    NUMBER = "number"
    EVENT = "event"
    LOCK = "lock"
    SIREN = "siren"
    # Add others as needed

CONF_HOST = "host"
CONF_TOKEN = "token"

CONCENTRATION_PARTS_PER_MILLION = "ppm"
PERCENTAGE = "%"
UnitOfTemperature = type("UnitOfTemperature", (), {"CELSIUS": "°C"})
UnitOfPower = type("UnitOfPower", (), {"WATT": "W"})
UnitOfEnergy = type("UnitOfEnergy", (), {"KILO_WATT_HOUR": "kWh"})
UnitOfElectricCurrent = type("UnitOfElectricCurrent", (), {"AMPERE": "A"})
UnitOfElectricPotential = type("UnitOfElectricPotential", (), {"VOLT": "V"})
UnitOfFrequency = type("UnitOfFrequency", (), {"HERTZ": "Hz"})
UnitOfInformation = type("UnitOfInformation", (), {"MEGABYTES": "MB"})
UnitOfTime = type("UnitOfTime", (), {"SECONDS": "s", "MINUTES": "min"})
DEGREE = "°"
ATTR_TEMPERATURE = "temperature"
ATTR_ENTITY_ID = "entity_id"
LIGHT_LUX = "lx"
UnitOfLength = type("UnitOfLength", (), {"KILOMETERS": "km", "METERS": "m"})
UnitOfPrecipitationDepth = type("UnitOfPrecipitationDepth", (), {"MILLIMETERS": "mm"})
UnitOfSpeed = type("UnitOfSpeed", (), {"KILOMETERS_PER_HOUR": "km/h"})
UnitOfVolume = type("UnitOfVolume", (), {"CUBIC_METERS": "m³"})

