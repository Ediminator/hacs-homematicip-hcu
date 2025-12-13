"""Entity discovery logic for the Homematic IP HCU integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import asyncio

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
    DOMAIN,
    DUTY_CYCLE_BINARY_SENSOR_MAPPING,
    HMIP_CHANNEL_TYPE_TO_ENTITY,
    HMIP_FEATURE_TO_ENTITY,
    MULTI_FUNCTION_CHANNEL_DEVICES,
    PLATFORMS,
    EVENT_CHANNEL_TYPES,
)
from .util import get_device_manufacturer

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
        "HcuButtonEvent": event,
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
        # Check if manufacturer is disabled via options
        manufacturer = get_device_manufacturer(device_data)
        if manufacturer != "eQ-3":
            option_key = f"import_{manufacturer.lower().replace(' ', '_')}"
            if not config_entry.options.get(option_key, True):
                _LOGGER.debug(
                    "Skipping device %s (%s) as manufacturer %s is disabled",
                    device_data.get("id"),
                    device_data.get("label"),
                    manufacturer,
                )
                continue

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
                class_name = channel_mapping["class"]
                # Skip EVENT_CHANNEL_TYPES, allowing only specific event entity classes
                if base_channel_type in EVENT_CHANNEL_TYPES and class_name not in (
                    "HcuDoorbellEvent",
                    "HcuButtonEvent",
                ):
                    continue
                if is_unused_channel:
                    continue

                # Note: Some channels serve multiple functions (e.g., HmIP-BSL NOTIFICATION_LIGHT_CHANNEL)
                # - These channels create light entities for backlight control
                # - They ALSO respond to button presses via DEVICE_CHANNEL_EVENT
                # - Button events are handled in __init__.py via _handle_device_channel_events
                # - See MULTI_FUNCTION_CHANNEL_DEVICES in const.py for device-specific mappings
                if module := class_module_map.get(class_name):
                    try:
                        entity_class = getattr(module, class_name)
                        platform = getattr(entity_class, "PLATFORM")
                        init_kwargs = {"config_entry": config_entry} if base_channel_type == "DOOR_LOCK_CHANNEL" else {}

                        # Log siren entity creation for debugging
                        if class_name == "HcuSiren":
                            _LOGGER.debug(
                                "Creating siren entity: device=%s, channel=%s, type=%s",
                                device_data.get("id"),
                                channel_index,
                                channel_type,
                            )

                        entities[platform].append(
                            entity_class(coordinator, client, device_data, channel_index, **init_kwargs)
                        )
                    except (AttributeError, TypeError) as e:
                        _LOGGER.error(
                            "Failed to create entity for device %s, channel %s (type: %s, base: %s, class: %s): %s",
                            device_data.get("id"), channel_index, channel_type, base_channel_type, class_name, e
                        )

            # Handle multi-function channels (e.g., HmIP-BSL NOTIFICATION_LIGHT_CHANNEL)
            # These channels serve multiple purposes and need additional event entities
            device_type = device_data.get("type")
            if device_type in MULTI_FUNCTION_CHANNEL_DEVICES:
                multi_func_config = MULTI_FUNCTION_CHANNEL_DEVICES[device_type].get(base_channel_type or channel_type)
                if multi_func_config and "button" in multi_func_config.get("functions", []):
                    # Create additional button event entity for multi-function channel
                    try:
                        _LOGGER.debug(
                            "Creating button event entity for multi-function channel: device=%s (%s), channel=%s (%s)",
                            device_data.get("id"),
                            device_type,
                            channel_index,
                            channel_type,
                        )
                        entities[Platform.EVENT].append(
                            event.HcuButtonEvent(coordinator, client, device_data, channel_index)
                        )
                    except (AttributeError, TypeError) as e:
                        _LOGGER.error(
                            "Failed to create button event entity for device %s, channel %s (type: %s): %s",
                            device_data.get("id"), channel_index, channel_type, e
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

            # Create generic feature-based entities (sensors, binary sensors, buttons)
            for feature, mapping in HMIP_FEATURE_TO_ENTITY.items():
                if feature in processed_features or feature not in channel_data:
                    continue

                # Skip HcuHomeSensor entities as they are home-level sensors handled separately
                if mapping.get("class") == "HcuHomeSensor":
                    continue

                # Skip dutyCycleLevel sensor for the main HCU device to avoid redundancy
                # with the home-level dutyCycle sensor (HcuHomeSensor)
                if feature == "dutyCycleLevel" and device_data.get("id") == client.hcu_device_id:
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
                        _LOGGER.error(
                            "Failed to create entity for device %s, channel %s, feature %s (%s): %s",
                            device_data.get("id"), channel_index, feature, class_name, e
                        )

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
        "EXTENDED_LINKED_SWITCHING": (Platform.LIGHT, light.HcuLightGroup, {}),
        "EXTENDED_LINKED_SHUTTER": (Platform.COVER, cover.HcuCoverGroup, {}),
    }

    # Track group discovery statistics for diagnostics
    groups_discovered = 0
    groups_skipped_meta = 0
    groups_unknown_type = 0

    # Fetch device registry once before iterating groups
    dev_reg = dr.async_get(hass)

    for group_data in state.get("groups", {}).values():
        group_type = group_data.get("type")
        group_id = group_data.get("id")
        group_label = group_data.get("label", group_id)

        # Skip groups without valid ID (defensive null-checking)
        if not group_id:
            _LOGGER.debug(
                "Skipping group without valid ID (type: %s, label: %s)",
                group_type,
                group_label or "unknown"
            )
            continue

        # Skip and clean up groups with no channels (zombie groups)
        # These are groups that exist in the HCU but contain no devices.
        # They should not be exposed as entities and existing ones should be removed (issue #185).
        channels = group_data.get("channels")

        # A group is a zombie if 'channels' is not a non-empty list.
        if not (isinstance(channels, list) and channels):
            if not isinstance(channels, list) and channels is not None:
                _LOGGER.warning(
                    "Group '%s' (id: %s) has a 'channels' attribute that is not a list: %s. Treating as zombie.",
                    group_label,
                    group_id,
                    type(channels).__name__,
                )
            else:  # This covers None or an empty list.
                _LOGGER.debug(
                    "Skipping group without channels (zombie): %s (id: %s)",
                    group_label,
                    group_id,
                )

            # Cleanup: If this group exists in the device registry, remove it.
            # This handles cases where the group was previously discovered (and created as a device)
            # but is now empty/zombie.
            if device := dev_reg.async_get_device(identifiers={(DOMAIN, group_id)}):
                _LOGGER.debug("Removing zombie group device from registry: %s (id: %s)", group_label, group_id)
                try:
                    dev_reg.async_remove_device(device.id)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _LOGGER.warning("Failed to remove zombie group device '%s' (id: %s)", group_label, group_id, exc_info=True)

            continue

        if mapping := group_type_mapping.get(group_type):
            # Previously we skipped groups with metaGroupId assuming they were only auto-created room groups.
            # However, user-created "Direct Connections" also have metaGroupId (issue #146).
            # We now allow them to be discovered. If users find room groups redundant,
            # we may need a more specific filter or an option in the future.
            if group_type in ("SWITCHING", "LIGHT", "EXTENDED_LINKED_SWITCHING") and "metaGroupId" in group_data:
                _LOGGER.debug(
                    "Discovering %s group '%s' (id: %s) despite having metaGroupId (likely Direct Connection or Room Group)",
                    group_type,
                    group_label,
                    group_id
                )

            platform, entity_class, extra_kwargs = mapping
            entities[platform].append(
                entity_class(coordinator, client, group_data, **extra_kwargs)
            )
            groups_discovered += 1
            _LOGGER.debug(
                "Created %s group entity '%s' (id: %s, type: %s)",
                platform.value,
                group_label,
                group_id,
                group_type
            )
        else:
            # Log unknown group types to help diagnose missing entities
            if group_type:
                _LOGGER.warning(
                    "Unknown group type '%s' for group '%s' (id: %s) - no entity created. "
                    "If you expected an entity for this group, please report this as an issue.",
                    group_type,
                    group_label,
                    group_id
                )
                groups_unknown_type += 1

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

    # Log group discovery summary for diagnostics
    if groups_discovered > 0 or groups_skipped_meta > 0 or groups_unknown_type > 0:
        _LOGGER.info(
            "Group discovery summary: %d created, %d skipped (meta groups), %d unknown types",
            groups_discovered,
            groups_skipped_meta,
            groups_unknown_type
        )

    return entities