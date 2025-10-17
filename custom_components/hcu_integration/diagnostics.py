# custom_components/hcu_integration/diagnostics.py
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN, CONF_PIN
from .api import HcuApiClient


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = coordinator.client

    # Redact sensitive information for privacy
    to_redact_config = {CONF_PIN}
    to_redact_state = {"authtoken", "pin"}

    def _redact_dict(data: dict[str, Any], keys_to_redact: set[str]) -> dict[str, Any]:
        """Recursively redact sensitive data in a dictionary."""
        if not isinstance(data, dict):
            return data
            
        redacted = data.copy()
        for key, value in redacted.items():
            if key in keys_to_redact:
                redacted[key] = "**REDACTED**"
            elif isinstance(value, dict):
                redacted[key] = _redact_dict(value, keys_to_redact)
            elif isinstance(value, list):
                redacted[key] = [_redact_dict(item, keys_to_redact) for item in value]
        return redacted

    redacted_config = {
        "title": config_entry.title,
        "data": _redact_dict(dict(config_entry.data), to_redact_config),
        "options": _redact_dict(dict(config_entry.options), to_redact_config),
    }

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    # Correlate HCU raw data with Home Assistant device and entity data
    correlated_devices = {}
    hcu_devices = client.state.get("devices", {})

    for device_id, hcu_data in hcu_devices.items():
        ha_device = device_registry.async_get_device(identifiers={(DOMAIN, device_id)})
        device_info = {}
        entities = []

        if ha_device:
            device_info = {
                "id": ha_device.id,
                "manufacturer": ha_device.manufacturer,
                "model": ha_device.model,
                "name": ha_device.name,
                "sw_version": ha_device.sw_version,
                "via_device_id": ha_device.via_device_id,
                "area_id": ha_device.area_id,
                "name_by_user": ha_device.name_by_user,
                "disabled_by": ha_device.disabled_by,
            }
            
            ha_entities = er.async_entries_for_device(entity_registry, ha_device.id)
            for entity in ha_entities:
                state = hass.states.get(entity.entity_id)
                entities.append({
                    "entity_id": entity.entity_id,
                    "unique_id": entity.unique_id,
                    "state": state.as_dict() if state else "NOT_FOUND",
                    "disabled_by": entity.disabled_by,
                })

        correlated_devices[device_id] = {
            "hcu_data": _redact_dict(hcu_data, to_redact_state),
            "ha_device": device_info or "NOT_IN_REGISTRY",
            "ha_entities": entities,
        }

    # Correlate HCU group data with Home Assistant virtual devices and entities
    correlated_groups = {}
    hcu_groups = client.state.get("groups", {})

    for group_id, hcu_group_data in hcu_groups.items():
        ha_device = device_registry.async_get_device(identifiers={(DOMAIN, group_id)})
        device_info = {}
        entities = []

        if ha_device:
            device_info = {
                "id": ha_device.id,
                "manufacturer": ha_device.manufacturer,
                "model": ha_device.model,
                "name": ha_device.name,
                "sw_version": ha_device.sw_version,
                "via_device_id": ha_device.via_device_id,
                "area_id": ha_device.area_id,
                "name_by_user": ha_device.name_by_user,
                "disabled_by": ha_device.disabled_by,
            }
            
            ha_entities = er.async_entries_for_device(entity_registry, ha_device.id)
            for entity in ha_entities:
                state = hass.states.get(entity.entity_id)
                entities.append({
                    "entity_id": entity.entity_id,
                    "unique_id": entity.unique_id,
                    "state": state.as_dict() if state else "NOT_FOUND",
                    "disabled_by": entity.disabled_by,
                })
        
        correlated_groups[group_id] = {
            "hcu_data": _redact_dict(hcu_group_data, to_redact_state),
            "ha_device": device_info or "NOT_IN_REGISTRY",
            "ha_entities": entities,
        }


    return {
        "generated_at": dt_util.utcnow().isoformat(),
        "config_entry": redacted_config,
        "devices": correlated_devices,
        "groups": correlated_groups,
    }