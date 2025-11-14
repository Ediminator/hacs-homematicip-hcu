"""Entity discovery logic for the Homematic IP HCU integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import (
    alarm_control_panel,
    binary_sensor,
    button,
    climate,
    cover,
    event,
    light,
    lock,
    sensor,
    siren,
    switch,
)
from .api import HcuApiClient
from .const import (
    CHANNEL_TYPE_MULTI_MODE_INPUT_TRANSMITTER,
    DEACTIVATED_BY_DEFAULT_DEVICES,
    DUTY_CYCLE_BINARY_SENSOR_MAPPING,
    HMIP_CHANNEL_TYPE_TO_ENTITY,
    HMIP_FEATURE_TO_ENTITY,
    PLATFORMS,
    EVENT_CHANNEL_TYPES,
    HMIP_CHANNEL_KEY_ACOUSTIC_ALARM_ACTIVE,
)

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)

# Mapping for window state text sensor (complements binary sensor)
_WINDOW_STATE_SENSOR_MAPPING = {
    "name": "Window State",
    "icon": "mdi:window-open-variant",
}


async def async_discover_entities(
    hass: HomeAssistant,
    client: HcuApiClient,
    config_entry: ConfigEntry,
    coordinator: HcuCoordinator,
) -> dict[Platform, list[Any]]:
    """
    Discover and instantiate all entities for the integration.
    
    This function processes the HCU state data and creates appropriate
    Home Assistant entities based on device types, channel types, and features.
    """
    entities: dict[Platform, list[Any]] = {platform: [] for platform in PLATFORMS}
    state = client.state

    class_module_map = {
        "HcuLight": light,
        "HcuNotificationLight": light,
        "HcuSiren": siren,
        "HcuSwitch": switch,
        "HcuWateringSwitch": switch,
        "HcuCover": cover,
        "HcuGarageDoorCover": cover,
        "HcuDoorbellEvent": event,
        "HcuLock": lock,
        "HcuResetEnergyButton": button,
        "HcuDoorOpenerButton": button,
        "HcuGenericSensor": sensor,
        "HcuTemperatureSensor": sensor,
        "HcuHomeSensor": sensor,
        "HcuWindowStateSensor": sensor,
        "HcuBinarySensor": binary_sensor,
        "HcuWindowBinarySensor": binary_sensor,
        "HcuSmokeBinarySensor": binary_sensor,
        "HcuUnreachBinarySensor": binary_sensor,
        "HcuVacationModeBinarySensor": binary_sensor,
    }

    for device_data in state.get("devices", {}).values():
        for channel_index, channel_data in device_data.get("functionalChannels", {}).items():
            processed_features = set()
            is_deactivated_by_default = device_data.get("type") in DEACTIVATED_BY_DEFAULT_DEVICES
            is_unused_channel = is_deactivated_by_default and not channel_data.get("groups")

            channel_type = channel_data.get("functionalChannelType")
            base_channel_type = None
            channel_mapping = None
            is_main_channel_entity = False # Flag to track if a primary entity (like light/switch) was created

            # Match channel type, including indexed variants (e.g., SWITCH_CHANNEL_1)
            if channel_type in HMIP_CHANNEL_TYPE_TO_ENTITY:
                base_channel_type = channel_type
                channel_mapping = HMIP_CHANNEL_TYPE_TO_ENTITY[base_channel_type]
            elif channel_type:
                for base_type in HMIP_CHANNEL_TYPE_TO_ENTITY:
                    if channel_type.startswith(base_type):
                        base_channel_type = base_type
                        channel_mapping = HMIP_CHANNEL_TYPE_TO_ENTITY[base_channel_type]
                        break

            # Create channel-based entities (lights, switches, covers, locks, event)
            if channel_mapping:
                # Skip EVENT_CHANNEL_TYPES except doorbell (which creates event entities)
                if base_channel_type in EVENT_CHANNEL_TYPES and base_channel_type != CHANNEL_TYPE_MULTI_MODE_INPUT_TRANSMITTER:
                    continue
                if is_unused_channel:
                    continue

                class_name = channel_mapping["class"]
                if module := class_module_map.get(class_name):
                    try:
                        entity_class = getattr(module, class_name)
                        platform = getattr(entity_class, "PLATFORM")
                        init_kwargs = {"config_entry": config_entry} if base_channel_type == "DOOR_LOCK_CHANNEL" else {}

                        # Log siren entity creation for debugging issue #82
                        if class_name == "HcuSiren":
                            _LOGGER.debug(
                                "Creating siren entity: device=%s, channel=%s, type=%s, has_acousticAlarmActive=%s",
                                device_data.get("id"),
                                channel_index,
                                channel_type,
                                HMIP_CHANNEL_KEY_ACOUSTIC_ALARM_ACTIVE in channel_data
                            )

                        entities[platform].append(
                            entity_class(coordinator, client, device_data, channel_index, **init_kwargs)
                        )
                        is_main_channel_entity = True
                    except (AttributeError, TypeError) as e:
                        _LOGGER.error(
                            "Failed to create entity for channel %s (base: %s, class: %s): %s",
                            channel_type, base_channel_type, class_name, e
                        )

            # --- Feature-based entity creation starts here ---
            
            # Create temperature sensor (prioritize actualTemperature over valveActualTemperature)
            temp_features = {"actualTemperature", "valveActualTemperature"}
            found_temp_feature = next((f for f in temp_features if f in channel_data), None)
            
            # Optimization: Skip redundant check for main channel entity if it's NOT a multi-function device.
            # However, for devices like HmIP-BSL (light + stateless button) or devices with both a primary
            # function AND a secondary sensor (like a dimmable switch with power consumption sensor),
            # we must proceed to the feature discovery below.
            
            # The only thing that strictly needs to skip the feature loop is if we intentionally mapped
            # a channel type to 'None' (meaning no entities should be created for this primary type)
            if channel_mapping is None and not is_main_channel_entity:
                continue

            if found_temp_feature:
                try:
                    mapping = HMIP_FEATURE_TO_ENTITY[found_temp_feature]
                    entities[Platform.SENSOR].append(
                        sensor.HcuTemperatureSensor(
                            coordinator, client, device_data, channel_index, found_temp_feature, mapping
                        )
                    )
                    processed_features.update(temp_features)
                except (AttributeError, TypeError) as e:
                    _LOGGER.error("Failed to create temperature sensor for %s: %s", device_data.get("id"), e)

            # Create generic feature-based entities (sensors, binary sensors, buttons)
            for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
                if feature in processed_features or feature not in channel_data:
                    continue

                # Skip HcuHomeSensor entities as they are home-level sensors handled separately
                if mapping.get("class") == "HcuHomeSensor":
                    continue

                # Skip features with null values to prevent broken sensors
                if channel_data[feature] is None:
                    _LOGGER.debug(
                        "Skipping feature '%s' on device %s channel %s: value is null",
                        feature, device_data.get("id"), channel_index
                    )
                    continue

                class_name = mapping["class"]
                if module := class_module_map.get(class_name):
                    try:
                        entity_class = getattr(module, class_name)
                        platform = getattr(entity_class, "PLATFORM")
                        entity_mapping = mapping.copy()
                        if is_deactivated_by_default:
                            entity_mapping["entity_registry_enabled_default"] = not is_unused_channel
                        entities[platform].append(
                            entity_class(coordinator, client, device_data, channel_index, feature, entity_mapping)
                        )

                        # Add reset button for energy counters
                        if feature == "energyCounter":
                            entities[Platform.BUTTON].append(
                                button.HcuResetEnergyButton(coordinator, client, device_data, channel_index)
                            )

                        # Add text sensor for window state (complements binary sensor)
                        if feature == "windowState":
                            entities[Platform.SENSOR].append(
                                sensor.HcuWindowStateSensor(
                                    coordinator, client, device_data, channel_index, feature, _WINDOW_STATE_SENSOR_MAPPING
                                )
                            )
                    except (AttributeError, TypeError) as e:
                        _LOGGER.error("Failed to create entity for feature %s (%s): %s", feature, class_name, e)

            # Special handling for dutyCycle binary sensor (device-level warning flag)
            # Note: dutyCycle exists in both home object (percentage) and device channels (boolean)
            # This is handled separately to avoid key collision in HMIP_FEATURE_TO_ENTITY
            if "dutyCycle" in channel_data and isinstance(channel_data["dutyCycle"], bool):
                try:
                    entity_mapping = DUTY_CYCLE_BINARY_SENSOR_MAPPING.copy()
                    if is_deactivated_by_default:
                        entity_mapping["entity_registry_enabled_default"] = not is_unused_channel
                    entities[Platform.BINARY_SENSOR].append(
                        binary_sensor.HcuBinarySensor(
                            coordinator, client, device_data, channel_index, "dutyCycle", entity_mapping
                        )
                    )
                except (AttributeError, TypeError) as e:
                    _LOGGER.error("Failed to create dutyCycle binary sensor for device %s: %s", device_data.get("id"), e)

    # Create group entities using type mapping
    # Maps group type to (platform, entity_class, extra_kwargs)
    group_type_mapping = {
        "HEATING": (Platform.CLIMATE, climate.HcuClimate, {"config_entry": config_entry}),
        "SHUTTER": (Platform.COVER, cover.HcuCoverGroup, {}),
        "SWITCHING": (Platform.SWITCH, switch.HcuSwitchGroup, {}),
        "LIGHT": (Platform.LIGHT, light.HcuLightGroup, {}),
    }

    for group_data in state.get("groups", {}).values():
        group_type = group_data.get("type")
        if mapping := group_type_mapping.get(group_type):
            # Skip auto-created meta groups for SWITCHING and LIGHT
            # These are created automatically by HCU for rooms and provide unexpected entities
            # User-created functional groups don't have metaGroupId and will still be discovered
            if group_type in ("SWITCHING", "LIGHT"):
                if "metaGroupId" in group_data:
                    _LOGGER.debug(
                        "Skipping auto-created meta %s group '%s'",
                        group_type,
                        group_data.get("label", group_data.get("id"))
                    )
                    continue

            platform, entity_class, extra_kwargs = mapping
            entities[platform].append(
                entity_class(coordinator, client, group_data, **extra_kwargs)
            )

    # Create home-level entities (alarm panel, vacation mode sensor, home sensors)
    if "home" in state:
        entities[Platform.ALARM_CONTROL_PANEL].append(
            alarm_control_panel.HcuAlarmControlPanel(coordinator, client)
        )
        entities[Platform.BINARY_SENSOR].append(
            binary_sensor.HcuVacationModeBinarySensor(coordinator, client)
        )
        for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
            if feature in state["home"] and mapping.get("class") == "HcuHomeSensor":
                entities[Platform.SENSOR].append(
                    sensor.HcuHomeSensor(coordinator, client, feature, mapping)
                )

    _LOGGER.info("Discovered entities: %s", {p.value: len(e) for p, e in entities.items() if e})
    return entities
