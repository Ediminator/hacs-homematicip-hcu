# Homematic IP Local (HCU) Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

This is a custom integration for Home Assistant that connects directly to your **Homematic IP Home Control Unit (HCU)** over your local network. It allows you to control and monitor your Homematic IP devices without relying on the cloud.

## Features

* **Local Control:** All communication happens on your local network for speed and privacy.
* **Real-Time Updates:** Uses a persistent WebSocket connection for instant "local push" state changes.
* **Broad Device Support:** Includes support for a wide range of devices, including multi-function devices (`HmIP-MP3P`), stateless buttons (`SWITCH_INPUT`), and watering controllers.
* **Secure Lock Control:** A secure, UI-based options flow allows you to configure the PIN for your door lock.
* **User-Friendly Setup:** A simple, step-by-step configuration flow with instructional images guides you through the setup process.

## Installation

### Prerequisites

1.  A running Home Assistant instance.
2.  [HACS](https://hacs.xyz/) (Home Assistant Community Store) installed.
3.  A Homematic IP Home Control Unit (HCU) connected to your local network.

### 1. Installation via HACS (Required First Step)

You must install the integration via HACS before you can configure it in Home Assistant.

1.  In HACS, go to **Integrations** and click the three dots in the top right corner.
2.  Select **Custom repositories**.
3.  In the "Repository" field, paste this URL: `https://github.com/Ediminator/hacs-homematicip-hcu/`
4.  For "Category", select **Integration**.
5.  Click **ADD**, then close the custom repositories window.
6.  You should now see the "Homematic IP Local (HCU)" integration. Click **INSTALL** and proceed with the installation.
7.  **Restart Home Assistant** when prompted.

## Configuration

### 2. Prepare Your HCU

After installing via HACS and restarting, you must enable the local API on your HCU before adding the integration in Home Assistant.

1.  Access your HCU's web interface, known as **HCUweb**. According to the official documentation, you can reach it in your local network at `https://hcu1-XXXX.local`, where `XXXX` are the last four digits of the SGTIN found on the underside of your device.
2.  Navigate to the **Developer Mode** page.
3.  Activate the **Developer Mode** switch.
4.  Activate the switch to **Expose the Connect API WebSocket**.

### 3. Add the Integration in Home Assistant

1.  In Home Assistant, go to **Settings > Devices & Services**.
2.  Click **ADD INTEGRATION** and search for `Homematic IP Local (HCU)`.
3.  In the first dialog, enter the **IP address** of your HCU. While you can access the web interface via the hostname, the integration still requires the direct IP address to connect.
4.  The next dialog will ask for an **Activation Key**.
    * Go back to your HCU's web interface.
    * Click the **Generate activation key** button. This key is temporary.
    * Copy the generated key and paste it into the Home Assistant dialog.
5.  The integration will complete the setup and automatically discover your devices.

### 4. Configure Your Door Lock (Optional)

If you have a Homematic IP door lock, you must provide its PIN for the integration to be able to control it.

1.  After the integration is added, find its card in **Settings > Devices & Services**.
2.  Click the **CONFIGURE** button on the card.
3.  Enter your door lock's **Authorization PIN** and click **SUBMIT**.

## Enabling Debug Logging

If you need to report an issue, you can enable debug logging to get more detailed information.

### Method 1: Via the User Interface (Recommended)

This is the easiest and quickest way to get logs for a specific issue.

#### Enabling the Log

1.  Navigate to **Settings > Devices & Services**.
2.  Find the "Homematic IP Local (HCU)" integration in your list.
3.  Click the three-dot menu on the integration card.
4.  Click **Enable debug logging**.

#### Downloading the Log File

After enabling logging, you need to reproduce the issue and then download the generated log file.

1.  Perform the action in Home Assistant that is causing the issue (e.g., turn on a switch, change the temperature).
2.  Once you have reproduced the problem, go back to the three-dot menu on the integration card.
3.  Click **Disable debug logging**.
4.  Your browser will immediately prompt you to save the log file. Save it to your computer so you can attach it to your issue report.

### Method 2: Via `configuration.yaml` (Permanent)

To make debug logging permanent so it remains active after a restart, add the following to your `configuration.yaml` file:

```yaml
logger:
  default: info
  logs:
    custom_components.hcu_integration: debug
```