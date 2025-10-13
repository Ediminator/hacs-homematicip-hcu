from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import (
    alarm_control_panel,
    binary_sensor,
    button,
    climate,
    cover,
    light,
    lock,
    sensor,
    switch,
)
from .api import HcuApiClient
from .const import (
    DEACTIVATED_BY_DEFAULT_DEVICES,
    HMIP_CHANNEL_TYPE_TO_ENTITY,
    HMIP_FEATURE_TO_ENTITY,
)

if TYPE_CHECKING:
    from . import HcuCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_discover_entities(
    hass: HomeAssistant,
    client: HcuApiClient,
    config_entry: ConfigEntry,
    coordinator: "HcuCoordinator",
) -> dict[Platform, list]:
    """
    Discover and instantiate all entities for the integration.
    This function iterates through all devices and their channels provided by the
    HCU API, creating the corresponding Home Assistant entities based on predefined
    mappings.
    """
    entities: dict[Platform, list] = {platform: [] for platform in Platform}
    state = client.state

    class_module_map = {
        "HcuLight": light,
        "HcuSwitch": switch,
        "HcuWateringSwitch": switch,
        "HcuCover": cover,
        "HcuGarageDoorCover": cover,
        "HcuLock": lock,
        "HcuButton": button,
        "HcuGenericSensor": sensor,
        "HcuHomeSensor": sensor,
        "HcuBinarySensor": binary_sensor,
        "HcuWindowBinarySensor": binary_sensor,
        "HcuSmokeBinarySensor": binary_sensor,
        "HcuUnreachBinarySensor": binary_sensor,
    }

    for device_data in state.get("devices", {}).values():
        for channel_index, channel_data in device_data.get(
            "functionalChannels", {}
        ).items():
            
            is_deactivated_by_default_device = (
                device_data.get("type") in DEACTIVATED_BY_DEFAULT_DEVICES
            )
            # An unused channel on these devices is one not assigned to any groups.
            is_unused_channel = (
                is_deactivated_by_default_device
                and len(channel_data.get("groups") or []) == 0
            )

            # 1. Discover entities based on channel type (direct mapping)
            channel_type = channel_data.get("functionalChannelType")
            if channel_mapping := HMIP_CHANNEL_TYPE_TO_ENTITY.get(channel_type):
                # Skip creating primary entities for unused channels on specified multi-channel devices.
                if is_unused_channel:
                    continue

                class_name = channel_mapping["class"]
                if module := class_module_map.get(class_name):
                    try:
                        entity_class = getattr(module, class_name)
                        platform = getattr(entity_class, "PLATFORM")
                        init_kwargs = (
                            {"config_entry": config_entry}
                            if channel_type == "DOOR_LOCK_CHANNEL"
                            else {}
                        )
                        entities[platform].append(
                            entity_class(
                                coordinator,
                                client,
                                device_data,
                                channel_index,
                                **init_kwargs,
                            )
                        )
                    except AttributeError as e:
                        _LOGGER.error(
                            "Failed to create entity for channel type %s: %s",
                            channel_type,
                            e,
                        )

            # 2. Discover entities based on features (iterative mapping)
            for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
                if feature in channel_data:
                    class_name = mapping["class"]
                    if module := class_module_map.get(class_name):
                        try:
                            entity_class = getattr(module, class_name)
                            platform = getattr(entity_class, "PLATFORM")
                            entity_mapping = mapping.copy()

                            # For specified multi-channel devices, only enable entities for channels that are in use.
                            if is_deactivated_by_default_device:
                                entity_mapping["entity_registry_enabled_default"] = not is_unused_channel
                            
                            entities[platform].append(
                                entity_class(
                                    coordinator,
                                    client,
                                    device_data,
                                    channel_index,
                                    feature,
                                    entity_mapping,
                                )
                            )
                        except AttributeError as e:
                            _LOGGER.error(
                                "Failed to create entity for feature %s: %s", feature, e
                            )

    # Discover entities for groups (e.g., Climate)
    for group_data in state.get("groups", {}).values():
        if group_data.get("type") == "HEATING":
            entities[Platform.CLIMATE].append(
                climate.HcuClimate(coordinator, client, group_data, config_entry)
            )

    # Discover entities for the 'home' object
    if "home" in state:
        entities[Platform.ALARM_CONTROL_PANEL].append(
            alarm_control_panel.HcuAlarmControlPanel(coordinator, client)
        )
        entities[Platform.SWITCH].append(switch.HcuHomeSwitch(coordinator, client))

        for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
            if feature in state["home"] and mapping["class"] == "HcuHomeSensor":
                entities[Platform.SENSOR].append(
                    sensor.HcuHomeSensor(coordinator, client, feature, mapping)
                )

    _LOGGER.info(
        "Discovered entities: %s",
        {p.value: len(e) for p, e in entities.items() if e},
    )
    return entities