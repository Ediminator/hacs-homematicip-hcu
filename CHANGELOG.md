# Changelog

All notable changes to the Homematic IP Local (HCU) integration will be documented in this file.

---

## Version 1.15.9 - 2025-11-11

### 🐛 Bug Fixes

**Fix HmIP-ASIR2 Audio Not Playing - Issue #100**

Fixed critical bug where HmIP-ASIR2 siren tones were not playing when activated. The HCU was rejecting all siren commands with error 400 `INVALID_REQUEST`.

**Root Cause**

The siren was being controlled using the **wrong API endpoint**. The integration was using `/hmip/device/control/setSoundFileVolumeLevelWithTime` (designed for doorbell devices like HmIP-MP3P that play sound *files*), but the HmIP-ASIR2 siren requires control via an **ALARM_SWITCHING group** using the `/hmip/group/switching/setState` endpoint with group-specific parameters.
**Fix HmIP-BSL Light Not Turning On When Setting Color - Issue #108**

Fixed a critical regression from v1.15.7 where HmIP-BSL notification lights would not turn on when setting a color without explicitly specifying brightness.

**Root Cause**

The v1.15.7 fix correctly separated color and dimLevel API calls, but introduced a new bug: it only sent the dimLevel command when `ATTR_BRIGHTNESS` or `ATTR_TRANSITION` was explicitly provided in the service call. This caused lights to remain off when users set colors through the Home Assistant UI (which doesn't send brightness by default).

**Behavior Before This Fix (v1.15.7-1.15.8):**
```python
# Siren controlled via DEVICE API (wrong!)
await client.async_set_sound_file(
    device_id=device_id,
    channel_index=1,
    sound_file=tone,  # HCU rejected with INVALID_REQUEST
    volume=1.0,
    duration=duration
)
# User clicks light and picks red color
# Home Assistant calls: light.turn_on(hs_color=[0, 100])
# No ATTR_BRIGHTNESS in kwargs
↓
1. Set color to RED ✅
2. Skip dimLevel command ❌  (condition was: if ATTR_BRIGHTNESS in kwargs)
3. Light stays OFF (dimLevel remains 0.0)
```

**What Was Fixed**

The siren is now properly controlled through its ALARM_SWITCHING group:

1. **Find ALARM_SWITCHING group** during siren initialization
2. **Use group API** `/hmip/group/switching/setState` instead of device API
3. **Send correct parameters**: `signalAcoustic` (tone), `signalOptical` (LED pattern), `onTime` (duration)
4. **Added tone list corrections**: Fixed incorrect tone names (BATTERY_STATUS→LOW_BATTERY, etc.) and added missing tones (EXTERNALLY_ARMED, INTERNALLY_ARMED, etc.)
5. **Sorted tones alphabetically** within groups for better maintainability
Changed the logic to **always** send dimLevel when setting color or effect on `simpleRGBColorState` devices. The dimLevel value is already correctly calculated from:
- Explicit brightness if provided in kwargs
- Current brightness if light is already on
- Default to full brightness (255) if light is off

**Behavior After This Fix (v1.15.9):**
```python
# Siren controlled via ALARM_SWITCHING GROUP (correct!)
await client.async_set_alarm_switching_group_state(
    group_id=alarm_group_id,
    on=True,
    signal_acoustic=tone,                        # Acoustic tone
    signal_optical="BLINKING_ALTERNATELY_REPEATING",  # LED pattern
    on_time=duration                             # Duration in seconds
)
```

**Impact**
- ✅ Audio tones now play correctly when siren is activated
- ✅ All 18 official HomematicIP acoustic tones work (FREQUENCY_RISING, EXTERNALLY_ARMED, etc.)
- ✅ HCU accepts commands and siren activates immediately
- ✅ LED visual signals work alongside acoustic signals
- ✅ Duration control works properly
- ✅ Turn off command successfully stops the siren

---

## Version 1.15.8 - 2025-11-11

### 🐛 Bug Fixes

**Fix HmIP-BSL False Button Events - Issue #98**

Fixed a critical bug where HmIP-BSL devices triggered false button events whenever the light was toggled via Home Assistant, not just on actual physical button presses. This caused automations to trigger unexpectedly.

**Root Cause**

The integration was treating `SWITCH_CHANNEL` with `DOUBLE_INPUT_SWITCH` internal link configuration as an event channel for timestamp-based button detection. The problem is that this channel's `lastStatusUpdate` timestamp changes whenever the switch state changes - whether from a physical button press OR from a programmatic toggle via Home Assistant.

**Previous behavior (broken):**
```python
# SWITCH_CHANNEL with DOUBLE_INPUT_SWITCH was included in event_channels
# Timestamp-based detection fired on ANY state change:
#   - Physical button press → timestamp changed → event fired ✓
#   - HA light toggle → timestamp changed → event fired ✗ (false positive)
```

**What Was Fixed**

- **Removed DOUBLE_INPUT_SWITCH detection** from `_extract_event_channels()` method
- **HmIP-BSL now uses ONLY DEVICE_CHANNEL_EVENT** for button press detection (no timestamp-based detection)
- **Enhanced logging** with device model, channel index, channel label, and channel type
- **Elevated log level to INFO** for button presses to help diagnose channel identification issues
- **Code cleanup**: Refactored logging using fallback empty dict pattern for cleaner, more concise code

**New behavior (working):**
```python
# SWITCH_CHANNEL excluded from timestamp-based detection
# Button presses detected ONLY via DEVICE_CHANNEL_EVENT:
#   - Physical button press → DEVICE_CHANNEL_EVENT → event fired ✓
#   - HA light toggle → no event fired ✓
```

**Technical Details**

HmIP-BSL device channel structure:
- **Channel 0**: `DEVICE_BASE` (maintenance/status)
- **Channel 1**: `SWITCH_CHANNEL` with `DOUBLE_INPUT_SWITCH` (relay control)
  - State changes on every toggle (physical or programmatic)
  - NOT suitable for timestamp-based button detection
- **Channels 2-3**: `NOTIFICATION_LIGHT_CHANNEL` (button backlights)

Button press events are properly sent via `DEVICE_CHANNEL_EVENT` with the actual channel index that was pressed. The enhanced logging will help identify which channel indices correspond to upper vs lower buttons.

**Enhanced Logging Example**
```
Button press: device=3014F711A00018D9992FBF94 (HmIP-BSL), channel=2 (Upper Button, NOTIFICATION_LIGHT_CHANNEL), event=PRESS_SHORT
# User clicks light and picks red color
# Home Assistant calls: light.turn_on(hs_color=[0, 100])
↓
1. Set color to RED ✅
2. Send dimLevel=1.0 (full brightness) ✅
3. Light turns ON with red color ✅
```

**Impact**
- ✅ HmIP-BSL lights now turn on when setting color from UI
- ✅ Color changes work without requiring explicit brightness
- ✅ Brightness is preserved when changing color on already-on lights
- ✅ Effects (blinking, flashing) now properly turn light on
- ✅ All color control methods work as expected

**Files Changed**
- `custom_components/hcu_integration/light.py` - Removed conditional checks, always send dimLevel for simpleRGBColorState devices

---

## Version 1.15.7 - 2025-11-11

### 🐛 Bug Fixes

**Fix HmIP-BSL Multicolor Functionality - Issue #99**

Fixed a critical bug where HmIP-BSL notification light color changes failed with error `404 UNKNOWN_REQUEST`. The issue affected all HmIP-BSL devices with `NOTIFICATION_LIGHT_CHANNEL` (notification light backlights).

**Root Cause**

The `HcuLight` class was incorrectly sending both `simpleRGBColorState` and `dimLevel` parameters in a single API call to `/hmip/device/control/setSimpleRGBColorState`. The HCU API endpoint only accepts color and optical signal behavior parameters, not dimLevel.

**Previous behavior (broken):**
```python
# Single API call with both color and dimLevel
payload = {"simpleRGBColorState": "RED", "dimLevel": 1.0}
# Result: 404 UNKNOWN_REQUEST error
```

**What Was Fixed**

- **Separated API calls**: Color changes now use `/hmip/device/control/setSimpleRGBColorState` (color only)
- **Separate dimming**: Brightness changes use `/hmip/device/control/setDimLevel` (separate call)
- **Preserved functionality**: All features still work (color, brightness, effects)
- **Proper sequencing**: When both color and brightness are changed, color is set first, then brightness

**New behavior (working):**
```python
# Color/effect API call (no dimLevel)
payload = {"simpleRGBColorState": "RED", "opticalSignalBehaviour": "BLINKING_MIDDLE"}

# Separate brightness API call if needed
await async_set_dim_level(device_id, channel, dim_level)
```

**Impact**
- ✅ HmIP-BSL notification lights now properly change colors
- ✅ All 7 colors work: WHITE, RED, BLUE, GREEN, YELLOW, PURPLE, TURQUOISE
- ✅ Brightness control works independently
- ✅ Optical signal effects (blinking, flashing, billowing) work correctly
- ✅ No more 404 errors when setting colors

---

## Version 1.15.6 - 2025-11-10

### 🐛 Bug Fixes

**Fix Siren JSON Serialization Error (frozenset)**

Fixed a `TypeError: Type is not JSON serializable: frozenset` error that occurred when Home Assistant tried to serialize the siren entity's state and attributes. This error appeared in the logs when the siren entity was loaded or updated.

The issue was caused by assigning the `HMIP_SIREN_TONES` `frozenset` directly to the `_attr_available_tones` attribute in `siren.py`.

The attribute is now correctly converted from a `frozenset` to a `list` during the entity's initialization, resolving the serialization issue.

**Fix Entities Stuck in "Unavailable" State After Startup**

Fixed a bug where entities (especially battery-powered ones like sirens `HmIP-ASIR2` or weather sensors) could get stuck in an `unavailable` state with a `restored: true` attribute after a Home Assistant restart.

- **Root Cause:** The integration would load the entity, which defaults to `unavailable` when restored. It would then wait for a *new* WebSocket event from the device to trigger its first state update. Battery-powered devices that don't change state often (e.g., a siren that isn't triggered) would never send this update, causing the entity to remain "unavailable" indefinitely, even though the coordinator's initial state fetch confirmed it was reachable.
- **The Fix:** The coordinator now forces a state update for *all* discovered entities (devices, groups, and home) immediately after the initial `get_system_state()` call succeeds during startup. This ensures all entities refresh their availability and state from the coordinator's cache right away, moving them from the "restored" state to their correct (available) state without waiting for a push event.

---

## Version 1.15.5 - 2025-11-10

### 🐛 Bug Fixes

#### Fix Missing Entities for Weather Sensors and Other Devices - Issue #71

**Fixed: Entities Disappearing After Updates (HmIP-SWO-PR Weather Sensor)**

Weather sensor entities (HmIP-SWO-PR) and potentially other devices were showing as "unavailable" or missing after HCU updates.

**Root Cause**

The base entity's availability check included `if not self._channel`, which evaluates to `True` when channel data is an empty dict `{}`. This was introduced in commit 2d137f86 (Oct 17, 2025) as part of "Improved Entity Availability" changes.

The problem:
- When `self._channel` returns `{}` (empty dict), Python evaluates `not {}` as `True`
- This caused entities to become unavailable even though devices were reachable
- Many channels (weather sensors, sirens, etc.) have sparse data or are temporarily omitted from HCU updates
- This is normal HCU behavior - channels don't need all state fields in every update

**What Was Fixed**

- **Removed faulty check**: Removed `not self._channel` from base `HcuBaseEntity.available` property
- **Robust availability logic**: Availability now based solely on:
  - Client connection status
  - Device data presence (not channel data)
  - Device reachability (permanentlyReachable flag or maintenance channel status)
- **Updated siren override**: Simplified siren's `available` override to focus on diagnostic logging
- **Documentation**: Added detailed comments explaining why channel data check is intentionally omitted

**Impact**
- ✅ Weather sensor entities (HmIP-SWO-PR) remain available with sparse channel data
- ✅ All entities more resilient to temporary channel data omissions from HCU updates
- ✅ Fixes the same root cause that affected sirens in issue #82
- ✅ No more entities disappearing after integration updates

#### Add Missing Weather Sensor Entities - Issue #22

**Fixed: Rain Counter and Sunshine Duration Sensors Not Created (HmIP-SWO-PL Weather Sensor Plus)**

Weather sensor Plus devices (HmIP-SWO-PL) were missing entities for rain counters and sunshine duration, causing these sensors to show as "unavailable" with "restored: true" in diagnostics.

**Root Cause**

Feature mappings were missing from `const.py` for the following weather sensor fields:
- `totalRainCounter` - Total accumulated rainfall
- `todayRainCounter` - Today's rainfall
- `yesterdayRainCounter` - Yesterday's rainfall
- `totalSunshineDuration` - Total sunshine duration
- `todaySunshineDuration` - Today's sunshine duration
- `yesterdaySunshineDuration` - Yesterday's sunshine duration

Without these mappings, the discovery logic skipped creating entities for these features even though the data was present in the HCU API.

**What Was Fixed**

- **Added rain counter sensors**: All three rain counter features now properly create precipitation sensors
  - Uses `UnitOfPrecipitationDepth.MILLIMETERS` with appropriate device class
  - `totalRainCounter` uses `TOTAL_INCREASING` state class (cumulative total)
  - `todayRainCounter` and `yesterdayRainCounter` use `TOTAL` state class (daily measurements)
- **Added sunshine duration sensors**: All three sunshine duration features now properly create duration sensors
  - Uses `UnitOfTime.MINUTES` with duration device class
  - Proper state classes for total, today, and yesterday measurements
- **Proper icons**: Added weather-appropriate icons (weather-pouring, weather-rainy, weather-sunny, etc.)

**Impact**
- ✅ HmIP-SWO-PL devices now expose all 6 additional weather sensors
- ✅ Rain counter sensors properly track daily and total precipitation
- ✅ Sunshine duration sensors track daily and total sun exposure
- ✅ Entities will be auto-discovered on next integration reload
- ✅ Previously "unavailable" entities will become functional again

---

## Version 1.15.4 - 2025-11-10

This release includes critical bug fixes for siren entities, climate ECO mode, button events, and temperature sensors.

### 🚨 Critical Siren Fix (HmIP-ASIR2) - Issue #82, PR #95

**Fixed: Siren Entity Incorrectly Showing as Unavailable**

HmIP-ASIR2 siren entities were showing as "unavailable" in Home Assistant despite devices being reachable and functioning normally.

#### Root Cause
The base entity's availability check included `if not self._channel`, which evaluates to `True` when channel data is an empty dict `{}`. Since empty dicts are falsy in Python, this caused false unavailability.

ALARM_SIREN_CHANNEL behaves differently from other channel types:
- Often has minimal/sparse data (only metadata fields like `functionalChannelType`, `groups`, `channelRole`)
- May be omitted entirely from some HCU state updates
- Doesn't require state fields when siren is inactive (no `acousticAlarmActive` field present)

#### What Was Fixed
- **Override `available` property**: Removed faulty `not self._channel` check that caused false unavailability
- **Device reachability**: Availability now based solely on device reachability (`permanentlyReachable` flag or maintenance channel status)
- **State synchronization fix**: Critical bug where siren remained stuck in "on" state when `acousticAlarmActive` field disappeared from updates
- **Diagnostic logging**: Added comprehensive logging to troubleshoot availability issues
- **Code quality**: Replaced magic strings with constants (`CHANNEL_TYPE_ALARM_SIREN`, `HMIP_CHANNEL_KEY_ACOUSTIC_ALARM_ACTIVE`)

#### Impact
- ✅ Siren entities remain available as long as device is reachable
- ✅ Empty or missing channel data doesn't affect availability
- ✅ State correctly updates to "off" when `acousticAlarmActive` field is missing
- ✅ No more stuck "on" state issue
- ✅ Reduced log noise during normal sparse updates

### 🌡️ Temperature Sensor Fix (HmIP-STE2-PCB) - Issue #28, PR #90

**Fixed: Missing Temperature Values for External Temperature Sensors**

HmIP-STE2-PCB devices now properly report all three temperature values.

#### What Was Fixed
- **Added `TEMPERATURE_SENSOR_2_EXTERNAL_DELTA_CHANNEL`** to channel type mapping
- **Fixed HcuTemperatureSensor class**: Changed from hardcoded field names to dynamic `_feature` attribute access
- **Three temperature sensors now discovered**:
  - `temperatureExternalOne` - First external sensor
  - `temperatureExternalTwo` - Second external sensor
  - `temperatureExternalDelta` - Temperature difference between sensors

#### Root Cause
The original implementation hardcoded specific temperature field names, causing external sensors to return no values. The sensor class now dynamically accesses the correct temperature field for each entity.

### 🌡️ Climate ECO Mode Fix - PR #92

**Fixed: Climate Preset Mode Not Updating for ECO Modes**

Climate entities now correctly show "ECO" preset mode when ECO mode is activated globally.

#### What Was Fixed
- **Switched to INDOOR_CLIMATE functional group**: Fixed incorrect functional group lookup (was checking `HEATING` instead of `INDOOR_CLIMATE`)
- **Support for PERIOD absence type**: Extended ECO mode recognition to include both `PERMANENT` and `PERIOD` absence types
- **Added `ecoAllowed` validation**: ECO mode only activates when room permits it (thermostats can, underfloor heating cannot)
- **Added absence type constants**: Introduced `ABSENCE_TYPE_PERIOD` and `ABSENCE_TYPE_PERMANENT` to replace magic strings

#### Impact
- ✅ Rooms with thermostats correctly display "ECO" preset when global ECO mode is active
- ✅ Rooms with underfloor heating remain in "Standard" mode (as they cannot use ECO)
- ✅ Preset mode attribute updates properly in Home Assistant UI

### 🔘 Button Event Fix (HmIP-BSL) - Issues #91, #81, PR #93

**Fixed: HmIP-BSL Button Events Not Firing**

Button presses on HmIP-BSL switch actuators now properly trigger `hcu_integration_event` events for automations.

#### Root Cause
The integration incorrectly assumed HmIP-BSL devices used `KEY_CHANNEL` for buttons. In reality, these devices use `SWITCH_CHANNEL` with `DOUBLE_INPUT_SWITCH` configuration. The event extraction method also only processed `DEVICE_CHANGED` events, but HmIP-BSL sends `DEVICE_CHANNEL_EVENT` type events for button presses.

#### What Was Fixed
- **Corrected channel type detection**: Properly handle `SWITCH_CHANNEL` with dual input configuration
- **Fixed event type handling**: Process both `DEVICE_CHANGED` and `DEVICE_CHANNEL_EVENT` events
- **Button events now fire** for all press types: SHORT, LONG, LONG_START, LONG_STOP

#### Device Structure
HmIP-BSL (BRAND_SWITCH_NOTIFICATION_LIGHT) contains:
- Channel 0: Device base configuration
- Channel 1: Switch channel with dual input (physical buttons)
- Channels 2-3: Notification light channels (button backlights)

### 💡 Optical Signal Behavior Support (HmIP-BSL) - Issue #81, PR #93

**Added: Visual Effect Support for HmIP-BSL Notification Lights**

Notification light channels on HmIP-BSL devices now support configurable visual effects beyond simple on/off.

#### New Visual Effects
- **OFF** – No light
- **ON** – Steady illumination
- **BLINKING_MIDDLE** – Medium-speed blinking effect
- **FLASH_MIDDLE** – Medium-speed flash effect
- **BILLOWING_MIDDLE** – Medium-speed pulsing/breathing effect

#### Usage
Set visual effects independently or combine with color and brightness:
```yaml
service: light.turn_on
target:
  entity_id: light.bsl_switch_backlight
data:
  effect: "BLINKING_MIDDLE"
  hs_color: [0, 100]  # Red
  brightness: 255
```

#### Technical Implementation
- Added `opticalSignalBehaviour` field support in HcuNotificationLight
- Immutable `HMIP_OPTICAL_SIGNAL_BEHAVIOURS` constant with all available effects
- Effect list exposed via `effect_list` attribute for Home Assistant UI

---

## Version 1.15.0 - 2025-11-09

### 🪟 Window Sensor State Enhancement (HmIP-SRH)

**Add Dedicated Window State Sensor (GitHub Issue #48)**

The v1.10.0 fix for window state was incomplete - it only exposed the state as an attribute on a binary sensor. This release adds a proper text sensor that shows the actual window state.

#### What Changed
- **New Sensor Entity**: "Window State" sensor now displays "Open", "Tilted", or "Closed" as its main state value
- **Binary Sensor Kept**: The existing binary sensor (on/off) remains for compatibility
- **No More Hidden Attributes**: Users can now see the window state directly without checking attributes

#### Why This Matters
- **v1.10.0 limitation**: Window state (OPEN/TILTED/CLOSED) was only visible as an attribute on the binary sensor
- **Binary sensors** can only show on/off in their main state, making the tilted state invisible in the UI
- **User experience**: The new text sensor makes the state immediately visible in dashboards and automations

#### Usage
Both entities will now appear for HmIP-SRH devices:
- **Binary Sensor**: "Window" - Shows on (open or tilted) / off (closed)
- **Text Sensor**: "Window State" - Shows Open / Tilted / Closed

Use the text sensor in automations that need to distinguish between open and tilted states:
```yaml
trigger:
  - platform: state
    entity_id: sensor.bedroom_window_window_state
    to: "Tilted"
```

### 🔘 Switch Actuator Enhancements (HmIP-BSL)

**Fix Button Event Detection (GitHub Issue #67)**

Button presses on HmIP-BSL switch actuators now properly generate `hcu_integration_event` events.

#### What Was Fixed
- Added `KEY_CHANNEL` to `EVENT_CHANNEL_TYPES`
- BSL button inputs (channels 1-2) now trigger events for automations
- Supports all button press types: SHORT, LONG, LONG_START, LONG_STOP

#### Usage
Button events now work as documented:
```yaml
trigger:
  - platform: event
    event_type: hcu_integration_event
    event_data:
      device_id: "YOUR_BSL_DEVICE_ID"
      channel: 1
      type: "KEY_PRESS_SHORT"
```

**Add Full Color Support for Backlight (GitHub Issue #68)**

The illuminated backlight on HmIP-BSL switches now supports all 7 colors instead of just white.

#### Supported Colors
- **White** (default)
- **Blue**
- **Green**
- **Turquoise** (Light Blue)
- **Red**
- **Violet** (Purple)
- **Yellow**

#### How It Works
- HcuLight entities now detect and handle `simpleRGBColorState`
- Automatic color mapping from HS color picker to closest BSL color
- Uses same RGB system as HmIP-MP3P notification lights

#### Usage
Set backlight color from UI or automation:
```yaml
service: light.turn_on
target:
  entity_id: light.bsl_switch_backlight
data:
  hs_color: [240, 100]  # Blue
```

**Technical Implementation:**
- Added `_has_simple_rgb` detection in HcuLight.__init__
- Enhanced `hs_color` property to read `simpleRGBColorState`
- Added `_hs_to_simple_rgb()` color conversion method
- Modified `async_turn_on()` to use `/hmip/device/control/setRgbDimLevel` API for RGB devices

### 🔊 Siren Enhancements (HmIP-ASIR2)

**Implement Tone and Duration Support for Alarm Sirens (GitHub Issue #73)**

The HMIP-ASIR2 and compatible siren devices now properly support acoustic signal selection and duration control.

#### New Siren Features
- **Tone Selection** - Choose from 18 different acoustic signals:
  - Frequency patterns (rising, falling, alternating, etc.)
  - Status tones (battery, armed, event, error)
  - Customizable alert sounds
- **Duration Control** - Set alarm duration in seconds (default: 10s)
- **Full Home Assistant Siren Integration** - Proper `siren.turn_on` service support with tone and duration parameters

#### Usage Example
```yaml
service: siren.turn_on
target:
  entity_id: siren.alarm_siren
data:
  tone: "FREQUENCY_RISING"
  duration: 30
```

**Technical Details:**
- Added `HMIP_SIREN_TONES` constant with 18 available tones
- Updated siren entity to support `SirenEntityFeature.TONES` and `SirenEntityFeature.DURATION`
- Switched from switch API to sound file API for proper siren control
- Default tone: `FREQUENCY_RISING`, default duration: 10 seconds

### 🪟 Cover Device Support (HmIP-HDM1)

**Add Support for HunterDouglas Blind Devices (GitHub Issue #64)**

Added channel mapping for HmIP-HDM1 (HunterDouglas) roller blinds to properly expose cover entities.

#### Changes
- Added `BRAND_BLIND_CHANNEL` mapping for HunterDouglas and third-party blind devices
- Ensures HDM1 devices appear as controllable covers in Home Assistant

**Note:** This fix is based on device type analysis. If your HDM1 device still doesn't appear, please provide diagnostics via GitHub issue #64.

---

## Version 1.14.0 - 2025-11-09

### 🔒 Door Lock Enhancements (HmIP-DLD)

**Complete Implementation of Lock State Properties (GitHub Issue #30, PR #75)**

This release significantly enhances the door lock integration by implementing missing state properties and diagnostic capabilities that were previously claimed but not implemented.

#### New Lock State Properties
- **`is_locking`** - Returns `True` when lock motor is actively locking
- **`is_unlocking`** - Returns `True` when lock motor is actively unlocking
- **`is_jammed`** - Returns `True` when lock mechanism is jammed
- **`is_opening`** - Returns `True` when lock is opening the latch

These properties enable:
- Real-time lock operation status in Home Assistant UI
- Automation triggers based on lock state (e.g., notify if jammed)
- Better visual feedback during lock/unlock operations

#### Enhanced Diagnostic Attributes

New state attributes for troubleshooting:
- **`motor_state`** - Current motor status ("STOPPED", "LOCKING", "UNLOCKING", "OPENING", "JAMMED")
- **`lock_jammed`** - Boolean jam detection from device channel 0
- **`auto_relock_enabled`** - Whether auto-relock is configured
- **`auto_relock_delay`** - Auto-relock delay in seconds
- **`has_access_authorization`** - Whether plugin has any access authorization
- **`authorized_access_channels`** - List of authorized access profile channels

#### Access Control Diagnostics & Error Messages

**New Permission Error Detection:**
- Detects `ACCESS_DENIED` and `INVALID_REQUEST` errors
- Provides step-by-step instructions for fixing access control issues
- Documents known HCU limitation where plugin user appears grayed out in HomematicIP app
- Helps users diagnose authorization problems via state attributes

**Improved Error Messages:**
- Clear guidance for PIN configuration issues
- Detailed instructions for access profile setup
- Explanation of HCU firmware limitations
- Links to documentation

#### Technical Improvements

**Accurate State Reporting:**
- Fixed critical logic error where properties returned `None` for known states instead of `False`
- `None` now correctly means "state unknown" (device offline/data missing)
- `False` correctly means "we know it's not in this state"
- `True` correctly means "we know it is in this state"
- Improves UI rendering and automation reliability

**Implementation Based on Real Device Data:**
- Refined using actual HmIP-DLD diagnostic data (firmware 1.4.12)
- Removed speculative field checks (`activityState`, `errorJammed`, `sabotage`) that don't exist on HmIP-DLD
- Uses correct field names: `lockJammed` on channel 0, `motorState` and `lockState` on channel 1
- Verified against `IOptionalFeatureDeviceErrorLockJammed` supported feature

**Code Quality:**
- Refactored for maintainability (reduced code duplication)
- Dictionary comprehensions for cleaner attribute assignment
- Proper `None` vs `False` semantics throughout
- Clear inline documentation

#### Known Limitations

**HCU Access Control Issue (Issue #30):**
The HomematicIP app may show the "Home Assistant Integration" plugin user as grayed out or expired, preventing assignment to access profiles. This is a known HCU firmware limitation, not an integration bug. The integration now:
- Detects this situation and provides helpful error messages
- Exposes `has_access_authorization` attribute for easy diagnosis
- Explains the issue and workarounds in logs

Users experiencing access control issues should:
1. Check the `has_access_authorization` state attribute
2. Follow error message instructions for access profile setup
3. Monitor for HCU firmware updates that may fix this limitation

#### References
- GitHub Issue #30 - PIN and access control configuration
- PR #75 - Complete door lock implementation
- Diagnostic data from real HmIP-DLD devices (firmware 1.4.12)

---

## Version 1.13.0 - 2025-11-08

### ✨ New Device Support

**HmIP-DRI32 Wired Input Actuator (Issue #31)**
- Added support for HmIP-DRI32 (32-channel digital radio input actuator)
- All 32 input channels now properly discovered
- Button press events fire via `hcu_integration_event`
- Contact state binary sensors created for all channels
- Device disabled by default (input-only device with many channels)

### 🔧 Technical Improvements

**Platform Override Infrastructure (Issue #38 - Partial)**
- Added `CONF_PLATFORM_OVERRIDES` configuration constant
- Lays groundwork for future light/switch toggle feature
- Full UI implementation deferred to future release

---

## Version 1.12.1 - 2025-11-08

### 🐛 Bug Fixes

**Duplicate Group Entity Names**
- Fixed issue where group entity names were displayed twice (e.g., "Wohnzimmer Wohnzimmer")
- Affected heating groups (HcuClimate), cover groups (HcuCoverGroup), and switching/light groups
- Root cause: Missing `_attr_has_entity_name = False` flag caused Home Assistant to combine device name with entity name
- Users will see correct single names after restarting Home Assistant

**Auto-Created Meta Groups**
- Integration now skips auto-created meta groups for SWITCHING and LIGHT types
- These groups are automatically created by HCU for rooms and were causing unexpected/redundant entities
- User-created functional groups (without `metaGroupId`) are still discovered and created
- Significantly reduces entity clutter from unwanted auto-generated groups

---

## Version 1.12.0 - 2025-11-08

### ✨ Enhancements

**SWITCHING and LIGHT Group Entity Support (Issue #44)**
- Added support for SWITCHING group entities that control multiple switches together
- Added support for LIGHT group entities that control multiple lights together
- Achieves feature parity with the official Homematic IP cloud integration for these group types
- Groups are automatically discovered from HCU configuration and appear as switch/light entities in Home Assistant
- Example: A "Living Room Lights" group can now control all living room lights with a single on/off toggle
- Groups use the `/hmip/group/switching/setState` API endpoint for synchronized control

### 🔧 Technical Improvements

**Clean Architecture for Group Entities**
- Created `HcuSwitchingGroupBase` base class to eliminate code duplication between switch and light groups
- Implemented `SwitchingGroupMixin` for shared state management logic (optimistic updates, error handling)
- Optimistic state updates provide instant UI feedback before API confirmation
- Robust error handling with automatic state rollback if API calls fail
- Dictionary-based discovery mapping in `discovery.py` for scalable group type handling
- Consistent type hints across all group entity classes (`dict[str, Any]`)
- Removed unused group entity mappings from `class_module_map` for clearer discovery flow

**Code Quality**
- Reduced code duplication by ~50 lines through base class consolidation
- Direct attribute access instead of `getattr()` for improved code clarity
- Consistent entity naming pattern across all group types

---

## Version 1.11.0 - 2025-11-07

### 🐛 Bug Fixes

**HCU Device Registration in Multi-Access-Point Setups (Issue #42)**
- Fixed critical issue where the actual HCU device was missing from device registry in setups with multiple access points (HCU + HAP + DRAP)
- Home-level entities (vacation mode, alarm) are now correctly assigned to the HCU device instead of auxiliary access points
- Updated logic to prioritize actual HCU models (HmIP-HCU-1, HmIP-HCU1-A) when determining the primary device
- HAP and DRAP are now properly recognized as auxiliary access points connected to the main HCU
- Devices that were incorrectly associated with HAP now correctly show as children of the HCU

**Heating Group Auto Mode Preservation (Issue #35)**
- Fixed behavior where manually adjusting temperature switched from AUTO to MANUAL mode permanently
- Temperature adjustments in AUTO mode now create temporary overrides that automatically revert at the next scheduled temperature change
- Matches the original Homematic IP app behavior - users can adjust temperature without disrupting heating schedules
- System automatically resumes scheduled operation at the next programmed time
- Manual temperature adjustments in AUTO mode no longer force the system into MANUAL mode unless explicitly set to HEAT

**Alarm Siren Device Classification (Issue #50)**
- HmIP-ASIR2 alarm siren now properly classified as siren entity instead of switch
- Users can now use `siren.turn_on` and `siren.turn_off` services
- Added new siren platform with proper entity features
- Created `HcuSiren` class for alarm siren devices

### ✨ Enhancements

**Door Opener Button for HmIP-FDC (Issue #41)**
- Added button entity to trigger door opener on HmIP-FDC (Full Flush Door Controller)
- Creates "Open Door" button that sends 1-second pulse to open door
- Provides the primary functionality that was missing from this device
- Matches functionality available in the Homematic IP app

**HmIP-RC8 Button Events (Issue #33)**
- Confirmed HmIP-RC8 button events are working correctly (supported since v1.8.1)
- `SINGLE_KEY_CHANNEL` is included in event handling
- Added documentation for proper automation configuration (channel numbers should not be quoted)

### 🔧 Technical Improvements

- Added Platform.SIREN to platforms list
- Updated HCU_MODEL_TYPES to correctly identify actual HCU devices (removed HmIP-HAP as it's an auxiliary access point)
- Enhanced device identification logic with proper fallback hierarchy
- Refactored turn_on/turn_off methods to eliminate code duplication (DRY principle)
- Added deterministic sorting for consistent primary HCU selection across restarts

---

## Version 1.10.0 - 2025-11-07

### 🐛 Bug Fixes

**Window Sensor State Attribute (Issue #48)**
- HmIP-SRH window sensors now expose the actual window state ("OPEN", "TILTED", or "CLOSED") as a state attribute
- Users can now distinguish between tilted and fully open windows in automations
- Binary sensor still shows on/off (on for both OPEN and TILTED), but the `window_state` attribute provides the precise state

**Improved Lock PIN Error Messages (Issue #30)**
- Door lock PIN configuration errors now include detailed step-by-step instructions
- Error messages point directly to the configuration location in Home Assistant
- Includes link to README documentation for additional help

**Entity Prefix Applied to All Entities (PR #61 Critical Fixes)**
- Fixed critical bug where entity prefix was not applied to main entities on unlabeled channels
- Affected devices like HmIP-FROLL, HmIP-PSM-2, HmIP-BSM now correctly show prefix
- Added fallback logic to ensure prefix is applied even when labels are missing:
  - Device entities: Falls back to device label → model type → device ID
  - Climate groups: Falls back to group label → group ID
  - Cover groups: Falls back to group label → group ID
- Example: With prefix "House1", device "HmIP-PSM-2" becomes "House1 HmIP-PSM-2"
- Ensures prefix is applied to ALL entities without exception

### ✨ Enhancements

**Entity Name Prefix for Multi-Home Setups (Issue #43)**
- Added optional entity name prefix during integration setup
- Perfect for users with multiple HCU instances (e.g., multiple houses)
- Prefix is applied to all entity names (e.g., "House1 Living Room")
- Helps avoid naming conflicts and improves organization
- Configured in Settings → Devices & Services → Add Integration → Enter optional prefix

### 🔧 Code Quality Improvements

**Refactored Entity Prefix Logic (PR #61 Feedback)**
- Created `HcuEntityPrefixMixin` to eliminate code duplication across base entity classes
- Added `_apply_prefix()` helper method to centralize prefix application logic
- Consolidated prefix application in `_set_entity_name` method (DRY principle)
- Updated all entity classes to use the helper method (alarm_control_panel, binary_sensor, climate, cover, sensor)
- Removed redundant None check in `_set_entity_name` method
- Moved documentation URL to constant (`DOCS_URL_LOCK_PIN_CONFIG`) for better maintainability
- Improved code clarity and eliminated repetitive prefix logic across 6 files

### 📝 Documentation

**Issue #20 Closure**
- Confirmed that HmIP-WGS and HmIP-WRC6 button event issues were fixed in v1.8.1
- Created comprehensive closure documentation with testing instructions

**Issue #55 Investigation**
- Created diagnostics request for HmIP-BSM energy counter issue
- Requires user diagnostics file to determine root cause

---

## Version 1.9.0 - 2025-11-07

### 🐛 Bug Fixes

**Fixed Entity Naming for Unlabeled Channels (Issue #27)**
- Entities without channel labels now display with proper names instead of showing unique IDs
- Affected devices like HmIP-FROLL, HmIP-PSM-2, HmIP-BSM, and others now show friendly names (e.g., "HmIP-PSM-2" instead of "domain_id_1_on")
- Fixed by correctly setting `has_entity_name=True` when entity name is `None`

### ✨ Enhancements

**Comprehensive API Response Validation**
- Added robust validation for all API responses and WebSocket messages
- System now gracefully handles malformed data, missing fields, and unexpected types
- Enhanced error logging provides specific details for troubleshooting
- Improved stability when HCU returns unexpected data structures

**Enhanced Code Documentation**
- Improved docstrings throughout the codebase with detailed parameter and return descriptions
- Better inline comments explaining complex logic (button detection, state management)
- Added validation pattern documentation for developers

### 📚 New Developer Documentation

**CONTRIBUTING.md**
- Comprehensive developer guide (650+ lines)
- Detailed code structure explanation for all modules
- Testing guidelines and coverage goals (80% minimum, 90% target)
- Pull request process and coding standards
- Step-by-step guides for common tasks (adding devices, services)
- API response validation patterns and best practices
- Debugging tips and troubleshooting workflow

### 🧪 Testing

**Phase 3: Comprehensive Test Suite**
- Added 32+ unit tests covering core infrastructure
- 90%+ test coverage for api.py, coordinator, and entity modules
- Tests for all critical paths including edge cases
- Validates button detection, state management, and event processing

### 🔧 Technical Improvements

**API Client Enhancements**
- `get_system_state()`: Validates response structure and ensures critical keys exist
- `process_events()`: Type validation and required field checking
- `_handle_incoming_message()`: Message structure validation with specific error logging
- `_handle_device_channel_events()`: Validates complete event data before processing

---

## Version 1.8.1 - 2025-10-26

### 🐛 Critical Bug Fix

**Fixed Button Events for Stateless Devices (HmIP-WGS, HmIP-WRC6, and similar)**

This release fixes a critical bug that prevented button press events from firing for certain wall-mounted switches and remote controls, specifically:
- **HmIP-WGS** (Wall-mounted Glass Switch)
- **HmIP-WRC6** (6-button Wall Remote)
- Other devices with button channels that don't report channel-level timestamps

**What was broken:**
- Button presses on these devices were received via WebSocket but never triggered `hcu_integration_event` events
- Users couldn't create automations for these buttons
- Events monitor showed no activity when buttons were pressed

**What's fixed:**
- Implemented dual-path button detection that works with both timestamp-based and stateless button channels
- Events now fire correctly for all button devices regardless of their timestamp behavior
- Added debug logging to help diagnose button press detection

**Technical Details:**
The fix enhances the `_handle_event_message` method in the coordinator to:
1. Track which specific channels are present in WebSocket events (not just which devices)
2. Detect button presses via timestamp changes (existing behavior - preserved)
3. Detect button presses via event presence for channels without timestamps (new fallback)
4. Prevent false positives by only firing events for channels actually in the WebSocket message

This change is **backward compatible** and won't affect existing button devices that already work correctly.

**User Action Required:**
If you have HmIP-WGS or HmIP-WRC6 devices (or similar button devices that weren't working), please:
1. Update to version 1.8.1
2. Restart Home Assistant
3. Test your buttons using Developer Tools → Events (listen to `hcu_integration_event`)
4. Refer to the updated README for automation examples

---

## Version 1.8.0 - 2025-10-24

**<-- This feature is still in beta and still has some issues**

### 🐛 Bug Fixes
* **Fixed Unresponsive Switches:** Resolved a critical bug that caused certain switch models (e.g., `HmIP-BSM`, `HmIP-DRSI1`) to become unresponsive to commands from Home Assistant. The integration now correctly sends the `onLevel` parameter to the API for all switch operations.
* **HmIP-FSI16 Full Channel Support:** Fixed an issue where only the first 8 channels of the `HmIP-FSI16` (16-channel flush-mount switch actuator) were created. All 16 switch entities are now correctly discovered and functional.
* **HmIP-ESI Energy Meter Support:** Added comprehensive support for all features of the `HmIP-ESI` (Energy Meter and Sensor Interface). New sensors are now created for:
  * Energy Counter T1 (Low Tariff)
  * Energy Counter T2 (High Tariff)
  * Power Production (Current Grid Feed-in)
  * Energy Production (Total Grid Feed-in)
* **HmIP-SLO Light Sensor:** The `illumination` sensor for the `HmIP-SLO` (Light Sensor Outdoor) is now correctly discovered and created.
* **Alarm Control Panel Syntax Error:** Fixed a syntax error in `alarm_control_panel.py` that could prevent the alarm panel from arming correctly.
* **Duplicate Siren Entities:** Removed a redundant mapping for `acousticAlarmActive` that was causing duplicate siren switch entities to be created for some devices.

### ✨ Improvements
* **Modernized Stateless Button Handling:** Refactored how stateless buttons (e.g., wall switches like `HmIP-BRC2`, remote controls like `HmIP-KRC4`) are handled. These devices no longer create button entities and instead fire `hcu_integration_event` on the Home Assistant event bus. This aligns with Home Assistant's standard approach for stateless device triggers and provides better flexibility in automations. See the README for automation examples.
* **Instant UI Updates for Absence Modes:** Implemented proactive state synchronization for Vacation and Eco modes. When you activate an absence mode from Home Assistant, related entities (such as `binary_sensor.vacation_mode`) now update instantly, matching the behavior of the official Homematic IP app for a more responsive user experience.
* **Enhanced Device Compatibility:** Added numerous new device types and channel type definitions to improve device mapping accuracy and ensure better support for future Homematic IP devices.

---

## Version 1.6.1 - 2025-10-20

### 🚀 New Device Support
* Added support for `HmIP-FSI16` (`FULL_FLUSH_SWITCH_16`), enabling all 16 switch channels.
* Added support for the `HmIP-WGS` (Wall-mounted Glass Switch), creating switch entities for its channels.
* Added support for `HmIP-BS2` (`BRAND_SWITCH_2`), ensuring it is correctly identified as a switch.
* The backlight of the `HmIP-WGS` is now properly discovered and created as a light entity, allowing for brightness control.

### 🐛 Bug Fixes
* **Fixed Unresponsive Switches:** Corrected a bug that caused certain switch models, particularly the `HmIP-BSM`, to become unresponsive to commands from Home Assistant. The API payload now includes the `onLevel` parameter for broader compatibility.

### ✨ Improvements
* **Optimistic State for Switches:** All switch entities now use optimistic state updates. This provides instant feedback in the Home Assistant UI when a switch is toggled, improving the user experience.
* **Robust Switch Error Handling:** Added `try...except` blocks to switch turn-on/off actions. If a command fails, an error is logged, and the entity's state reverts, preventing it from getting stuck in an incorrect state.

---

## Version 1.5.0 - 2025-10-15

### ✨ Improvements
- **Robust Service Handling:** Service calls (like play_sound and activate_party_mode) have been refactored to call entity methods directly instead of parsing entity IDs. This makes the implementation more robust and less prone to breaking with future changes.
- **Idiomatic Button Events:** Stateless physical buttons (like wall switches) no longer create a confusing button entity in the UI. Instead, they now fire a hcu_integration_event on the Home Assistant event bus, which is the standard and more flexible way to handle stateless device triggers in automations.
- **Smarter Climate Entity:** The climate card will now correctly display temperature and humidity readings from radiator thermostats (HmIP-eTRV) if a dedicated wall thermostat is not present in the room.
- **Smoother Climate Control:** The logic for changing HVAC modes has been completely overhauled to provide an instant, optimistic UI update. This eliminates the "jumpy" or delayed feeling when switching between Auto, Heat, and Off.
- **Dynamic Climate Presets:** The climate entity now dynamically discovers and displays heating profiles from the HCU as presets, allowing users to switch between their custom heating schedules directly from Home Assistant.
- **Improved Entity Availability:** The core logic for determining if an entity is available has been hardened. Entities will now more reliably report as unavailable if the connection to the HCU is lost or if the device data is temporarily missing from the API payload, fixing issues for devices like the HmIP-SWO-PR Weather Sensor and various switch models.
- **Enhanced Lock State:** The lock entity now reports jammed, locking, and unlocking states for better real-time feedback.
