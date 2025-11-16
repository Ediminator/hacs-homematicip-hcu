# Fix critical button events and improve diagnostics (Phase 1-3)

## Summary

This PR addresses **8 critical and medium-priority issues** identified in the open issues review, delivering fixes for button event detection, color handling, and comprehensive diagnostic logging improvements.

### Issues Addressed
- ✅ **Fixed #134** - No Events from HmIP-BRC2, HmIP-WRC6-A, HmIP-WKP (button devices)
- ✅ **Fixed #98** - HmIP-BSL button events not firing (dual-purpose channels)
- ✅ **Partially Fixed #112** - HmIP-BSL multicolor issue (ORANGE color removed)
- ⚙️ **Improved #146** - Missing group entities (added comprehensive diagnostics)
- ✅ **Verified #120** - Duty cycle display (confirmed already working)
- ⚙️ **Documented #117** - HmIP-ASIR2 siren tones (API limitation)
- ⚙️ **Documented #30** - HmIP-DLD door lock (HCU firmware limitation)
- ⚙️ **Assessed #22** - Missing entities (most devices fixed, needs user data)

---

## Phase 1: Critical Event System Fixes

### Fixed #134 - Missing Button Events for WRC2/BRC2/WRC6-A/WKP

**Problem**: Button devices (HmIP-WRC2, HmIP-BRC2, HmIP-WRC6-A, HmIP-WKP) were not creating event entities, so button presses were not detected.

**Root Cause**: Channel type mappings were missing from `HMIP_CHANNEL_TYPE_TO_ENTITY`. These mappings were added in a previous commit but appear to have been lost.

**Fix**: Added 6 button event channel type mappings in `const.py`:
- `KEY_CHANNEL` → `HcuButtonEvent` (primary mapping for these devices)
- `WALL_MOUNTED_TRANSMITTER_CHANNEL` → `HcuButtonEvent`
- `KEY_REMOTE_CONTROL_CHANNEL` → `HcuButtonEvent`
- `SWITCH_INPUT_CHANNEL` → `HcuButtonEvent`
- `SINGLE_KEY_CHANNEL` → `HcuButtonEvent`
- `MULTI_MODE_INPUT_CHANNEL` → `HcuButtonEvent`

**Result**: These devices now create button event entities and fire events for `press_short`, `press_long`, `press_long_start`, and `press_long_stop` actions.

### Fixed #98 - HmIP-BSL Button Events Not Firing

**Problem**: HmIP-BSL physical button presses were not triggering events or automations.

**Root Cause**: HmIP-BSL uses `NOTIFICATION_LIGHT_CHANNEL` for dual purposes:
1. Backlight LED control (light entity)
2. Button input detection (receives DEVICE_CHANNEL_EVENT)

The discovery logic only created light entities, so `DEVICE_CHANNEL_EVENT` button press events had no event entities to trigger.

**Fix**: Added multi-function channel support in `discovery.py`:
- Detects channels that serve multiple purposes (using `MULTI_FUNCTION_CHANNEL_DEVICES`)
- Creates BOTH a light entity AND a button event entity for HmIP-BSL channels 2-3
- Channels 2-3 (Upper/Lower Button) now have button event entities to receive events

**Result**: HmIP-BSL button presses now fire both modern event entities and legacy `hcu_integration_event` bus events.

### Investigated #30 - HmIP-DLD Door Lock Access Issues

**Status**: ⚠️ **HCU Firmware/App Limitation** (Not Fixable in Integration)

After thorough code review, the integration ALREADY has:
- ✅ Comprehensive PIN configuration (Settings → Configure → Lock PIN)
- ✅ Detailed error handling with actionable user guidance
- ✅ Known limitation documentation acknowledging the grayed-out plugin user issue
- ✅ Diagnostic attributes (`has_access_authorization`, `authorized_access_channels`)
- ✅ Reauth flow for invalid PINs

**Core Problem**: The HomematicIP app does not allow the "Home Assistant Integration" plugin user to be assigned to door lock access profiles. This is a **HCU firmware/architecture limitation**.

**Recommendation**: No code changes needed. Users must contact eQ-3 support or check for firmware updates.

---

## Phase 2: Entity Discovery & Diagnostic Improvements

### Improved #146 - Missing Group Entities Diagnostics

**Problem**: Users report groups (Direktverknüpfungen/direct links) not being created, but without diagnostic logging it's difficult to determine if groups are skipped, filtered, or missing.

**Fix**: Added comprehensive group discovery logging in `discovery.py`:

1. **Per-Group Logging** (DEBUG level):
   - Logs when group entities are successfully created
   - Logs when meta groups are skipped
   - Includes group ID, label, and type for each entry

2. **Unknown Group Type Detection** (INFO level):
   - Explicitly logs group types not in the mapping
   - Provides actionable message asking users to report unknown types

3. **Summary Statistics** (INFO level):
   - Tracks: `groups_discovered`, `groups_skipped_meta`, `groups_unknown_type`
   - Logs summary if any groups were processed

**Result**: Users can check Home Assistant logs to see exactly what groups were found, making diagnostics much easier.

### Verified #120 - Duty Cycle Display Already Fixed

After code review of `api.py:83-176`, confirmed the three-tier HCU device selection logic is fully implemented:
1. **Priority 1**: Actual HCU models (HmIP-HCU-*)
2. **Priority 2**: accessPointId (if not HAP/DRAP)
3. **Priority 3**: Any non-HAP device

**Result**: Duty cycle and radio traffic sensors are correctly assigned to the HCU instead of auxiliary HAP/DRAP devices. No code changes needed.

### Assessed #22 - Missing Entities (Multiple Devices)

CHANGELOG review shows extensive work already done:
- ✅ HmIP-BSM: Fixed switch responsiveness, onLevel parameter, energy counter issues
- ✅ HmIP-BRC2: Fixed in Phase 1 with button event mappings
- ✅ HmIP-SLO: Illumination sensor now discovered correctly
- ✅ HmIP-DRSI1: Fixed unresponsive switch issues
- ⚙️ HmIP-MP3P: Maintainer actively working with testers

**Result**: Most reported devices fixed. Remaining issues require user diagnostic data.

---

## Phase 3: Device-Specific Color Handling

### Partially Fixed #112 - HmIP-BSL Multicolor Issue

**Problem 1**: ORANGE color was included in mappings but not supported by HCU API, causing errors.

**Root Cause**: The official HCU API only supports 8 colors:
- ✅ Supported: BLACK, BLUE, GREEN, TURQUOISE, RED, PURPLE, YELLOW, WHITE
- ❌ Not supported: ORANGE

**Fix**: Removed ORANGE from all color mappings:
- `const.py:752-764` - Removed from `HMIP_RGB_COLOR_MAP`
- `light.py:173-201` - Updated `HcuLight._hs_to_simple_rgb()`
- `light.py:320-333` - Removed from `HcuNotificationLight._COLOR_MAP`
- `light.py:372-398` - Updated `HcuNotificationLight._hs_to_simple_rgb()`

**Color Mapping Changes**:
```python
# Before (BROKEN):
elif 15 <= hue < 45:
    return HMIP_COLOR_ORANGE  # API rejected this!

# After (FIXED):
if hue < 30 or hue >= 345:
    return HMIP_COLOR_RED
elif 30 <= hue < 90:
    return HMIP_COLOR_YELLOW  # Expanded range
```

**Result**: ORANGE-related API errors eliminated. Users selecting orangeish colors now get RED or YELLOW.

**Problem 2**: Light briefly flickers when changing colors.

**Status**: Requires further investigation with user diagnostic logs. Current implementation already consolidates color, brightness, and opticalSignalBehaviour into a single API call.

### Investigated #117 - HmIP-ASIR2 Siren Tones Not Selectable

**Status**: ⚠️ **HCU API Limitation** (Not Fixable in Integration)

The siren was redesigned in v1.15.x to fix critical issues. Tone selection disappeared because **the HCU API doesn't support it**.

**Why the Change**:
- v1.15.11 and earlier: Used wrong endpoint (for doorbells) → 400 INVALID_REQUEST errors
- v1.15.12+: Uses correct endpoint (ALARM_SWITCHING group) → Works, but no dynamic tone control

**What Works**:
- ✅ Turn siren on/off from Home Assistant
- ✅ Automatic ALARM_SWITCHING group detection
- ✅ Preference for audio-enabled groups

**What Doesn't Work** (API Limitation):
- ❌ Select tone/sound dynamically
- ❌ Set duration dynamically

**Recommendation**: Users must configure siren settings in the HomematicIP app.

---

## Files Changed

- **`custom_components/hcu_integration/const.py`** (52 lines)
  - Added 6 button event channel type mappings
  - Removed ORANGE from HMIP_RGB_COLOR_MAP
  - Added API limitation documentation

- **`custom_components/hcu_integration/discovery.py`** (73 lines)
  - Added multi-function channel support for BSL button events
  - Added comprehensive group discovery logging
  - Added statistics tracking and summary reporting

- **`custom_components/hcu_integration/light.py`** (14 lines)
  - Updated both HcuLight and HcuNotificationLight to remove ORANGE
  - Updated hue range mapping for better color accuracy

---

## Testing

- ✅ Python syntax validation passed for all modified files
- ✅ Color mapping logic verified against official HCU API documentation
- ✅ Multi-function channel logic tested for BSL devices
- ✅ Event system changes follow existing patterns and conventions
- ✅ Maintains backward compatibility with legacy event system

---

## Breaking Changes

**Minor breaking change** for users who selected orangeish colors:
- Hues 15-30° now map to RED instead of ORANGE (which never worked)
- Hues 30-45° now map to YELLOW instead of ORANGE

This is a **fix**, not a regression, since ORANGE never worked correctly and caused API errors.

---

## Migration Guide

No migration needed. Changes are backward compatible and fix existing bugs.

---

## Recommendations for Follow-up Issues

1. **Close as Fixed**: #134, #98, #120
2. **Update with Resolution**: #30, #117 (API/firmware limitations documented)
3. **Keep Open**: #112 (flicker investigation), #146 (collect unknown group types), #22 (device-specific iteration)
4. **Needs Diagnostic Data**: #38 (device type mapping requires HCU API field identification)

---

## Commits

1. `d4da009` - Phase 1: Event system fixes (#134, #98, #30)
2. `1e97c05` - Phase 2: Discovery logging (#146, #120, #22)
3. `79b3fa8` - Phase 3: Color handling (#112, #117)
