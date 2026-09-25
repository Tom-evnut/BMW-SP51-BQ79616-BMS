# SME daughter board

The BMW SME carries a daughter board with:

- A **TI BQ79616-Q1**, used as the daisy-chain **base device** (UART host interface).
- A **TI ISO7721-Q1** digital isolator next to the header. Marking: `7721Q` / `47T` / `ARE JG4`.

## Identified components (from photos)

| Marking | Package | Part | Confidence | Role (hypothesis) |
|---|---|---|---|---|
| `BQ79616 46ATP6W G4` | HTQFP-64 | TI BQ79616-Q1 | Confirmed | Chain base device, plus pack-level measurements on its GPIO/ADC inputs |
| `7721Q 47T ARE JG4` | SOIC-8 | TI ISO7721-Q1 | Confirmed | Isolates the host UART (TX/RX) |
| `240A1Q` (×2) | SOIC-8 | TI INA240A1-Q1 current-sense amplifier (gain 20 V/V) | High | Pack current from a shunt, fed into the BQ79616 GPIO ADC |
| `HC595` | TSSOP-16 | 74HC595 serial-in / parallel-out shift register | High | Digital **outputs**, probably driven by the BQ79616 SPI controller |
| `HEF4021BT` | SOIC-16 | Nexperia HEF4021B parallel-in / serial-out shift register | High | Digital **inputs**, read by the BQ79616 SPI controller |
| `BYG23M` | SMA | Vishay BYG23M, ~1 kV-class rectifier | Medium (check rating) | HV network |
| `3303` | 1206 resistors | 330 kΩ | High | HV divider / insulation-measurement resistor strings |
| ST logo, DPAK (several, some under grey silicone) | DPAK | ST, unidentified | — | Likely HV MOSFETs switching the measurement network |
| onsemi `RXB BH-16`(?) | SOT-223 | Unidentified | — | Probably a regulator |
| Würth `20059 V1` | SMD magnetic | Würth, unidentified | — | Transformer or choke |
| `GF 820 EZR` (×3, rear) | Radial can | ~820 µF capacitor | Medium | Bulk capacitance for a switching supply |
| Beige 2-way connector | — | — | — | Unknown. The chain goes out through the header instead, so this may be shunt sense or a sensor |

### Interpretation

This looks like more than a UART bridge. It resembles a **pack monitor**, similar in function to TI's BQ79631-Q1:

- Current measured by INA240s from a shunt.
- HV voltage and/or insulation-resistance measurement using 330 kΩ strings, 1 kV diodes and HV MOSFETs.
- Switching and status handled by shift registers on the BQ79616's SPI controller.
  - BQ79616 GPIO4 (pin 58) = SS, GPIO5 (57) = MISO, GPIO6 (56) = MOSI, GPIO7 (55) = SCLK, enabled by
    `GPIO_CONF1[SPI_EN]`. Registers: `SPI_CONF` 0x34D, `SPI_EXE` 0x351.

**Consequence:** the BQ79616 side is very likely **referenced to the HV pack**. Only probe the header side of the ISO7721.
If this holds, the whole board could be reused as a pack monitor and chain bridge for the new master.

### Header layout (from photos, to confirm)

- 2-row, 20-way.
- One row lands on top-side pads (about 10 positions); the ISO7721 host-side traces run to this row.
- The other row is through-hole, with only **6 fitted: position 1, positions 4–7, position 10**.
- The 4 missing pins flank the central group of 4, which points to a creepage gap around those 4 pins. They may
  carry HV sense lines from the SME main board. Check each with an ohmmeter: readings in the MΩ range into the
  330 kΩ strings mean HV.

## ISO7721-Q1

- A dual-channel digital isolator, with one channel in each direction.
- `7721Q` = automotive (-Q1) version with outputs that **default high**. The "F" variant, with outputs defaulting low, is marked `7721FQ`.
- `47T` and `ARE JG4` are date and lot codes.
- Source: [SLLSEU1C](../datasheets/ISO7721-Q1_SLLSEU1C.pdf).

### Pinout, 8-pin SOIC (D or DWV), top view

```
 Side 1                        Side 2
 VCC1 1 ●──────┐   ┌──────── 8 VCC2
 OUTA 2 ◄──────┼───┼──────── 7 INA     Channel A: side 2 → side 1
  INB 3 ───────┼───┼───────► 6 OUTB    Channel B: side 1 → side 2
 GND1 4 ───────┘   └──────── 5 GND2
             isolation barrier
```

### Pinout, 16-pin wide SOIC (DW)

| Signal | 16-pin | 8-pin |
|---|---|---|
| GND1 | 1, 7 | 4 |
| VCC1 | 3 | 1 |
| OUTA | 4 | 2 |
| INB | 5 | 3 |
| OUTB | 12 | 6 |
| INA | 13 | 7 |
| VCC2 | 14 | 8 |
| GND2 | 9, 16 | 5 |
| NC | 2, 6, 8, 10, 11, 15 | — |

## What the isolator tells us

- The daughter board's BQ79616 is **galvanically isolated** from the SME's 12 V side, and its UART runs through the ISO7721.
- **Treat the BQ79616 side as potentially at HV potential** until you've traced where its BAT (pin 1) gets power.
  Connect test-equipment ground to the **header side only**.
- Both isolator channels carry the UART, so **NFAULT cannot pass through this part**. Look for a second isolator or
  optocoupler if NFAULT reaches the header.
- The BQ79616 side needs its own supply. Look for an isolated DC-DC (a transformer plus driver, or a module), or a feed
  from a module or the HV connector.

## Deriving the header pinout

1. With the board unpowered, beep the header pins against ISO7721 GND1 and GND2. The one that connects tells you which
   side faces the header.
2. Map TX and RX:

   | Header side is… | Host TX → BQ RX (pin 52) | Host RX ← BQ TX (pin 53) |
   |---|---|---|
   | Side 1 (pins 1–4) | Pin 3 INB → pin 6 OUTB | Pin 2 OUTA ← pin 7 INA |
   | Side 2 (pins 5–8) | Pin 7 INA → pin 2 OUTA | Pin 6 OUTB ← pin 3 INB |

3. On the BQ side, confirm the isolator output reaches BQ79616 **pin 52 (RX)** and the input comes from **pin 53 (TX)**,
   possibly through series resistors. The BQ-side VCC is probably fed from BQ79616 CVDD (pin 45, 5 V).
4. Identify the remaining header pins: host logic supply and GND, any isolated DC-DC supply, and any NFAULT or wake line.

## Header pinout worksheet

The header is **20-way with 4 pins missing** (16 populated). Missing pins in a header like this usually form a
**creepage/clearance gap** between two isolation domains. Expect the populated pins to split into:

- **LV / host side:** host logic supply, GND, host UART TX/RX, and possibly 12 V, wake and NFAULT.
- **BQ side (treat as HV until proven otherwise):** daisy-chain COMH/COML pairs (the chain connector may sit on the
  SME main board), BQ79616 BAT supply, and possibly bus-bar or voltage sense.

### Pin numbering convention

Use this until the connector's own pin-1 marking or part number is known. View the **component side** with the header
at the **bottom edge** of the board:

```
            (board centre / ISO7721 above)
   A1  A2  A3  A4  A5  A6  A7  A8  A9  A10   ← Row A: surface-mount pads, board side
   B1  B2  B3  B4  B5  B6  B7  B8  B9  B10   ← Row B: through-hole, board edge side
            (board edge below)
```

- Columns are numbered 1–10 from left to right in this view.
- **From the back of the board, everything is mirrored: column 1 is on the right.**
- Missing pins (from photos, to confirm): B2, B3, B8, B9.

### Procedure (unpowered, daughter board removed if possible)

1. Mark pin 1 and the numbering scheme. Record which 4 positions are missing.
2. For each populated pin, beep it against:
   - ISO7721 GND1 and GND2, VCC1 and VCC2, INA, INB, OUTA and OUTB.
   - BQ79616 pin 1 (BAT), 39 (AVSS), 40–43 (COMLP/COMLN/COMHN/COMHP), 62 (NFAULT) and 63/64 (BBN/BBP).
3. Anything that connects to the BQ side without passing through the ISO7721 is **BQ-side/HV-domain**. Check whether
   those pins sit together on the far side of the missing-pin gap.
4. For COM lines, note what sits between the BQ79616 pins and the header: capacitors, chokes or transformers.

### Confirmed so far

- **A1 + B1 = daisy-chain pair**, through **isolation transformer(s)** on the daughter board. This is most
  likely BQ79616 COMHP/COMHN, running up to module 1 via the SME main board.
  - The base-device end of the chain is **transformer-isolated**. The new master must match this: same or equivalent
    transformer, and keep the P/N polarity.
  - Still to find out:
    - Which BQ79616 pins (42/43 COMH or 40/41 COML) the transformer connects to.
    - The transformer's part number.
    - Whether a second transformer-coupled pair exists. If it does, that's the ring return; if not, it's a linear chain.
  - Don't sniff these lines. They carry TI's differential chain signalling, not UART. Sniff the host UART instead.

### Worksheet

Domain: **LV** = host side, **BQ** = BQ79616 / isolated side, **—** = pin missing.

| Pin | Populated | Domain | Net | Connects to | Voltage (powered) | Notes |
|---|---|---|---|---|---|---|
| A1 | Yes | Chain (transformer-isolated) | Daisy-chain pair (P/N to confirm) | Isolation transformer → BQ79616 COMH? (to confirm) | | |
| A2 | Yes |  |  |  | | |
| A3 | Yes |  |  |  | | |
| A4 | Yes |  |  |  | | |
| A5 | Yes |  |  |  | | |
| A6 | Yes |  |  |  | | |
| A7 | Yes |  |  |  | | |
| A8 | Yes |  |  |  | | |
| A9 | Yes |  |  |  | | |
| A10 | Yes |  |  |  | | |
| B1 | Yes | Chain (transformer-isolated) | Daisy-chain pair (P/N to confirm) | Isolation transformer → BQ79616 COMH? (to confirm) | | |
| B2 | No (to confirm) | — |  |  | | |
| B3 | No (to confirm) | — |  |  | | |
| B4 | Yes |  |  |  | | |
| B5 | Yes |  |  |  | | |
| B6 | Yes |  |  |  | | |
| B7 | Yes |  |  |  | | |
| B8 | No (to confirm) | — |  |  | | |
| B9 | No (to confirm) | — |  |  | | |
| B10 | Yes |  |  |  | | |

## Findings log

| Date | Finding |
|---|---|
| | BQ79616 found on daughter board, used as base device |
| | ISO7721-Q1 (`7721Q`) found next to the header |
| | Header is 20-way with 4 pins missing, which is likely an isolation (creepage) gap |
| | A1 + B1 (left column) go through isolation transformers: this is the daisy-chain pair to the modules |
| | Photos: INA240A1-Q1 ×2, 74HC595, HEF4021B and a HV network (BYG23M, 330 kΩ strings, ST DPAKs) point to a pack-monitor function |
