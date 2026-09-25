# SimpBMS / Victron CAN to ZombieVerter

The new BMS reports to a ZombieVerter VCU with `BMS_Mode = 1 (SimpBMS)`.

## What ZombieVerter actually decodes

From `src/simpbms.cpp` in [damienmaguire/Stm32-vcu](https://github.com/damienmaguire/Stm32-vcu). All values are
little-endian.

| ID | Bytes | Meaning | ZombieVerter use |
|---|---|---|---|
| **0x373** | 0-1 | Min cell voltage, mV | **Only frame that resets the timeout** (`BMS_Timeout`, in seconds) |
| | 2-3 | Max cell voltage, mV | Charge gating against `BMS_VminLimit` / `BMS_VmaxLimit` |
| | 4-5 | Min temperature, K (°C = value − 273) | Charge gating against `BMS_TminLimit` / `BMS_TmaxLimit` |
| | 6-7 | Max temperature, K | |
| **0x351** | 2-3 | Charge current limit, 0.1 A | Charger current. **0 ends AC charging and locks out until the next drive** |
| **0x356** | 0-1 | Pack voltage, 0.01 V | Only when `ShuntType = 0`: sets `udc2`, and `udcsw` = V − 30 (for precharge) |
| | 2-3 | Pack current, int16, 0.1 A | Only when `ShuntType = 0`: sets `idc` |
| **0x355** | 0-1 | SOC, 1 % | Display |

## Gotchas

1. **Discharge current limits are ignored.** 0x351 bytes 4-5 (DCL), the voltage limits and 0x35A alarms are not decoded,
   and `BMS_MaxInput` / `BMS_MaxOutput` aren't set in SimpBMS mode. ZombieVerter will not reduce motor or regen power
   on BMS request. **The BMS must be able to open the contactors in hardware** (a "BMS OK" interlock).
2. **Charge lockout latches.** Sending a charge current limit of 0 during AC charge, or letting 0x373 time out, ends
   the charge until the next drive cycle. So:
   - Wake the BMS on charger plug-in and on KL15.
   - Only start sending once measurements are valid.
   - Reduce the current limit rather than sending 0 for short pauses (for example, while balancing).
3. **Current sign.** The Victron convention is positive = charging. ZombieVerter passes the value straight into `idc`,
   so check the sign against how ZombieVerter's `idc` is used before relying on `ShuntType = 0`.

## Frames the BMS should send

Send every 100–200 ms at 500 kbps. Use the full Victron set so other Victron-compatible equipment understands it too.

| ID | Content |
|---|---|
| 0x351 | Charge voltage limit (0.1 V), charge current limit (0.1 A), discharge current limit (0.1 A), discharge voltage limit (0.1 V) |
| 0x355 | SOC (%), SOH (%), high-resolution SOC (0.01 %) |
| 0x356 | Pack voltage (0.01 V), current (0.1 A, signed), temperature (0.1 °C) |
| 0x35A | Alarm and warning bitfields |
| 0x35E | Manufacturer name (ASCII) |
| 0x35F | Battery info / firmware version |
| 0x373 | Min/max cell mV, min/max temperature K |
| 0x379 | Installed capacity (Ah) |

Per-cell data (108 voltages plus temperatures) goes on the separate diagnostics bus or on IDs that don't clash.
