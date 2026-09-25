# BQ79616-Q1 quick reference

All values here are from the datasheet [SLUSE81F](../datasheets/BQ79616-Q1_SLUSE81F.pdf) (Aug 2020, revised Jun 2026).
When in doubt, the datasheet wins.

## Package and pins

64-pin HTQFP (PAP), 10 × 10 mm, 0.5 mm pitch, with an exposed pad. Pin 1 is BAT, at the dot corner.
Pins 1–16 run down the left side, 17–32 along the bottom, 33–48 up the right side, and 49–64 right-to-left across the top.

| Pin | Name | Notes |
|---|---|---|
| 1 | BAT | Module supply, 9–80 V for full functionality |
| 2–35 (alternating) | CB16, VC16, CB15, … VC1, CB0, VC0 | Cell balance and sense inputs (pin 2 = CB16 … pin 35 = VC0) |
| 36 / 37 | REFHM / REFHP | |
| 38 / 39 | AVDD / AVSS | |
| 40 / 41 | COMLP / COMLN | Daisy chain, low side (ring / towards the host) |
| 42 / 43 | COMHN / COMHP | Daisy chain, high side (towards the next device up) |
| 44 | NEG5V | |
| 45 / 46 | CVDD / CVSS | 5 V comms supply |
| 47 | LDOIN | |
| 48 | NPNB | |
| 49 / 50 | DVDD / DVSS | |
| 51 | TSREF | NTC bias reference |
| **52** | **RX** | UART in (from host). Pull up to CVDD on the base device |
| **53** | **TX** | UART out (to host) |
| 54–61 | GPIO8…GPIO1 | NTC / aux inputs |
| **62** | **NFAULT** | Fault output, active low |
| 63 / 64 | BBN / BBP | Bus-bar measurement |

## UART

- **1 Mbps**, 8N1, idle high, **half duplex** (250 kbps is available in comm debug mode).
- Optional two stop bits for responses (`DEV_CONF[TWO_STOP_EN]`).

### Pings on RX (host holds RX low)

| Low time | Meaning |
|---|---|
| ~250 µs | SLEEP → ACTIVE |
| ≥ 2 ms | WAKE |
| ~7 ms | SHUTDOWN |
| ~36 ms | HW_RESET |

A logic analyser will show these as UART framing errors or breaks. Classify them by pulse width.

## Frame format

```
Command:  INIT | [DEV ADR] | REG ADR hi | REG ADR lo | DATA … | CRC lo | CRC hi
Response: INIT | DEV ADR   | REG ADR hi | REG ADR lo | DATA … | CRC lo | CRC hi
```

The device address byte is **only present in single-device commands**. It is always present in responses.

### Command INIT byte

| Bits | Field | Values |
|---|---|---|
| 7 | FRAME_TYPE | 1 = command |
| 6:4 | REQ_TYPE | 000 single read, 001 single write, 010 stack read, 011 stack write, 100 broadcast read, 101 broadcast write, 110 broadcast write reverse |
| 3 | reserved | |
| 2:0 | DATA_SIZE | Number of data bytes − 1 (1–8 bytes) |

For read commands, the single data byte is the number of register bytes to read, minus 1 (0x00 = 1 byte, 0x7F = 128 bytes).

Common INIT values:

| INIT | Command |
|---|---|
| 0x80 | Single device read |
| 0x90–0x97 | Single device write, 1–8 bytes |
| 0xA0 | Stack read |
| 0xB0–0xB7 | Stack write, 1–8 bytes |
| 0xC0 | Broadcast read |
| 0xD0–0xD7 | Broadcast write, 1–8 bytes |
| 0xE0–0xE7 | Broadcast write reverse, 1–8 bytes |

### Response INIT byte

| Bits | Field | Values |
|---|---|---|
| 7 | FRAME_TYPE | 0 = response |
| 6:0 | RESPONSE_BYTE | Number of data bytes − 1 (up to 128) |

### CRC

- CRC-16-IBM (x¹⁶ + x¹⁵ + x² + 1), initialised to 0xFFFF, bit-reflected. This is the same algorithm as CRC-16/MODBUS (reflected poly 0xA001).
- Computed over the whole frame. **Transmitted low byte first.**
- Running the CRC over a whole frame including its CRC gives 0x0000 when the frame is valid.
- Datasheet example: `80 00 02 0F 0B` → CRC bytes `C0 29`. See [tools/bq_crc.py](../tools/bq_crc.py).

## Start-up and auto-addressing (DIR_SEL = 0)

1. **WAKE** ping on the base device's RX. Then write `CONTROL1[SEND_WAKE] = 1` to the base device (single write, address 0), which sends the WAKE tone up the stack.
2. **Dummy write** to synchronise the daisy-chain DLLs (required after any reset): broadcast write 0x00 to `OTP_ECC_DATAIN1…8` (0x343–0x34A).
3. **Enable auto-addressing:** broadcast write `CONTROL1[ADDR_WR] = 1`.
4. **Assign addresses:** broadcast write `DIR0_ADDR` = 0x00, then 0x01, 0x02, … once per device. For the SP51 that is 0x00–0x09.
5. **Set stack roles:**
   - Broadcast write `COMM_CTRL`: `STACK_DEV = 1`, `TOP_STACK = 0`.
   - Single write to the base (address 0): `STACK_DEV = 0`.
   - Single write to the top of stack (address 9): `TOP_STACK = 1`.
6. **Dummy read** (broadcast read `OTP_ECC_DATAIN1…8`) to synchronise the read-direction DLLs. Some responses may be missing.

Stack reads are answered by stack devices only, **top of stack first**. Broadcast reads include the base device.

## Key registers

### OTP-shadowed configuration (NVM)

| Addr | Name | Notes |
|---|---|---|
| 0x0000 | DIR0_ADDR_OTP | |
| 0x0001 | DIR1_ADDR_OTP | |
| 0x0002 | DEV_CONF | Reset value 0x54. NFAULT enable, fault tone, two stop bits, etc. |
| 0x0003 | ACTIVE_CELL | `NUM_CELL[3:0]` = cells − 6. **12S → 0x06**, 16S → 0x0A |
| 0x0005–0x0006 | BBVC_POSN1/2 | Bus-bar position |
| 0x0007–0x0008 | ADC_CONF1/2 | |
| 0x0009 | OV_THRESH | |
| 0x000A | UV_THRESH | |
| 0x000B | OTUT_THRESH | |
| 0x000C–0x000D | UV_DISABLE1/2 | |
| 0x000E–0x0011 | GPIO_CONF1…4 | |
| 0x0016–0x0017 | FAULT_MSK1/2 | |
| 0x0019 | COMM_TIMEOUT_CONF | |
| 0x0036–0x0037 | CUST_CRC | |

### Control (RW)

| Addr | Name | Notes |
|---|---|---|
| 0x0306 | DIR0_ADDR | Device address (DIR_SEL = 0) |
| 0x0307 | DIR1_ADDR | Device address (DIR_SEL = 1) |
| 0x0308 | COMM_CTRL | `STACK_DEV`, `TOP_STACK` |
| 0x0309 | CONTROL1 | `DIR_SEL`, `SEND_SHUTDOWN`, `SEND_WAKE`, `SEND_SLPTOACT`, `GOTO_SHUTDOWN`, `GOTO_SLEEP`, `SOFT_RESET`, `ADDR_WR` |
| 0x030A | CONTROL2 | |
| 0x030D | ADC_CTRL1 | `MAIN_GO`, `MAIN_MODE`, LPF enables |
| 0x030E–0x030F | ADC_CTRL2/3 | AUX ADC |
| 0x0310 | REG_INT_RSVD | **Do not write** |
| 0x0318–0x0327 | CB_CELL16_CTRL … CB_CELL1_CTRL | Balance timer per cell |
| 0x032A | VCB_DONE_THRESH | |
| 0x032B | OTCB_THRESH | |
| 0x032C | OVUV_CTRL | |
| 0x032D | OTUT_CTRL | |
| 0x032E–0x0330 | BAL_CTRL1/2/3 | `BAL_GO`, auto-balance, duty, fault stop |
| 0x0331–0x0332 | FAULT_RST1/2 | |
| 0x0343–0x034B | OTP_ECC_DATAIN1…9 | Used for DLL sync dummy writes and reads |

### Status and results (R)

| Addr | Name | Notes |
|---|---|---|
| 0x0500 | PARTID | |
| 0x0E00 | DEV_REVID | Check this: some registers differ between silicon revisions |
| 0x0527–0x0528 | ADC_STAT1/2 | |
| 0x052C | DEV_STAT | |
| 0x052D | FAULT_SUMMARY | |
| 0x0530–0x0532 | FAULT_COMM1…3 | |
| 0x053C–0x053D | FAULT_OV1/2 | |
| 0x053E–0x053F | FAULT_UV1/2 | |
| 0x0540 / 0x0541 | FAULT_OT / FAULT_UT | |
| 0x0556–0x0557 | CB_COMPLETE1/2 | |
| 0x0568 … 0x0586 | VCELL16_HI … VCELL1_HI | 2 bytes each, HI byte first, two's complement. 12S uses VCELL12 (0x0570) to VCELL1 |
| 0x0588 | BUSBAR_HI/LO | |
| 0x058C | TSREF_HI/LO | |
| 0x058E … 0x059C | GPIO1_HI … GPIO8_HI | 2 bytes each |
| 0x05AE / 0x05B0 | DIETEMP1 / DIETEMP2 | |
| 0x05B6 | AUX_BAT_HI/LO | |

## ADC scaling

| Measurement | LSB |
|---|---|
| Cell voltage (main and AUX) | 190.73 µV |
| Bus bar (BBP–BBN) | 30.52 µV |
| GPIO | 152.59 µV |
| TSREF | 169.54 µV |
| Die temperature | 0.025 °C (0x0000 = 0 °C) |
| BAT (AUX) | 3.05 mV |

A 12-cell stack read is 24 bytes: stack-read `VCELL12_HI` (0x0570), length 24.
