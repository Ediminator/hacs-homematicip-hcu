# Homematic IP Local (HCU) Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

**Local control** for your Homematic IP devices via the Home Control Unit (HCU). No cloud required!

This integration connects directly to your HCU's local API, providing real-time control and status updates for all your Homematic IP devices through Home Assistant.

---

## 📋 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [Configuration](#-configuration-options)
- [Working with Buttons & Remote Controls](#-working-with-buttons--remote-controls) ⭐ **NEW: Simplified Guide**
- [Available Services](#-available-services)
- [Diagnostics & Troubleshooting](#-diagnostics--troubleshooting)
- [FAQ](#-faq)
- [Support](#-support)

---

## 🌟 Features

- **🏠 Local Control**: Direct communication with your HCU - no cloud dependency
- **⚡ Real-time Updates**: Instant device state changes via WebSocket
- **🔌 Full Device Support**: Switches, lights, sensors, climate, covers, locks, and more
- **🎛️ Advanced Climate Control**: Heating profiles, party mode, vacation mode
- **🔘 Event-Based Buttons**: Stateless button devices trigger automation events
- **🛡️ Security Integration**: Alarm control panel for your security system
- **🔧 Extensive Services**: Play sounds, control rules, manage heating schedules
- **📊 Diagnostics**: Built-in diagnostics for troubleshooting and device support

---

## 📦 Requirements

- **Home Assistant** 2024.1.0 or newer
- **Homematic IP Home Control Unit (HCU)** with firmware 1.x or later
- **Local network access** to your HCU

---

## 🚀 Installation

### Step 1: Install via HACS

[![Open your Home Assistant instance and add this repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Ediminator&repository=hacs-homematicip-hcu&category=Integration)

Or, add it manually:

1. Open **HACS** in your Home Assistant sidebar
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

5. Toggle the switch to **Expose the Connect API WebSocket**
   - ⚠️ **Important:** Sometimes the toggle is already activated even on first setup. Please **deactivate and activate the toggle** to ensure it's properly enabled.

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

## 🔘 Working with Buttons & Remote Controls

**⭐ This is the most common question, so read this section carefully!**

### Understanding Button Devices

Stateless button devices (wall switches, remote controls, etc.) work differently from regular switches in Home Assistant:

**❌ You will NOT see:**
- Button entities in your entity list
- Buttons in the device card
- Toggle switches for each button

**✅ You WILL get:**
- Events fired on the Home Assistant event bus
- Full control via automations
- Support for multi-button scenarios

**Why?** Stateless buttons don't maintain an on/off state - they only send momentary press signals. Home Assistant's standard approach for these devices is to use events, which provides much more flexibility for automations.

---

### Supported Button Devices

This integration supports button events for:

**Wall Switches:**
- HmIP-WGS (Wall-mounted Glass Switch) ⭐ **Fixed in v1.8.1**
- HmIP-WRC2 (2-button Wall Remote)
- HmIP-WRC6 (6-button Wall Remote) ⭐ **Fixed in v1.8.1**
- HmIP-WRCC2 (Wall Remote with Display)
- HmIP-BRC2 (2-button Remote Control)
- And more...

**Remote Controls:**
- HmIP-KRC4 (4-button Key Ring Remote)
- HmIP-RC8 (8-button Remote)
- HmIP-KRCK (Key Ring Remote with Display)
- And more...

**Contact Interfaces (when configured as buttons):**
- HmIP-FCI1 (Flush-mount Contact Interface 1)
- HmIP-FCI6 (Flush-mount Contact Interface 6)
- HmIP-SCI (Shutter Contact Interface)

---

### Step-by-Step: Testing Your Buttons

Before creating automations, verify your buttons are working:

#### 1. Open the Events Monitor

1. Go to **Developer Tools** → **Events** (in the sidebar)
2. In the "Listen to events" section, type: `hcu_integration_event`
3. Click **START LISTENING**

#### 2. Press Your Buttons

- Press any button on your Homematic IP device
- You should immediately see an event appear in the event monitor

#### 3. Understand the Event Data

When a button is pressed, you'll see something like this:

```yaml
event_type: hcu_integration_event
data:
  device_id: 3014F711A00048240995D6BC
  channel: 1
  type: KEY_PRESS_SHORT
origin: LOCAL
time_fired: 2025-10-26T10:30:45.123456+00:00
```

**What each field means:**
- `device_id`: The unique ID of your button device (SGTIN)
- `channel`: Which button was pressed (1, 2, 3, etc.)
- `type`: The type of the button event (`KEY_PRESS_SHORT`, `KEY_PRESS_LONG`,
          `KEY_PRESS_LONG_START` or `KEY_PRESS_LONG_STOP`)

**Please note**: A long button press first generates a single `KEY_PRESS_LONG`
event, followed by a single `KEY_PRESS_LONG_START` event. As long as the button
is pressed, a sequence of periodic `KEY_PRESS_LONG` events is then generated
approximately every 0.35 seconds. When the button is released, a single
`KEY_PRESS_LONG_STOP` event is generated.

#### 4. Note Down Your Device ID and Channels

**Important:** You'll need these values for your automations!

- Write down your `device_id`
- Note which `channel` corresponds to each physical button

**💡 Tip:** You can find your device_id more easily in the diagnostics file - see the [Diagnostics section](#-diagnostics--troubleshooting) below.

---

### Creating Button Automations

Now that you've confirmed your buttons work, let's create automations!

#### Method 1: Visual Editor (Recommended for Beginners)

**Example: Turn on a light when button 1 is pressed**

1. Go to **Settings** → **Automations & Scenes**
2. Click **+ CREATE AUTOMATION** → **Create new automation**
3. **Add Trigger:**
   - Click **ADD TRIGGER**
   - Select **Event**
   - Event type: `hcu_integration_event`
4. **Add Condition:**
   - Click **ADD CONDITION**
   - Select **Template**
   - Template:
     ```jinja
     {{ trigger.event.data.device_id == '3014F711A00048240995D6BC' and trigger.event.data.channel == 1 }}     
     ```
   - Replace the `device_id` and `channel` with your values!
5. **Add Action:**
   - Click **ADD ACTION**
   - Select **Call service**
   - Service: `light.turn_on`
   - Target: Choose your light
6. **Save** your automation with a descriptive name

---

#### Method 2: YAML (For Advanced Users)

**Example 1: Simple Toggle**

```yaml
alias: Living Room - Button 1 Toggle Light
description: Toggle living room light with wall switch button 1
mode: single
triggers:
  - event_type: hcu_integration_event
    event_data:
      device_id: 3014F711A00048240995D6BC
      channel: 1
    trigger: event
actions:
  - target:
      entity_id: light.living_room
    action: light.toggle
```

**Example 2: Multi-Button Control (Choose Action by Button)**

```yaml
alias: Kitchen Remote - 4 Buttons
description: Control multiple lights with a 4-button remote
mode: single
triggers:
  - event_type: hcu_integration_event
    event_data:
      device_id: 3014F711A00048240995D6BC
    trigger: event
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.channel == 1 }}"
        sequence:
          - target:
              entity_id: light.kitchen_main
            action: light.turn_on
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.channel == 2 }}"
        sequence:
          - target:
              entity_id: light.kitchen_main
            action: light.turn_off
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.channel == 3 }}"
        sequence:
          - target:
              entity_id: light.kitchen_cabinet
            action: light.turn_on
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.channel == 4 }}"
        sequence:
          - target:
              entity_id: light.kitchen_cabinet
            action: light.turn_off
```

**Example 3: Same Button for On/Off (Double Press Detection)**

```yaml
alias: Bedroom - Button 1 with Double Press
description: Single press = dim light, double press = full brightness
mode: restart
triggers:
  - event_type: hcu_integration_event
    event_data:
      device_id: 3014F711A00048240995D6BC
      channel: 1
    trigger: event
actions:
  - if:
      - condition: state
        entity_id: timer.button_press_timer
        state: active
    then:
      # Second press detected within 1 second
      - target:
          entity_id: light.bedroom
        data:
          brightness: 255
        action: light.turn_on
      - target:
          entity_id: timer.button_press_timer
        action: timer.cancel
    else:
      # First press - start timer
      - target:
          entity_id: timer.button_press_timer
        data:
          duration: "00:00:01"
        action: timer.start
      - wait_for_trigger:
          - entity_id: timer.button_press_timer
            to: idle
            trigger: state
        timeout: "00:00:01"
      # Timer expired - this was a single press
      - if:
          - condition: state
            entity_id: timer.button_press_timer
            state: idle
        then:
          - target:
              entity_id: light.bedroom
            data:
              brightness: 128
            action: light.turn_on
```

*Note: For double-press detection, create a timer helper first:*
1. Go to **Settings** → **Devices & Services** → **Helpers**
2. Click **+ CREATE HELPER** → **Timer**
3. Name: "Button Press Timer"
4. Duration: "00:00:01"

**Example 4: Switch or Dim (Using Short and Long Press Events)**

```
alias: Offic - Switch or Dim the light
triggers:
  - event_type: hcu_integration_event
    event_data:
      device_id: 3014F711A00048240995D6BC
      channel: 1
    trigger: event
actions:
  - choose:
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.type == 'KEY_PRESS_SHORT' }}"
        sequence:
          - target:
              entity_id: light.light_office
            action: light.toggle
      - conditions:
          - condition: template
            value_template: "{{ trigger.event.data.type == 'KEY_PRESS_LONG' }}"
        sequence:
          - repeat:
              while:
                - condition: template
                  value_template: |
                    {{ trigger.event.data.type == 'KEY_PRESS_LONG' }}
              sequence:
                - data:
                    entity_id: light.light_office
                    brightness_step: 10
                  action: light.turn_on
                - delay: "0.2"
mode: restart
```

---

### Finding Your Device ID and Channels

**Easiest Method: Use Diagnostics**

1. Go to **Settings** → **Devices & Services**
2. Find the **Homematic IP Local (HCU)** card and click it
3. Find your button device in the list and click it
4. Click the **three dots** (⋮) in the top right
5. Select **Download diagnostics** (or just look at the device info on the page)
6. The device ID (SGTIN) is shown clearly

**Manual Method: Diagnostics File**

1. Download the full integration diagnostics:
   - Settings → Devices & Services
   - Click on the Homematic IP Local (HCU) card
   - Three dots (⋮) → Download diagnostics

2. Open the JSON file and search for your device name

3. Look for the structure:
   ```json
   "3014F711A00048240995D6BC": {
     "label": "Living Room Wall Switch",
     "functionalChannels": {
       "0": { "functionalChannelType": "DEVICE_BASE" },
       "1": { "functionalChannelType": "SINGLE_KEY_CHANNEL" },
       "2": { "functionalChannelType": "SINGLE_KEY_CHANNEL" },
       "3": { "functionalChannelType": "SINGLE_KEY_CHANNEL" },
       "4": { "functionalChannelType": "SINGLE_KEY_CHANNEL" }
     }
   }
   ```

4. Note:
   - The long string is your `device_id`
   - Channels 1, 2, 3, 4 are your buttons (ignore channel 0 - it's always the maintenance channel)

---

### Troubleshooting Button Events

**Problem: No events appear when I press buttons**

✅ **Solutions:**
1. **Update to v1.8.1 or later** - Critical bug fixes for HmIP-WGS and HmIP-WRC6
2. **Verify the device is connected:**
   - Check Settings → Devices & Services → Your device
   - Make sure it's not showing as "unavailable"
3. **Check you're listening to the right event:**
   - Event type must be exactly: `hcu_integration_event` (no spaces, underscores)
4. **Enable debug logging:**
   - See [Debug Logging section](#debug-logging) below
   - Look for lines like "Button press detected via..." in the logs
5. **Verify your button device is actually a button:**
   - Not all channels are buttons
   - Check diagnostics to see the channel type

**Problem: I see button entities in my old version**

This is expected if you're upgrading from a very old version (pre-1.5.0). The old button entities were removed because:
- They didn't reflect the actual button press (always showed "unknown")
- Event-based triggers are more flexible and reliable
- This matches Home Assistant's standard approach

Simply delete the old button entities and use event-based automations instead.

---

## 📊 Diagnostics & Troubleshooting

### Downloading Diagnostics

Diagnostics files are **extremely valuable** for troubleshooting and adding support for new devices.

**When to download diagnostics:**
- Before reporting an issue on GitHub
- When buttons aren't working (v1.8.1 or later fixes most button issues)
- When a device isn't working correctly
- To help add support for a new device type

**How to Download:**

1. Go to **Settings** → **Devices & Services**
2. Find the **Homematic IP Local (HCU)** integration card
3. Click on the card to open the integration details
4. In the top right, click the **three dots** (⋮)
5. Select **Download diagnostics**
6. Your browser downloads: `hcu_integration-XXXX.json`

**What's in the file?**
- Complete device inventory and current states
- Heating groups and configurations
- Entity mappings
- Device capabilities

**Privacy:** Sensitive data like PINs and tokens are automatically redacted (`**REDACTED**`).

---

### Debug Logging

For detailed troubleshooting, especially for button events:

#### Method 1: Quick Debug (Recommended)

1. Go to **Settings** → **Devices & Services**
2. Find **Homematic IP Local (HCU)** card
3. Click the **three dots** (⋮)
4. Click **Enable debug logging**
5. Reproduce the issue (e.g., press your buttons)
6. Click the **three dots** (⋮) again
7. Click **Disable debug logging**
8. Your browser immediately downloads the log file

**Look for these log entries for button debugging:**
- `Button press detected via timestamp change` - Timestamp-based detection (old devices)
- `Button press detected for stateless channel` - Event-based detection (HmIP-WGS, HmIP-WRC6, etc.)

#### Method 2: Permanent Logging

For persistent debug logging:

1. Edit your `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.hcu_integration: debug
   ```

2. Restart Home Assistant
3. View logs in **Settings** → **System** → **Logs**

---

## 🎮 Available Services

### `hcu_integration.play_sound`

Play a sound on compatible notification devices (e.g., HmIP-MP3P).

**Example:**
```yaml
service: hcu_integration.play_sound
target:
  entity_id: switch.doorbell
data:
  sound_file: "ALARM_01"
  volume: 0.8
  duration: 10
```

### `hcu_integration.set_rule_state`

Enable or disable automation rules within the HCU.

**Example:**
```yaml
service: hcu_integration.set_rule_state
data:
  rule_id: "00000000-0000-0000-0000-000000000000"
  enabled: true
```

### `hcu_integration.activate_party_mode`

Temporarily override heating schedule for a specific room.

**Example:**
```yaml
service: hcu_integration.activate_party_mode
target:
  entity_id: climate.living_room
data:
  temperature: 22
  duration: 14400  # 4 hours in seconds
```

### `hcu_integration.activate_vacation_mode`

System-wide vacation mode for all heating groups.

**Example:**
```yaml
service: hcu_integration.activate_vacation_mode
data:
  temperature: 15
  end_time: "2025-12-24 18:00"
```

### `hcu_integration.activate_eco_mode`

Activate permanent absence (Eco) mode.

**Example:**
```yaml
service: hcu_integration.activate_eco_mode
```

### `hcu_integration.deactivate_absence_mode`

Deactivate any active absence mode.

**Example:**
```yaml
service: hcu_integration.deactivate_absence_mode
```

---

## 🔄 Updating the Integration

When a new version is released:

1. Open **HACS**
2. Go to **Integrations**
3. Find **Homematic IP Local (HCU)**
4. If an update is available, click **UPDATE**
5. **Restart Home Assistant**

**Important:** Always check the CHANGELOG before updating for any breaking changes or new requirements.

---

## ❓ FAQ

### Can I use both the cloud integration and this local integration?

Not recommended. Running both simultaneously may cause conflicts. Choose one approach.

### My button device isn't working (HmIP-WGS, HmIP-WRC6, etc.)

Make sure you're on **v1.8.1 or later**. This version includes critical fixes for button event detection. See the [Button Troubleshooting section](#troubleshooting-button-events) above.

### Why don't I see button entities anymore?

As of v1.5.0, button devices use **event-based triggers** instead of entities. This is the Home Assistant standard for stateless buttons and provides more flexibility. See the [Button section](#-working-with-buttons--remote-controls) for how to use them.

### My device isn't appearing in Home Assistant

1. Verify the device appears in the HCU web interface
2. Check if it's a third-party device (may be filtered)
3. Download diagnostics and check if the device is listed
4. Create an issue on GitHub with your diagnostics file

### The integration says "Failed to connect"

- Verify the HCU's IP address is correct
- Ensure Developer Mode is enabled on the HCU
- Check "Expose the Connect API WebSocket" is enabled
- Verify ports 6969 and 9001 are accessible
- Try accessing the HCU web interface from the same machine running Home Assistant

### My door lock shows as "Unavailable"

Configure the door lock PIN in the integration options (Settings → Devices & Services → HCU → Configure).

### Can I control the HCU itself (reboot, updates, etc.)?

No, this integration only controls devices connected to the HCU. HCU management must be done through the HCU web interface.

---

## 💬 Support

- **Issues & Bug Reports:** [GitHub Issues](https://github.com/Ediminator/hacs-homematicip-hcu/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Ediminator/hacs-homematicip-hcu/discussions)

**When asking for help:**
1. Always include your Home Assistant version
2. Include your integration version
3. Attach diagnostics file when possible
4. Enable debug logging and include relevant log excerpts
5. Clearly describe what you expected vs. what happened

---

## 📜 License

This project is provided as-is for personal use. Please check the repository for license details.

---

## 🙏 Credits

Created and maintained by [@Ediminator](https://github.com/Ediminator)

Special thanks to all contributors and users who provide diagnostics files and feedback to improve the integration!

---

**Remember:** When in doubt, download diagnostics - it makes troubleshooting much faster! 🚀
