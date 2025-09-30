# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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



