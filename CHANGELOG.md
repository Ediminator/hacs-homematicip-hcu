# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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