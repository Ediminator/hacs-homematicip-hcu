# custom_components/hcu_integration/alarm_control_panel.py
"""
Alarm control panel platform for the Homematic IP HCU integration.

This platform creates a single alarm panel entity to control the HCU's security functions.
"""
import logging
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, API_PATHS
from .api import HcuApiClient, HcuApiError
from .entity import HcuHomeBaseEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the alarm control panel platform from a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    client: HcuApiClient = coordinator.client

    # Discover and create the alarm panel if the security solution is active in the HCU state.
    for home in client.state.get("home", {}).get("functionalHomes", {}).values():
        if home.get("solution") == "SECURITY_AND_ALARM":
            async_add_entities([HcuAlarmControlPanel(client)])
            break

class HcuAlarmControlPanel(HcuHomeBaseEntity, AlarmControlPanelEntity):
    """Representation of the HCU Security System."""
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME | AlarmControlPanelEntityFeature.ARM_AWAY
    )
    _attr_code_arm_required = False
    # This integration uses the modern state properties and does not support turning on/off via the switch domain.
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, client: HcuApiClient):
        """Initialize the alarm control panel."""
        super().__init__(client)
        self._attr_name = "Homematic IP Alarm"
        self._attr_unique_id = f"{self._hcu_device_id}_security"
        # HA Core Deprecation: Use _attr_alarm_state instead of _attr_state for optimistic updates.
        self._attr_alarm_state: AlarmControlPanelState | None = None

    @property
    def _security_home(self) -> dict:
        """Helper to return the latest security functional home data from the client's cache."""
        for home in self._home.get("functionalHomes", {}).values():
            if home.get("solution") == "SECURITY_AND_ALARM":
                return home
        return {}

    @callback
    def _handle_update(self, updated_ids: set) -> None:
        """
        Handle a state update signal from the coordinator.
        This is called when the real state has been updated in the client.
        """
        if self._home_uuid in updated_ids:
            # A real state update has arrived from the HCU.
            # Clear the assumed state flag and let HA re-read the state property.
            self._attr_assumed_state = False
            self.async_write_ha_state()

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """
        Return the current state of the alarm control panel.
        
        HA Core Deprecation: This property replaces the generic 'state' property.
        """
        # If an optimistic update is in progress, return the assumed state immediately.
        if self._attr_assumed_state:
            return self._attr_alarm_state

        sec_home = self._security_home
        if not sec_home:
            return None

        if sec_home.get("intrusionAlarmActive") or sec_home.get("safetyAlarmActive"):
            return AlarmControlPanelState.TRIGGERED

        zones = sec_home.get("securityZones", {})
        
        # Ensure zones data is a dictionary before proceeding.
        if not isinstance(zones, dict):
            _LOGGER.warning("Security zones data is not in the expected format: %s", zones)
            return AlarmControlPanelState.DISARMED

        internal_group_id = zones.get("INTERNAL")
        external_group_id = zones.get("EXTERNAL")

        internal_group = self._client.get_group_by_id(internal_group_id) if internal_group_id else {}
        external_group = self._client.get_group_by_id(external_group_id) if external_group_id else {}
        
        internal_active = internal_group.get("active", False)
        external_active = external_group.get("active", False)

        if internal_active and external_active:
            return AlarmControlPanelState.ARMED_AWAY
        if external_active:
            return AlarmControlPanelState.ARMED_HOME
        return AlarmControlPanelState.DISARMED
    
    async def _async_set_alarm_state(self, new_state: AlarmControlPanelState, payload: dict) -> None:
        """Helper to set alarm state with optimistic update and error handling."""
        # 1. Optimistic Update: Immediately set the state in Home Assistant's frontend.
        self._attr_alarm_state = new_state
        self._attr_assumed_state = True
        self.async_write_ha_state()

        # 2. API Call: Send the command to the HCU.
        try:
            await self._client.async_home_control(
                path=API_PATHS.SET_ZONES_ACTIVATION,
                body=payload,
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set alarm state for %s: %s", self.name, err)
            # 3. Revert Optimistic State on Failure: Clear assumed state and force a state refresh.
            self._attr_assumed_state = False
            self.async_write_ha_state()

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._async_set_alarm_state(
            AlarmControlPanelState.DISARMED,
            {"zonesActivation": {"INTERNAL": False, "EXTERNAL": False}}
        )

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command (only external zone active)."""
        await self._async_set_alarm_state(
            AlarmControlPanelState.ARMED_HOME,
            {"zonesActivation": {"INTERNAL": False, "EXTERNAL": True}}
        )

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command (both internal and external zones active)."""
        await self._async_set_alarm_state(
            AlarmControlPanelState.ARMED_AWAY,
            {"zonesActivation": {"INTERNAL": True, "EXTERNAL": True}}
        )