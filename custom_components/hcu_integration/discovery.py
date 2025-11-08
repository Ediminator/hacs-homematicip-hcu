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
    HMIP_CHANNEL_TYPE_TO_ENTITY,
    HMIP_FEATURE_TO_ENTITY,
    PLATFORMS,
    EVENT_CHANNEL_TYPES,
)

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


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
        "HcuLightGroup": light,
        "HcuSiren": siren,
        "HcuSwitch": switch,
        "HcuWateringSwitch": switch,
        "HcuSwitchGroup": switch,
        "HcuCover": cover,
        "HcuGarageDoorCover": cover,
        "HcuCoverGroup": cover,
        "HcuDoorbellEvent": event,
        "HcuLock": lock,
        "HcuResetEnergyButton": button,
        "HcuDoorOpenerButton": button,
        "HcuGenericSensor": sensor,
        "HcuTemperatureSensor": sensor,
        "HcuHomeSensor": sensor,
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
                        entities[platform].append(
                            entity_class(coordinator, client, device_data, channel_index, **init_kwargs)
                        )
                    except (AttributeError, TypeError) as e:
                        _LOGGER.error(
                            "Failed to create entity for channel %s (base: %s, class: %s): %s",
                            channel_type, base_channel_type, class_name, e
                        )

            # Create temperature sensor (prioritize actualTemperature over valveActualTemperature)
            temp_features = {"actualTemperature", "valveActualTemperature"}
            found_temp_feature = next((f for f in temp_features if f in channel_data), None)
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

            # Create feature-based entities (sensors, binary sensors, buttons)
            for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
                if feature in processed_features or feature not in channel_data:
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
                    except (AttributeError, TypeError) as e:
                        _LOGGER.error("Failed to create entity for feature %s (%s): %s", feature, class_name, e)

    # Create group entities (heating, shutter, switching, and light groups)
    for group_data in state.get("groups", {}).values():
        group_type = group_data.get("type")
        if group_type == "HEATING":
            entities[Platform.CLIMATE].append(
                climate.HcuClimate(coordinator, client, group_data, config_entry)
            )
        elif group_type == "SHUTTER":
            entities[Platform.COVER].append(
                cover.HcuCoverGroup(coordinator, client, group_data)
            )
        elif group_type == "SWITCHING":
            entities[Platform.SWITCH].append(
                switch.HcuSwitchGroup(coordinator, client, group_data)
            )
        elif group_type == "LIGHT":
            entities[Platform.LIGHT].append(
                light.HcuLightGroup(coordinator, client, group_data)
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
