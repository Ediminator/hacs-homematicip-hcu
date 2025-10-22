# Homematic IP Local (HCU) Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)

Control your **Homematic IP** devices locally through your **Home Control Unit (HCU)** without relying on the cloud. This custom integration for Home Assistant connects directly to your HCU over your local network for maximum speed, reliability, and privacy.

## ✨ Features

* **🏠 Local Control:** All communication happens on your local network - no cloud dependency
* **⚡ Real-Time Updates:** Instant state changes via persistent WebSocket connection
* **🎯 Easy Setup:** Simple step-by-step configuration flow guides you through setup
* **🔧 Broad Device Support:** Works with most Homematic IP devices based on their capabilities
* **🎵 Custom Services:** Flexible services for sound playback, rule control, and party mode
* **🔒 Secure:** Your data never leaves your network

## 📋 Supported Devices

This integration uses a **feature-based discovery system** rather than a fixed device list. This means that most Homematic IP devices will work automatically based on their capabilities:

- **Switches & Dimmers:** Pluggable, flush-mounted, and DIN rail variants
- **Covers:** Shutters, blinds, garage doors (including third-party modules like HunterDouglas)
- **Climate Control:** Heating groups, wall thermostats, radiator thermostats
- **Security Sensors:** Window/door contacts, motion detectors, smoke detectors, water sensors
- **Lights:** Dimmers, RGBW controllers, notification lights
- **Locks:** Door lock drives with PIN support
- **Special Devices:** Watering controllers, notification devices, e-paper displays

**How it works:** 
- Devices with `dimLevel` → appear as lights
- Devices with `shutterLevel` → appear as covers
- Devices with `windowState` or `presenceDetected` → appear as binary sensors
- And so on...

## 🚀 Installation

### Prerequisites

Before you begin, make sure you have:

1. ✅ A running Home Assistant instance
2. ✅ [HACS](https://hacs.xyz/) (Home Assistant Community Store) installed
3. ✅ A Homematic IP Home Control Unit (HCU) connected to your local network
4. ✅ The HCU's IP address (you can find this in your router's device list)

---

### Step 1: Install via HACS

> ⚠️ **Important:** You must install the integration through HACS first before you can configure it in Home Assistant.

1. Open HACS in your Home Assistant sidebar
2. Click on **Integrations**
3. Click the **three dots** (⋮) in the top right corner
4. Select **Custom repositories**
5. Add the following details:
   - **Repository:** `https://github.com/Ediminator/hacs-homematicip-hcu/`
   - **Category:** `Integration`
6. Click **ADD**
7. Close the custom repositories window
8. Search for **"Homematic IP Local (HCU)"** in HACS
9. Click **DOWNLOAD** and confirm
10. **Restart Home Assistant** when prompted

---

### Step 2: Enable the HCU Local API

Before adding the integration, you must enable the local API on your HCU.

1. Open your HCU's web interface (HCUweb) in a browser:
   - Try `https://hcu1-XXXX.local` (replace `XXXX` with the last 4 digits of your HCU's SGTIN)
   - Or use your HCU's IP address: `https://YOUR_HCU_IP`
   - **Note:** You may see a security warning about the certificate - this is normal, click "Advanced" and proceed

2. Log in to your HCU

3. Navigate to **Developer Mode** in the menu

4. Toggle the switch to **activate Developer Mode**

5. Toggle the switch to **Expose the Connect API WebSocket** - ⚠️ Sometimes the toggle for the Websocket is already activated, even when this is the first time the developer mode was activated. Please **deactivate and activate the toggle** in that case.

6. Leave this page open - you'll need it in the next step!

---

### Step 3: Add the Integration in Home Assistant

1. In Home Assistant, go to **Settings** → **Devices & Services**

2. Click the **+ ADD INTEGRATION** button (bottom right)

3. Search for `Homematic IP Local (HCU)` and select it

4. **First Dialog - Connection Details:**
   - Enter your **HCU's IP address** (e.g., `192.168.1.100`)
   - Leave the ports at their default values unless you changed them:
     - Authentication Port: `6969`
     - WebSocket Port: `9001`
   - Click **SUBMIT**

5. **Second Dialog - Authorization:**
   - Switch back to your HCU's web interface (from Step 2)
   - Click the **"Generate activation key"** button
   - A temporary key will appear (valid for a few minutes)
   - **Copy the entire key** and paste it into Home Assistant
   - Click **SUBMIT**

6. The integration will now connect and discover all your devices! This may take a few moments.

7. You should see a success message and your devices will start appearing in Home Assistant

---

### Step 4: Configure Door Lock PIN (Optional)

If you have a Homematic IP door lock (e.g., HmIP-DLD), you need to provide its PIN for the integration to control it.

> 💡 **Why?** The HCU requires a PIN for all lock operations for security reasons.

1. Go to **Settings** → **Devices & Services**
2. Find the **Homematic IP Local (HCU)** card
3. Click **CONFIGURE**
4. Enter your door lock's **Authorization PIN**
5. Click **SUBMIT**

Your door lock will now be available for control in Home Assistant!

---

## 🔧 Configuration Options

After installation, you can adjust some settings:

1. Go to **Settings** → **Devices & Services**
2. Find the **Homematic IP Local (HCU)** card
3. Click **CONFIGURE**

### Available Options:

- **Comfort Temperature:** Default temperature (in °C) used when switching from OFF to HEAT mode
- **Third-Party Device Filters:** Show/hide devices from manufacturers other than eQ-3

---

## 📊 Diagnostics & Troubleshooting

### Downloading Diagnostics

Diagnostics files are **extremely valuable** for improving the integration, adding support for new devices, and troubleshooting issues. Here's how to download them:

> 🎯 **When to download diagnostics:**
> - Before reporting an issue on GitHub
> - When you have a device that isn't working correctly
> - When you want to help add support for a new device type
> - For general troubleshooting

#### How to Download:

1. Go to **Settings** → **Devices & Services**
2. Find the **Homematic IP Local (HCU)** integration card
3. Click on the card to open the integration details
4. In the top right, click the **three dots** (⋮)
5. Select **Download diagnostics**
6. Your browser will download a JSON file with a name like `hcu_integration-XXXX.json`

#### What's in the diagnostics file?

The file contains:
- Your device inventory and their current states
- Your heating groups and their configurations
- Entity mappings between HCU and Home Assistant
- Device capabilities and features

> 🔒 **Privacy:** Sensitive data like your door lock PINs and API tokens are automatically **redacted** (replaced with `**REDACTED**`) in the diagnostics file.

#### Sharing diagnostics files:

When reporting an issue on GitHub:
1. Download the diagnostics file as described above
2. Attach it to your GitHub issue
3. This helps identify problems much faster!

---

### Debug Logging

If you need more detailed logs for troubleshooting:

#### Method 1: Via UI (Recommended for Quick Debugging)

This method is perfect for capturing logs for a specific issue.

1. Go to **Settings** → **Devices & Services**
2. Find the **Homematic IP Local (HCU)** card
3. Click the **three dots** (⋮) on the card
4. Click **Enable debug logging**
5. Reproduce the problem you're experiencing
6. Click the **three dots** (⋮) again
7. Click **Disable debug logging**
8. Your browser will immediately download the log file

#### Method 2: Via configuration.yaml (Permanent Logging)

For persistent debug logging that survives restarts:

1. Edit your `configuration.yaml` file
2. Add the following:

```yaml
logger:
  default: info
  logs:
    custom_components.hcu_integration: debug
```

3. Restart Home Assistant
4. Logs will appear in **Settings** → **System** → **Logs**

---

## 🎮 Available Services

The integration provides several custom services for advanced control:

### `hcu_integration.play_sound`

Play a sound on compatible notification devices (e.g., HmIP-MP3P).

**Example:**
```yaml
service: hcu_integration.play_sound
target:
  entity_id: switch.notification_device
data:
  sound_file: "ALARM_01"
  volume: 0.8
  duration: 10
```

### `hcu_integration.set_rule_state`

Enable or disable simple automation rules within the HCU.

**Example:**
```yaml
service: hcu_integration.set_rule_state
data:
  rule_id: "00000000-0000-0000-0000-000000000000"
  enabled: true
```

### `hcu_integration.activate_party_mode`

Activate party mode for heating groups with a specific temperature and duration.

**Example:**
```yaml
service: hcu_integration.activate_party_mode
target:
  entity_id: climate.living_room
data:
  temperature: 22
  duration: 4  # hours
```
---

## 🔘 Working with Stateless Buttons

Stateless buttons (like wall switches and remote controls) don't maintain an on/off state. Instead, they fire events when pressed. This integration handles these devices using Home Assistant's event bus, which is the standard and most flexible approach.

### Supported Stateless Devices

- **Wall Switches:** HmIP-BRC2, HmIP-WRC2, HmIP-WRC6, HmIP-WRCC2, etc.
- **Remote Controls:** HmIP-KRC4, HmIP-RC8, HmIP-KRCK, etc.
- **Contact Interfaces:** HmIP-FCI1, HmIP-FCI6, HmIP-SCI, etc.

### How Events Work

When you press a button on one of these devices, the integration fires an `hcu_integration_event` on the Home Assistant event bus with the following data:
```yaml
event_type: hcu_integration_event
data:
  device_id: "3014F711A00004953B83BE88"  # The device's SGTIN
  channel: "1"                            # The channel number that was pressed
  type: "press"                           # Always "press" for button events
```

### Creating Automations with Button Events

There are two main ways to use button events in your automations:

#### Method 1: Using the Visual Automation Editor (Recommended for Beginners)

1. Go to **Settings** → **Automations & Scenes**
2. Click **+ CREATE AUTOMATION** → **Create new automation**
3. Click **ADD TRIGGER** → **Event**
4. Set the following:
   - **Event type:** `hcu_integration_event`
5. Click **ADD CONDITION** (optional but recommended)
6. Choose **Template** and enter:
```jinja
   {{ trigger.event.data.device_id == '3014F711A00004953B83BE88' and trigger.event.data.channel == '1' }}
```
   *(Replace the device_id with your actual device ID)*
7. Add your desired actions

**Example:** Turn on a light when button 1 is pressed:
```yaml
alias: "Living Room Switch - Button 1"
description: "Turn on living room light when button 1 is pressed"
trigger:
  - platform: event
    event_type: hcu_integration_event
condition:
  - condition: template
    value_template: >
      {{ trigger.event.data.device_id == '3014F711A00004953B83BE88' 
         and trigger.event.data.channel == '1' }}
action:
  - service: light.turn_on
    target:
      entity_id: light.living_room
mode: single
```

#### Method 2: Using YAML (Advanced Users)

For more complex scenarios, you can write automations directly in YAML:

**Example 1:** Toggle a light with a single button
```yaml
alias: "Wall Switch - Toggle Light"
description: "Toggle the bedroom light with wall switch button 1"
trigger:
  - platform: event
    event_type: hcu_integration_event
    event_data:
      device_id: "3014F711A00004953B83BE88"
      channel: "1"
action:
  - service: light.toggle
    target:
      entity_id: light.bedroom
mode: single
```

**Example 2:** Multi-button control (different actions per button)
```yaml
alias: "Remote Control - Multi Button"
description: "Control multiple lights with a 4-button remote"
trigger:
  - platform: event
    event_type: hcu_integration_event
    event_data:
      device_id: "3014F711A00004953B83BE88"
action:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.channel == '1' }}"
        sequence:
          - service: light.turn_on
            target:
              entity_id: light.living_room
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.channel == '2' }}"
        sequence:
          - service: light.turn_off
            target:
              entity_id: light.living_room
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.channel == '3' }}"
        sequence:
          - service: light.turn_on
            target:
              entity_id: light.bedroom
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.channel == '4' }}"
        sequence:
          - service: light.turn_off
            target:
              entity_id: light.bedroom
mode: single
```

**Example 3:** Long press detection (requires multiple presses within a time window)
```yaml
alias: "Wall Switch - Long Press Detection"
description: "Detect long press by counting rapid button presses"
trigger:
  - platform: event
    event_type: hcu_integration_event
    event_data:
      device_id: "3014F711A00004953B83BE88"
      channel: "1"
action:
  - if:
      - condition: state
        entity_id: timer.button_press_timer
        state: active
    then:
      # Second press detected - this is a "long press"
      - service: scene.turn_on
        target:
          entity_id: scene.movie_mode
      - service: timer.cancel
        target:
          entity_id: timer.button_press_timer
    else:
      # First press - start the timer
      - service: timer.start
        target:
          entity_id: timer.button_press_timer
        data:
          duration: "00:00:01"
      - wait_for_trigger:
          - platform: state
            entity_id: timer.button_press_timer
            to: idle
        timeout: "00:00:01"
      # If timer expires without second press, do single press action
      - if:
          - condition: state
            entity_id: timer.button_press_timer
            state: idle
        then:
          - service: light.toggle
            target:
              entity_id: light.living_room
mode: restart
```

*Note: For the long press example, you need to create a timer helper first:*
1. Go to **Settings** → **Devices & Services** → **Helpers**
2. Click **+ CREATE HELPER** → **Timer**
3. Name it "Button Press Timer" (entity_id will be `timer.button_press_timer`)

### Finding Your Device ID and Channel Numbers

To find the device ID and channel numbers for your button device:

1. **Download Diagnostics:**
   - Go to **Settings** → **Devices & Services**
   - Find the **Homematic IP Local (HCU)** integration
   - Click on it, then click the **three dots** (⋮)
   - Select **Download diagnostics**

2. **Open the diagnostics file** in a text editor and search for your device name

3. **Look for the device structure:**
```json
   {
     "3014F711A00004953B83BE88": {
       "hcu_data": {
         "label": "Living Room Wall Switch",
         "functionalChannels": {
           "0": { ... },
           "1": { "functionalChannelType": "SINGLE_KEY_CHANNEL", ... },
           "2": { "functionalChannelType": "SINGLE_KEY_CHANNEL", ... }
         }
       }
     }
   }
```

4. **Note:**
   - The long string (e.g., `3014F711A00004953B83BE88`) is your `device_id`
   - The channel numbers are inside `functionalChannels` (usually "1", "2", "3", etc.)
   - Channel "0" is always the maintenance channel - ignore it

### Testing Your Button Events

You can listen to events in real-time to test your buttons:

1. Go to **Developer Tools** → **Events**
2. In the "Listen to events" section, enter: `hcu_integration_event`
3. Click **START LISTENING**
4. Press buttons on your device and watch the events appear
5. Copy the `device_id` and `channel` values for your automations

### Tips and Best Practices

- **Use Descriptive Aliases:** Name your automations clearly (e.g., "Kitchen Switch Button 1 - Lights")
- **Mode Selection:** Use `mode: single` for most buttons to prevent accidental double-presses
- **Visual Feedback:** Consider adding notifications or confirmation messages in your automations
- **Documentation:** Comment your YAML automations to remember which button does what
- **Test First:** Always test new button automations to ensure they trigger correctly

---

## 🐛 Reporting Issues

Found a bug or have a feature request? Please help improve the integration!

### Before Reporting:

1. ✅ Check if the issue already exists on [GitHub Issues](https://github.com/Ediminator/hacs-homematicip-hcu/issues)
2. ✅ Download diagnostics (see above)
3. ✅ Enable debug logging and capture relevant logs

### Creating an Issue:

1. Go to [GitHub Issues](https://github.com/Ediminator/hacs-homematicip-hcu/issues)
2. Click **New Issue**
3. Provide:
   - Clear description of the problem
   - Steps to reproduce
   - Expected vs actual behavior
   - **Attach your diagnostics file**
   - Relevant log excerpts (if applicable)
   - Home Assistant version
   - Integration version

> 💡 **Tip:** The more information you provide, especially diagnostics files, the faster issues can be resolved!

---

## 🔄 Updating the Integration

When a new version is released:

1. Open HACS
2. Go to **Integrations**
3. Find **Homematic IP Local (HCU)**
4. If an update is available, click **UPDATE**
5. Restart Home Assistant when prompted

---

## ❓ FAQ

### Can I use both the cloud integration and this local integration?

It's not recommended to run both simultaneously as they may conflict. Choose one approach.

### My device isn't appearing in Home Assistant

1. Make sure the device is visible in your HCU web interface
2. Check if it's a third-party device that might be filtered (check Configuration Options)
3. Download diagnostics and check if the device is listed there
4. Create an issue on GitHub with your diagnostics file

### The integration says "Failed to connect"

- Verify the HCU's IP address is correct
- Make sure Developer Mode is enabled on the HCU
- Check that "Expose the Connect API WebSocket" is enabled
- Verify your network allows communication on ports 6969 and 9001
- Try accessing the HCU web interface from the same machine running Home Assistant

### My door lock is showing as "Unavailable"

Make sure you've configured the door lock PIN in the integration options (see Step 4 above).

### Can I control the HCU itself (reboot, updates, etc.)?

No, this integration only controls the devices connected to the HCU. HCU management must be done through the HCU web interface.

---

## 📜 License

This project is provided as-is for personal use. Please check the repository for license details.

---

## 🙏 Credits

Created and maintained by [@Ediminator](https://github.com/Ediminator)

Special thanks to all contributors and users who provide diagnostics files and feedback to improve the integration!

---

## 💬 Support

- **Issues & Bug Reports:** [GitHub Issues](https://github.com/Ediminator/hacs-homematicip-hcu/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Ediminator/hacs-homematicip-hcu/discussions)

**Remember:** When asking for help, always include your diagnostics file - it makes troubleshooting much faster! 🚀
