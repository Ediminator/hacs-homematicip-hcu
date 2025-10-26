# Changelog

All notable changes to the Homematic IP Local (HCU) integration will be documented in this file.

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
