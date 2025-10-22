# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Version 1.7.0 - 2025-10-23

### 🎉 New Features
* **New Vacation Mode UI:** A "Set Vacation Mode" configuration option has been added to the integration's settings menu (in Settings → Devices & Services → Configure). This provides a user-friendly form to set the target temperature and end date/time, removing the need to manually call a service for vacation mode activation. **<-- This feature is still in beta and still has some issues**

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

## Version 1.5.0 - 2025-10-15

### ✨ Improvements
- **Robust Service Handling:** Service calls (like play_sound and activate_party_mode) have been refactored to call entity methods directly instead of parsing entity IDs. This makes the implementation more robust and less prone to breaking with future changes.
- **Idiomatic Button Events:** Stateless physical buttons (like wall switches) no longer create a confusing button entity in the UI. Instead, they now fire a hcu_integration_event on the Home Assistant event bus, which is the standard and more flexible way to handle stateless device triggers in automations.
- **Smarter Climate Entity:** The climate card will now correctly display temperature and humidity readings from radiator thermostats (HmIP-eTRV) if a dedicated wall thermostat is not present in the room.
- **Smoother Climate Control:** The logic for changing HVAC modes has been completely overhauled to provide an instant, optimistic UI update. This eliminates the "jumpy" or delayed feeling when switching between Auto, Heat, and Off.
- **Dynamic Climate Presets:** The climate entity now dynamically discovers and displays heating profiles from the HCU as presets, allowing users to switch between their custom heating schedules directly from Home Assistant.
- **Improved Entity Availability:** The core logic for determining if an entity is available has been hardened. Entities will now more reliably report as unavailable if the connection to the HCU is lost or if the device data is temporarily missing from the API payload, fixing issues for devices like the HmIP-SWO-PR Weather Sensor and various switch models.
- **Enhanced Lock State:** The lock entity now reports jammed, locking, and unlocking states for better real-time feedback.

### 🐛 Bug Fixes
- **Startup Error:** Fixed a NameError that prevented the integration from starting due to a missing import in the discovery module.

## Version 1.4.0 - Complete Code refactoring for better compatibility

### 🚀 New Features
- **Switch for Vacation Mode:** The "Vacation Mode" binary sensor has been replaced with a fully functional switch entity. You can now toggle the HCU's vacation mode directly from Home Assistant.

- **Button Entities for Remotes:** Stateless devices like wall switches and remote controls are now represented as proper button entities instead of the previous binary sensor workaround. This provides a more natural user experience and aligns with Home Assistant standards. A new button.py platform has been added.

- **New Service to Control HCU Automations:** A new service, hcu_integration.set_rule_state, has been added. This allows you to enable or disable any simple automation rule on your HCU directly from Home Assistant automations or scripts.

- **Device Action for Energy Sensors:** Energy metering devices now have a "Reset Energy Counter" device action. This allows you to reset the meter directly from the device page or within your automations.

- **Configurable HCU Ports:** Users can now specify custom ports for the HCU's Authentication API and WebSocket during initial setup and through the "Reconfigure" flow. This provides flexibility for advanced network setups.

## ✨ Improvements
- **🔒 Secure PIN Handling for Door Locks:** The storage and management of the door lock PIN has been completely overhauled. The PIN is now stored securely in the encrypted Home Assistant data store. Changing the PIN is now handled via the secure "Re-authenticate" flow, following Home Assistant's best practices for sensitive credentials.

- **🧹 Cleaner Climate Card UI:** Fixed a UI bug where the room name was being duplicated in all-caps at the top of climate entity cards. The cards are now clean and display the name correctly once.

- **🔧 Enhanced Reconfiguration Flow:** The reconfiguration process for changing the HCU's IP address or ports is now more robust and provides clearer error messages for connection failures.

- **Fully implemented SSL protection:** Accepting the self-signed SSL certificate from the HCU improving security and connectivity for some clients

- **🛡️ Proactive Lock Unavailability:** The lock entity will now report itself as "Unavailable" if the authorization PIN has not been set, providing immediate feedback to the user that configuration is required.

## 🐛 Bug Fixes
- **Fixed play_sound Service:** Corrected a critical bug that caused the play_sound service to fail due to a missing method and incorrect parameter passing in the API client.

- **Fixed Climate Control Failure:** Resolved an AttributeError caused by a method name typo (async_set_group_setpoint_temperature) that prevented users from setting the temperature on climate entities.

## Version 1.3.0 - Major Compatibility Update & Bug Fixes

This release significantly expands device support and fixes several key bugs related to optimistic state handling and entity mapping.

### 🎉 New Device Support
The integration now supports a much wider range of devices thanks to new mappings for their unique features and channel types.

- **Covers:**
  - Garage Door modules (e.g., `HmIP-MOD-HO`) are now supported as `cover` entities.

- **Lights:**
  - Full RGB color control (`HS` color mode) is now supported for lights like the `HmIP-RGBW`.

- **Sensors:**
  - Tilt/Vibration Sensor (`HmIP-STV`)
  - Mains Failure Sensor (`HmIP-PMFS`)
  - Multi-probe Temperature Sensors (e.g., `HmIP-STE2-PCB`) now create entities for all temperature readings (sensor 1, sensor 2, and delta).
  - Soil Sensors (e.g., `HmIP-SMI`) now expose entities for moisture and temperature.

- **Switches:**
  - Added specific device classes for DIN rail and wired switches (`HmIP-DRSI1`, `HmIPW-DRS8`, `HmIPW-DRS4`).

- **Event-Based Devices:**
  - Added support for `MULTI_MODE_INPUT_CHANNEL` to generate events for devices like the `HmIP-FCI6`.

### ✨ Improvements
- Added support for the wired DIN rail access point (`HmIPW-DRAP`) as a recognized hub device.
- The `play_sound` service is now available for compatible devices like sirens and doorbells.

### 🐛 Bug Fixes
- **Climate:** Fixed a critical bug where changing the temperature while in "Auto" mode would not switch the thermostat to "Heat" (manual) mode.
- **Alarm Panel:** Fixed a UI flickering issue that occurred during the arming sequence by correctly implementing the "Arming" state.
- **Alarm Panel:** Resolved a Home Assistant Core deprecation warning by renaming the internal `state` property to `alarm_state`.
- **Smart Plugs:** Corrected a feature key (`currentPowerConsumption`) to ensure power and energy sensors are created for smart plugs with metering (e.g., `HmIP-PSM`).
- **Code Quality:** Removed unused imports flagged by the linter.

## 1.2.0 - 2025-09-30

### ✨ Features

* **New `play_sound` Service:** The limited `button` entity has been replaced with a powerful `hcu_integration.play_sound` service. This allows you to play any sound file on compatible devices (like sirens or doorbells) and specify the volume and duration directly in your automations and scripts.
* **New Vacation Mode Sensor:** A binary sensor is now automatically created for the HCU, which turns `on` when vacation mode is active. This makes it easy to use the system-wide vacation state in your automations.
* **New Diagnostic Valve State Sensor:** For heating thermostats, a new "Valve State" sensor is now available (disabled by default). This can be enabled to help diagnose valve adaptation and operational states.

### 🔧 Improvements & Fixes

* **Alarm Control Panel Refactor:** The `alarm_control_panel` entity has been updated to use the modern `alarm_state` property, resolving deprecation warnings from Home Assistant Core and ensuring future compatibility. Optimistic state handling is now more robust.
* **Code Maintainability:** All API request paths have been centralized into a single `API_PATHS` class in `const.py`. This reduces code duplication and makes future API updates much easier.
* **Improved WebSocket Error Handling:** The WebSocket listener in `__init__.py` now catches more specific network exceptions, providing better log clarity while maintaining its robust reconnection logic.
* **General Code Cleanup:** Addressed several minor linter warnings and removed unused code for a cleaner, more efficient codebase.

## [1.1.0] - 2025-09-23

### 🚀 Features

* **Added Standalone Temperature Sensor for Radiator Thermostats**: The integration now correctly creates a dedicated temperature sensor for radiator thermostats (like `HmIP-eTRV-E`) by reading the `valveActualTemperature` property. This resolves the issue where rooms without a separate wall-mounted thermostat would not show a temperature reading.
* **Added New Sensor Entities**: Based on a deeper analysis of the API data, the following new sensors are now created where available:
    * **Absolute Humidity** (`vaporAmount`): For thermostats that report this value.
    * **Controls Locked** (`operationLockActive`): Binary sensor for thermostats.
    * **Frost Protection** (`frostProtectionActive`): Binary sensor for floor heating systems.
    * **Dew Point Alarm** (`dewPointAlarmActive`): Binary sensor for floor heating systems.

### 🐛 Bug Fixes

* **Corrected Inverted 'Controls Locked' State**: The "Controls Locked" binary sensor now correctly shows its state. The logic was inverted to match Home Assistant's standards for the `LOCK` device class.
* **Fixed Extraneous Battery Entities**: The integration no longer creates "Battery" or "Battery Level" entities for mains-powered devices that reported a `null` battery state.

### ⬆️ Improvements

* **Improved 'Unreachable' Sensor**: The binary sensor for device reachability (`unreach`) now uses the `PROBLEM` device class, resulting in more intuitive states of "OK" and "Problem" in the Home Assistant UI.
* **Rounded Humidity Value**: The "Absolute Humidity" sensor value is now rounded to two decimal places for a cleaner presentation.
* **More Robust Entity Discovery**: The logic for discovering most entities (sensors, binary sensors, covers, lights, and locks) has been updated to rely on the presence of specific API features (e.g., `shutterLevel`, `dimLevel`) instead of undocumented `functionalChannelType` names. This makes the integration more resilient to future HCU firmware updates.

## [1.0.0] - 2025-09-21

This is the initial stable release of the Homematic IP Local (HCU) integration, featuring a complete architectural overhaul and a wide range of supported devices.

### Added

* **Initial Support:** Full integration with the Homematic IP Local WebSocket API for real-time updates.
* **Broad Device Support:** Added platforms for:
    * `binary_sensor` (Window Contacts, Motion Detectors, Smoke Alarms, Buttons)
    * `climate` (Heating Groups)
    * `cover` (Shutters and Blinds)
    * `light` (Dimmers and Tunable White Lights)
    * `lock` (Door Locks)
    * `sensor` (Temperature, Humidity, Power, etc.)
    * `switch` (Switching actuators, Sirens, Watering Controllers)
* **Complex Device Handling:** Support for multi-function devices (e.g., `HmIP-MP3P`) and stateless buttons (`SWITCH_INPUT`).
* **UI Configuration:** A fully UI-based configuration flow for easy setup.
* **Options Flow:** A secure, UI-based options flow for configuring the door lock authorization PIN post-setup.
* **Resilient Connection:** Automatic and robust reconnection handling for the WebSocket connection.
* **Professional Look & Feel:**
    * Added a custom logo for the integration.
    * Created a `strings.json` file for a rich setup experience with images and localization support.
    * Comprehensive `README.md` and this `CHANGELOG.md`.

### Changed

* **Major Architectural Refactor:** The integration was completely rewritten from a polling-based model to a pure "local push" architecture for instant state updates and lower system overhead.
* **Improved Entity Discovery:** The discovery logic was significantly improved to be based on a device's `functionalChannelType` for much higher accuracy and reliability.
* **Full Code Cleanup:** The entire codebase has been cleaned, documented with professional docstrings, and all obsolete code has been removed.

### Fixed

* Resolved a critical `RuntimeError` (concurrent call) that occurred when sending commands while the event listener was active.
* Fixed a `TimeoutError` during integration startup caused by a race condition in the initial state fetch.
* Corrected multiple `AttributeError` issues in entity platforms by ensuring all helper methods and class initializations were correct.
* Fixed an `INVALID_NUMBER_PARAMETER_VALUE` error when turning off climate entities by respecting the device's advertised minimum temperature.
* Improved the state-tracking logic for `climate` entities to provide a more intuitive and less "jumpy" user experience in the dashboard.
* Fixed the discovery logic for `binary_sensor` entities to correctly identify and create motion detectors.

[Unreleased]: https://github.com/Ediminator/hacs-homematicip-hcu/compare/v1.0.0...HEAD

[1.0.0]: https://github.com/Ediminator/hacs-homematicip-hcu/releases/tag/v1.0.0
