# Release v1.15.14 - Radio Traffic Fix & Duty Cycle Monitoring

## 🐛 Critical Bug Fix

### Fix Radio Traffic Sensor Showing Values Up to 2000%

Fixed a critical bug where the **Radio Traffic (carrierSense) sensor** was displaying incorrect values, with reports of readings spiking up to **2000%** instead of the correct ~20%.

**What was wrong:**
- The HCU API sends `carrierSense` values already as percentages (e.g., 0.20 = 20%)
- The integration was incorrectly multiplying this by 100 again
- Result: 20% became 2000% 📈

**Now fixed:**
- ✅ Radio Traffic sensor shows correct percentage values
- ✅ No more unrealistic spikes
- ✅ Proper rounding to 1 decimal place

---

## ✨ New Feature: Duty Cycle Monitoring

Added comprehensive **duty cycle monitoring** to help you track radio transmission limits and network health!

### What is Duty Cycle?

Homematic IP devices operate on sub-GHz frequencies with strict transmission limits (typically **1% per hour**) to comply with regulations. If devices exceed these limits, they can't transmit and may become unresponsive.

### New Entities (All Disabled by Default)

#### 1. 📡 Overall Duty Cycle Sensor
- **What it shows:** System-wide radio network transmission levels
- **Where to find:** Home Assistant entity for your HCU
- **Entity:** `sensor.homematic_ip_hcu_duty_cycle`
- **Example value:** 5.3%

#### 2. 📊 Duty Cycle Level Sensors
- **What it shows:** Individual duty cycle for each access point
- **Available for:** Your HCU and any additional access points (HmIP-HAP)
- **Entity:** `sensor.[device_name]_duty_cycle_level`
- **Example value:** 13.5%

#### 3. ⚠️ Duty Cycle Limit Warning Sensors
- **What it shows:** Binary warning when a device exceeds its 1% transmission limit
- **Available for:** Most devices
- **Entity:** `binary_sensor.[device_name]_duty_cycle_limit`
- **Values:**
  - `on` = Device exceeded limit ⚠️
  - `off` = Normal operation ✅

### How to Enable

All new duty cycle entities are **disabled by default** to avoid clutter. To enable them:

1. Go to **Settings** → **Devices & Services**
2. Find your **Homematic IP Local (HCU)** integration
3. Click on the HCU device or access point
4. Find the disabled duty cycle entities
5. Click on them and enable them

### Why Monitor Duty Cycle?

- 🔍 **Diagnose communication issues** - High duty cycle can cause devices to stop responding
- 📈 **Track network health** - See if you're approaching regulatory limits
- ⚡ **Optimize your setup** - Identify devices transmitting too frequently
- 🛡️ **Prevent problems** - Get warnings before devices become unavailable

---

## 🔧 Technical Details

### Dictionary Key Collision Fix

The HCU API uses `dutyCycle` for **two different purposes**:
- On home object: Percentage value (system-wide)
- On device channels: Boolean flag (warning)

We implemented special handling to support both without conflicts, similar to how temperature sensors work.

### Consistent Formatting

All percentage-based sensors now have **consistent decimal formatting**:
- Radio Traffic: `20.5%` ✅ (was showing `2050%` ❌)
- Duty Cycle: `5.3%` ✅
- Duty Cycle Level: `13.5%` ✅

---

## 📦 Installation

### Via HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Find **Homematic IP Local (HCU)**
4. Click **Update** (or **Download** if not installed)
5. **Restart Home Assistant**

### Manual Installation

Download the latest release and copy to `custom_components/hcu_integration/`

---

## 📝 Files Changed

- `custom_components/hcu_integration/manifest.json` - Version bump to 1.15.14
- `custom_components/hcu_integration/sensor.py` - Fixed carrierSense multiplication, added duty cycle rounding
- `custom_components/hcu_integration/const.py` - Added duty cycle entity definitions
- `custom_components/hcu_integration/discovery.py` - Special handling for duty cycle binary sensors
- `CHANGELOG.md` - Complete changelog entry

---

## 🙏 Credits

**Reported by:** Community users in Issue #112

**Fixed by:** @Ediminator with AI assistance

---

## ⚠️ Breaking Changes

None! This is a **bug fix and feature enhancement** release.

---

## 🐛 Known Issues

None reported for this release.

---

**Full Changelog:** See [CHANGELOG.md](./CHANGELOG.md) for detailed technical information.
