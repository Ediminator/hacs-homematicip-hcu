# Homematic IP Local (HCU) Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

This is a custom integration for Home Assistant that connects directly to your **Homematic IP Home Control Unit (HCU)** over your local network. It allows you to control and monitor your Homematic IP devices without relying on the cloud.

## Features

* **Local Control:** All communication happens on your local network for speed and privacy.
* **Real-Time Updates:** Uses a WebSocket connection to receive instant state changes from your devices.
* **User-Friendly Setup:** A simple, step-by-step configuration flow guides you through the setup process.
* **Broad Device Support:** Includes support for a wide range of devices.

## Prerequisites

Before you can install the integration, you must activate **Developer Mode** on your Home Control Unit.

1.  Open the HCUweb interface in your browser (e.g., `https://hcu1-XXXX.local`).
2.  Navigate to the "Developer Mode" page.
3.  Press the button to **activate developer mode**.
4.  Activate the switch to **expose the Connect API WebSocket**.

## Installation

The recommended way to install this integration is through the [Home Assistant Community Store (HACS)](https://hacs.xyz/).

### HACS Installation (Recommended)

1.  Go to HACS in your Home Assistant sidebar.
2.  Click on **Integrations**, then click the three-dots menu in the top right and select **Custom repositories**.
3.  Add the URL to this GitHub repository and select the `Integration` category.
4.  The integration will now appear in the HACS list. Click **Install**.
5.  Restart Home Assistant.

### Manual Installation

1.  Download the latest release from the [Releases](https://github.com/Ediminator/hacs-homematicip-hcu/releases) page of this repository.
2.  Unzip the file and copy the `hcu_integration` folder into the `custom_components` directory of your Home Assistant configuration.
3.  Restart Home Assistant.

## Configuration

Once installed, you can add the integration to Home Assistant.

1.  Go to **Settings** > **Devices & Services**.
2.  Click **Add Integration** and search for **"Homematic IP Home Control Unit"**.
3.  Enter the **IP Address** of your HCU.
4.  The next screen will ask for an **Activation Key**. Follow the on-screen instructions to generate a new, temporary key from your HCU's developer mode page and paste it in.
5.  The integration will automatically perform the security handshake and set itself up. Your devices will be discovered and added to Home Assistant.

## Supported Devices

This integration provides entities across the following platforms:

* **Climate:** For thermostats and heating groups, including temperature/humidity readings and boost mode.
* **Cover:** For shutters and blinds, including tilt control.
* **Light:** For dimmers and light switches.
* **Lock:** For door locks.
* **Switch:** For pluggable outlets and other switches.
* **Sensor:** Automatically creates sensors for battery levels, signal strength, valve positions, and more.
* **Binary Sensor:** For door/window contacts, motion detectors, and other binary state devices.

> **Note:** The `Lock` entity requires an authorization PIN. This feature is not yet implemented in the configuration flow, so lock control is currently disabled.
