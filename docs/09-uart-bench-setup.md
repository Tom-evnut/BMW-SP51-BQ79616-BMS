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

## Troubleshooting

| Symptom | Check |
|---|---|
| No response at all | WAKE pulse width (scope A7): 2–2.5 ms. B10 ≥ 9 V. A8 = 3.3 V. TX/RX swapped? |
| Response with a CRC error | Baud accuracy: the BQ79616 tolerates about ±1.5 %. Check the ground (A6) connection |
| No response at address 0 | BMW may have programmed a different OTP address. Try a broadcast read (`0xC0`), or broadcast-write `CONTROL1[ADDR_WR] = 1` followed by broadcast-write `DIR0_ADDR = 0` |
| Works once, then stops | Communication timeout (`COMM_TIMEOUT_CONF`) may send the device to sleep or shutdown. Send WAKE again |
