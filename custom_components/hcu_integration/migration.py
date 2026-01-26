from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er


async def migrate_legacy_uid_if_exists(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    platform: str,
    legacy_unique_id: str,
    new_unique_id: str,
) -> bool:
    ent_reg = er.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(platform, entry.domain, legacy_unique_id)
    if entity_id is None:
        return False
    ent_reg.async_update_entity(entity_id, new_unique_id=new_unique_id)
    return True
