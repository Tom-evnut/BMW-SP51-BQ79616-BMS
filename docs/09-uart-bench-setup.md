# Talking to the daughter-board BQ79616 over UART (bench)

Goal: read registers from the base BQ79616 directly, with the daughter board **removed from the SME** and **no HV or
modules connected**.

## Wiring

```
Floating 12 V bench supply              USB-UART adapter (3.3 V logic)
   (+) ──► B10  isolated supply            TX  ──► A7  (ISO7721 INA  → BQ79616 RX)
   (−) ──► A10  isolated GND               RX  ◄── B7  (ISO7721 OUTB ← BQ79616 TX)
                                           3V3 ──► A8  (ISO7721 VCC2)
                                           GND ──► A6  (ISO7721 GND2)
```

| Header pin | Connect to | Notes |
|---|---|---|
| B10 | 12 V (+) | 9–40 V allowed (BQ79616 BAT minimum 9 V, TPS7A6650 maximum 40 V). Current limit ~100 mA |
| A10 | 12 V (−) | Isolated ground. **Do not connect to A6** |
| A8 | 3.3 V | ISO7721 VCC2 accepts 2.25–5.5 V and translates to the 5 V BQ side |
| A6 | Adapter / MCU GND | |
| A7 | Adapter / MCU TX | Must idle high. Holding it low ≥ 7 ms sends SHUTDOWN, ≥ 36 ms sends HW_RESET |
| B7 | Adapter / MCU RX | 3.3 V push-pull output from the ISO7721 |
| A1, B1 | Leave open | Daisy chain, not needed for the base device alone |

- Keep the 12 V supply **floating** (no earth strap) and don't link A10 to A6. On the bench, with no HV, a link wouldn't
  hurt anything, but keeping the domains separate matches how the board is used in the car.
- Expected supply current: about 10 mA through the 1.2 kΩ load, plus about 20 mA inrush when the BQ79616 wakes.

### Using an FTDI TTL-232R-5V-WE cable

The FTDI TTL-232R-5V cable (FT232R chip, 5 V logic, wire-ended) works directly. The ISO7721 host side accepts 5 V, so
power A8 from the cable's own 5 V wire and all the logic levels match. The FT232R supports both 1 Mbaud and the
4000 baud used for the WAKE pulse.

| Cable wire | Signal | Header pin |
|---|---|---|
| Black | GND | **A6** |
| Orange | TXD (output) | **A7** |
| Yellow | RXD (input) | **B7** |
| Red | VCC 5 V | **A8** |
| Brown | CTS# | not connected |
| Green | RTS# | not connected |

Check the colours against the label or datasheet of your cable before connecting.

## Bench measurements

| Date | Condition | B10 supply | Current | Notes |
|---|---|---|---|---|
| | Isolated side only (A8 unpowered, UART not connected) | 13.26 V | 63 mA | Higher than the ~20–25 mA budget below, so there is an extra load to find |
| | After WAKE via A7 (TTL-232R-5V, TXD confirmed on A7) | 13.23 V | 62 → 72 mA | **WAKE confirmed**: +10 mA = BQ79616 ACTIVE. No UART reply yet. Current limit must allow the wake-up surge |

Rough current budget on B10:

| Load | Current |
|---|---|
| 1.2 kΩ B10–A10 path | ~11 mA at 13 V |
| BQ79616 in SHUTDOWN / ACTIVE (idle) | 16 µA / ~11.6 mA |
| 5 V rail: ISO7721, 2 × INA240, 2 × LM2904B, logic | ~8–10 mA |

A successful WAKE should raise the supply current by about 12 mA, as the BQ79616 goes from SHUTDOWN to ACTIVE.

## UART

- 1 Mbaud, 8N1, idle high, half duplex. Send a command and wait for the full response before sending the next.
- The **WAKE ping** must hold RX low for **2–2.5 ms**. [tools/bq_uart.py](../tools/bq_uart.py) does this by sending
  `0x00` at 4000 baud: start bit plus 8 zero bits = 2.25 ms. The adapter must support 4000 baud; FTDI does.
- With a microcontroller instead, switch the TX pin to GPIO, drive it low for 2.25 ms, then switch it back to the UART.

## First session

```bash
pip install pyserial
cd tools
python bq_uart.py COM5 info -v     # WAKE, then PARTID, DEV_REVID, DIR0_ADDR, OTP shadow dump
python bq_uart.py COM5 cells -v    # start main ADC (continuous), read VCELL16..VCELL1
```

The frames sent (CRC checked against the datasheet example):

| Action | Frame |
|---|---|
| Read PARTID (0x0500), 1 byte | `80 00 05 00 00 35 DF` |
| Read OTP shadow 0x0000–0x0037, 56 bytes | `80 00 00 00 37 64 08` |
| Start main ADC, continuous (ADC_CTRL1 = 0x06) | `90 00 03 0D 06 90 8F` |
| Read VCELL16…VCELL1, 32 bytes | `80 00 05 68 1F 5B D7` |

A response is `INIT (length − 1) | DEV ADR | REG hi | REG lo | DATA … | CRC lo | CRC hi`.

## What to expect

- **PARTID / DEV_REVID:** silicon revision.
- **OTP shadow (0x0000–0x0037):** BMW's programmed defaults, if they programmed customer OTP. If the values are factory
  defaults, BMW configures everything at runtime and those settings have to come from sniffing the SME.
- **VCELL1:** left INA240 output. **VCELL1 + VCELL2:** right INA240 output. With no current flowing, both should read
  the INA240 reference voltage (probably ~2.5 V if set up for bidirectional measurement).
- **VCELL11 / VCELL14:** involve the 5 V rail, so expect readings related to 5 V, depending on what VC10, VC12, VC13
  and VC15 are connected to.

## First contact results

Bench setup: TTL-232R-5V cable on COM12, B10 = 13.23 V.

**Key lesson:** after WAKE, the device **ignores reads until the auto-address sequence has run**, even when it's a lone
base device. `bq_uart.py` now does this automatically (`init_single()`): DLL-sync broadcast write, `CONTROL1[ADDR_WR]`,
`DIR0_ADDR = 0`, `COMM_CTRL = 0`, DLL-sync broadcast read.

| Register | Value | Meaning |
|---|---|---|
| PARTID | 0x21 | BQ79616 |
| DEV_REVID | 0x00 | Normal operating mode |
| DEV_STAT | 0x60 | Factory and customer CRC checks completed |
| FAULT_SUMMARY | 0x12 | FAULT_COMM + FAULT_SYS (expected after the bench experiments; not yet cleared) |
| OTP shadow 0x0000–0x0037 | Factory defaults (ACTIVE_CELL 0x0A = 16S, PWR_TRANSIT_CONF 0x10, CUST_CRC 0x31F3) | **BMW did not program customer OTP.** All configuration is written at runtime by the SME, so it has to be sniffed |

### BAT supply (AUX ADC)

`python bq_uart.py COM12 bat` writes `ADC_CTRL3` (0x030F) = 0x06 (AUX_GO, continuous) and reads `AUX_BAT` (0x05B6,
3.05 mV/LSB).

| Bench supply at B10 | AUX_BAT (3 reads) |
|---|---|
| 13.23 V | 13.237 / 13.243 / 13.231 V |

This agrees with the bench supply to within a few mV, so the ~30 Ω in series with BAT carries negligible current. The
BCP56 collector probably takes its current before that resistor.

### Main ADC, no HV connected, no current

VCn node voltages relative to A10. VCELL10 saturates (+6.25 V limit), so the upper nodes are referenced to VC11 = 5.00 V
(DMM-confirmed).

| Node | Voltage | Interpretation |
|---|---|---|
| VC0 | 0 | GND |
| VC1 | 2.500 V | Left INA240 output: exactly mid-scale, so **bidirectional with a 2.5 V reference, 0 A** |
| VC2 | 1.950 V | Right INA240 output: **not** 2.5 V. Different reference or configuration; check its REF1/REF2 pins |
| VC3, VC5, VC6, VC7 | 5.00 V | On the 5 V rail |
| VC4, VC8, VC9 | 5.26 / 5.34 / 5.12 V | Slightly above 5 V, so driven by something on a higher supply (LM2904B outputs?) |
| VC10 | ~10.8 V | Above the 5 V rail, possibly derived from B10 |
| VC11 | 5.00 V | 5 V rail (confirmed) |
| VC12, VC13 | ~7.57 V | ~2.57 V above the 5 V reference |
| VC14 | 5.00 V | 5 V rail (confirmed; computed value agrees) |
| VC15 | ~7.61 V | ~2.61 V above VC14 |
| VC16 | ~9.94 V | |

The upper channels (VCELL12, VCELL15, VCELL16 ≈ 2.3–2.6 V) look like **bipolar signals centred about 2.5 V above a 5 V
reference**, which is typical for HV-divider or insulation measurements. That needs confirming by tracing.

## Troubleshooting

| Symptom | Check |
|---|---|
| No response at all | Did the auto-address sequence run? Reads are ignored before it. Does the supply current rise ~10 mA after WAKE? B10 ≥ 9 V. TX/RX swapped? Is the current limit high enough for the wake-up surge? |
| Response with a CRC error | Baud accuracy: the BQ79616 tolerates about ±1.5 %. Check the ground (A6) connection |
| No response at address 0 | BMW may have programmed a different OTP address. Try a broadcast read (`0xC0`), or broadcast-write `CONTROL1[ADDR_WR] = 1` followed by broadcast-write `DIR0_ADDR = 0` |
| Works once, then stops | Communication timeout (`COMM_TIMEOUT_CONF`) may send the device to sleep or shutdown. Send WAKE again |
