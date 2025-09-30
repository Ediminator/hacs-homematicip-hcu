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
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, client: HcuApiClient):
        """Initialize the alarm control panel."""
        super().__init__(client)
        self._attr_name = "Homematic IP Alarm"
        self._attr_unique_id = f"{self._hcu_device_id}_security"
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
        """Handle a state update signal from the coordinator."""
        if self._home_uuid in updated_ids:
            # A real state update has arrived from the HCU.
            # Clear the assumed state flag and optimistic state value,
            # then let HA re-read the state from the coordinator.
            self._attr_alarm_state = None
            self._attr_assumed_state = False
            self.async_write_ha_state()

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current state of the alarm control panel."""
        if self._attr_assumed_state:
            return self._attr_alarm_state

        sec_home = self._security_home
        if not sec_home:
            return None

        if sec_home.get("intrusionAlarmActive") or sec_home.get("safetyAlarmActive"):
            return AlarmControlPanelState.TRIGGERED
        
        # Check if the alarm is in the process of arming.
        if sec_home.get("activationInProgress"):
            return AlarmControlPanelState.ARMING

        zones = sec_home.get("securityZones", {})
        
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
        # When arming, the optimistic state should be 'ARMING', not the final 'ARMED' state.
        if new_state in (AlarmControlPanelState.ARMED_HOME, AlarmControlPanelState.ARMED_AWAY):
            self._attr_alarm_state = AlarmControlPanelState.ARMING
        else:
            self._attr_alarm_state = new_state
        
        self._attr_assumed_state = True
        self.async_write_ha_state()

        try:
            await self._client.async_home_control(
                path=API_PATHS.SET_ZONES_ACTIVATION,
                body=payload,
            )
        except (HcuApiError, ConnectionError) as err:
            _LOGGER.error("Failed to set alarm state for %s: %s", self.name, err)
            self._attr_alarm_state = None
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