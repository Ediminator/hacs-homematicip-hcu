import inspect
from collections import defaultdict
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import HcuApiClient
from .const import HMIP_FEATURE_TO_ENTITY, HMIP_CHANNEL_TYPE_TO_ENTITY

if TYPE_CHECKING:
    from . import HcuCoordinator


async def async_discover_entities(
    hass: HomeAssistant,
    client: HcuApiClient,
    config_entry: ConfigEntry,
    coordinator: "HcuCoordinator",
) -> dict[Platform, list]:
    """Discover all entities for the HCU integration."""
    # Defer platform imports to avoid blocking calls during startup
    from . import (
        alarm_control_panel, binary_sensor, button, climate, cover, light, lock, sensor, switch,
    )

    ENTITY_CLASS_MAP = {
        "HcuAlarmControlPanel": alarm_control_panel.HcuAlarmControlPanel,
        "HcuBinarySensor": binary_sensor.HcuBinarySensor,
        "HcuButton": button.HcuButton,
        "HcuClimate": climate.HcuClimate,
        "HcuCover": cover.HcuCover,
        "HcuGarageDoorCover": cover.HcuGarageDoorCover,
        "HcuLight": light.HcuLight,
        "HcuLock": lock.HcuLock,
        "HcuHomeSensor": sensor.HcuHomeSensor,
        "HcuGenericSensor": sensor.HcuGenericSensor,
        "HcuTemperatureSensor": sensor.HcuTemperatureSensor,
        "HcuSwitch": switch.HcuSwitch,
        "HcuWateringSwitch": switch.HcuWateringSwitch,
        "HcuHomeSwitch": switch.HcuHomeSwitch,
    }

    entities = defaultdict(list)
    created_entity_ids = set()

    # Generic device discovery
    for device_data in client.state.get("devices", {}).values():
        if device_data.get("PARENT"):
            continue

        oem = device_data.get("oem")
        if oem and oem != "eQ-3":
            option_key = f"import_{oem.lower().replace(' ', '_')}"
            if not config_entry.options.get(option_key, True):
                continue

        maintenance_channel = device_data.get("functionalChannels", {}).get("0", {})
        is_mains_powered = maintenance_channel.get("lowBat") is None

        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            # Discover by feature
            for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
                if feature not in channel_data:
                    continue

                entity_class_name = mapping.get("class")
                if not entity_class_name:
                    continue
                
                # Special handling for temperature sensors to avoid duplicates
                if feature in ("actualTemperature", "valveActualTemperature"):
                    unique_id = f"{device_data['id']}_{channel_index}_temperature"
                else:
                    unique_id = f"{device_data['id']}_{channel_index}_{feature}"

                if unique_id in created_entity_ids:
                    continue
                
                # Avoid creating a switch for a dimmable light
                if entity_class_name in ("HcuSwitch", "HcuWateringSwitch") and "dimLevel" in channel_data:
                    continue

                # Skip creating battery sensors for mains-powered devices
                if entity_class_name == "HcuBinarySensor" and feature == "lowBat" and is_mains_powered:
                    continue

                # Skip creating binary sensors for boolean values handled by other entities
                if entity_class_name == "HcuGenericSensor" and isinstance(channel_data.get(feature), bool):
                    continue

                # Don't create RSSI sensor for the HCU itself
                if entity_class_name == "HcuGenericSensor" and feature == "rssiDeviceValue" and client.hcu_device_id == device_data["id"]:
                    continue

                # Skip battery level sensor for mains-powered devices
                if entity_class_name == "HcuGenericSensor" and feature == "batteryLevel" and is_mains_powered:
                    continue

                entity_class = ENTITY_CLASS_MAP.get(entity_class_name)
                if entity_class:
                    # Dynamically provide only the arguments that the entity's __init__ expects.
                    # This makes adding new entity types easier without modifying this discovery logic.
                    constructor_params = inspect.signature(entity_class.__init__).parameters
                    args = {
                        "coordinator": coordinator,
                        "client": client,
                        "device_data": device_data,
                        "channel_index": channel_index,
                        "feature": feature,
                        "mapping": mapping,
                        "config_entry": config_entry,
                    }
                    filtered_args = {k: v for k, v in args.items() if k in constructor_params}
                    
                    entities[entity_class.PLATFORM].append(entity_class(**filtered_args))
                    created_entity_ids.add(unique_id)

            # Discover by channel type for event-based sensors (buttons)
            channel_type = channel_data.get("functionalChannelType")
            if mapping := HMIP_CHANNEL_TYPE_TO_ENTITY.get(channel_type):
                if entity_class_name := mapping.get("class"):
                    unique_id = f"{device_data['id']}_{channel_index}_{channel_type.lower()}"
                    if unique_id in created_entity_ids:
                        continue
                    
                    entity_class = ENTITY_CLASS_MAP.get(entity_class_name)
                    if entity_class:
                        entities[entity_class.PLATFORM].append(entity_class(coordinator, client, device_data, channel_index))
                        created_entity_ids.add(unique_id)
    
    # Home-level entities
    home_data = client.state.get("home", {})
    if home_data:
        # Alarm Panel
        if "SECURITY_AND_ALARM" in [h.get("solution") for h in home_data.get("functionalHomes", {}).values()]:
            unique_id = f"{client.hcu_device_id}_security"
            if unique_id not in created_entity_ids:
                entities[Platform.ALARM_CONTROL_PANEL].append(alarm_control_panel.HcuAlarmControlPanel(coordinator, client))
                created_entity_ids.add(unique_id)

        # Vacation Mode Switch
        unique_id = f"{client.hcu_device_id}_vacation_mode"
        if unique_id not in created_entity_ids:
            entities[Platform.SWITCH].append(switch.HcuHomeSwitch(coordinator, client))
            created_entity_ids.add(unique_id)
            
        # Home Sensors (e.g., Radio Traffic)
        for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
            if feature in home_data and mapping.get("class") == "HcuHomeSensor":
                unique_id = f"{client.hcu_device_id}_{feature}"
                if unique_id not in created_entity_ids:
                    entities[Platform.SENSOR].append(sensor.HcuHomeSensor(coordinator, client, feature, mapping))
                    created_entity_ids.add(unique_id)
    
    # Climate groups
    for group_data in client.state.get("groups", {}).values():
        if group_data.get("type") == "HEATING":
            unique_id = group_data["id"]
            if unique_id not in created_entity_ids:
                entities[Platform.CLIMATE].append(climate.HcuClimate(coordinator, client, group_data, config_entry))
                created_entity_ids.add(unique_id)

    return entities
