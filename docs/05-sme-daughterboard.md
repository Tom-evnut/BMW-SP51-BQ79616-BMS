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
| `46 PA1Q` (read as `PA10`), rear | HVSSOP-8 (DGN) | TI **TPS7A6650-Q1**, 5.0 V / 150 mA LDO, 4–40 V input, power-good output | High (TI marking lookup: PA1Q) | 5 V rail for the isolated domain, fed from header B10 |
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

- 2 rows of 10: row A on top-side surface-mount pads, row B through-hole. See the pin numbering convention below.
- Columns 2 and 9 are unpopulated (A2, B2, A9, B9), forming gaps around column 1 and column 10.

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
- **Unpopulated (confirmed): A2, B2, A9, B9.** Columns 2 and 9 are completely empty, which splits the header into
  three groups:
  - **Column 1 (A1, B1):** daisy-chain pair, transformer-isolated.
  - **Columns 3–8 (12 pins):** probably host side (ISO7721 UART, supply, GND) and anything else.
  - **Column 10 (A10, B10):** the **isolated (BQ79616-side) domain**. A10 = BQ-side GND (ISO7721 GND1), confirmed.
    The empty column 9 is the creepage gap between the host domain (columns 3–8) and the isolated domain.

### Procedure (unpowered, daughter board removed if possible)

1. Mark pin 1 and the numbering scheme. Record which 4 positions are missing.
2. For each populated pin, beep it against:
   - ISO7721 GND1 and GND2, VCC1 and VCC2, INA, INB, OUTA and OUTB.
   - BQ79616 pin 1 (BAT), 39 (AVSS), 40–43 (COMLP/COMLN/COMHN/COMHP), 62 (NFAULT) and 63/64 (BBN/BBP).
3. Anything that connects to the BQ side without passing through the ISO7721 is **BQ-side/HV-domain**. Check whether
   those pins sit together on the far side of the missing-pin gap.
4. For COM lines, note what sits between the BQ79616 pins and the header: capacitors, chokes or transformers.

### ISO7721 → header mapping

Fill this in with the board unpowered, using resistance mode (series resistors won't beep in continuity mode).

| ISO7721 pin | Name | Side (header / BQ) | Header pin(s) | Resistance | Via (series R, etc.) | Notes |
|---|---|---|---|---|---|---|
| 1 | VCC1 | BQ | — (via LDO from B10) | | | Powered from the TPS7A6650-Q1 5 V output (large SMD capacitors on the rail), **not** BQ79616 CVDD (confirmed) |
| 2 | OUTA | BQ | — | | | Expected → BQ79616 RX (pin 52) |
| 3 | INB | BQ | — | | | Expected ← BQ79616 TX (pin 53) |
| 4 | GND1 | BQ | **A10** | | | BQ-side (isolated) ground, **brought out on the header** (confirmed) |
| 5 | GND2 | Header | **A6** | | | Header-side GND (confirmed) |
| 6 | OUTB | Header | **B7** | | | **Host RX** ← BQ TX (confirmed) |
| 7 | INA | Header | **A7** | | | **Host TX** → BQ RX (confirmed) |
| 8 | VCC2 | Header | **A8** | | | Host logic supply (confirmed; voltage to measure) |

Isolation check: resistance from the BQ-side GND (ISO7721 pin 4 / A10) to every header pin **except column 10**
should read open (> 10 MΩ). This includes A1/B1, which go through a transformer. In particular, **A6 to A10 must be
open**.

### Base BQ79616: cell-input usage

The base BQ79616 has no cells attached, so BMW has wired its VC and CB inputs to other signals. In captures, **device
0's VCELL readings are pack-level measurements, not cell voltages**. This mapping says what each one measures.

Pin numbering confirmed as standard: anticlockwise from the dot, pin 1 = BAT. Checked by pin 46 (CVSS) and pin 34
(CB0) both reading 0 Ω to A10.

| VC input | Pin | Connects to | CB input | Connects to |
|---|---|---|---|---|
| VC16 | 3 |  | CB16 (pin 2) |  |
| VC15 | 5 |  | CB15 (pin 4) |  |
| VC14 | 7 | **5 V rail (0 Ω)** | CB14 (pin 6) |  |
| VC13 | 9 |  | CB13 (pin 8) |  |
| VC12 | 11 |  | CB12 (pin 10) |  |
| VC11 | 13 | **5 V rail (0 Ω)** | CB11 (pin 12) |  |
| VC10 | 15 |  | CB10 (pin 14) |  |
| VC9 | 17 |  | CB9 (pin 16) |  |
| VC8 | 19 |  | CB8 (pin 18) | **A10 / GND (0 Ω)** |
| VC7 | 21 |  | CB7 (pin 20) | **A10 / GND (0 Ω)** |
| VC6 | 23 |  | CB6 (pin 22) | **A10 / GND (0 Ω)** |
| VC5 | 25 |  | CB5 (pin 24) | **A10 / GND (0 Ω)** |
| VC4 | 27 |  | CB4 (pin 26) | **A10 / GND (0 Ω)** |
| VC3 | 29 |  | CB3 (pin 28) | **A10 / GND (0 Ω)** |
| VC2 | 31 |  | CB2 (pin 30) | **A10 / GND (0 Ω)** |
| VC1 | 33 |  | CB1 (pin 32) | **A10 / GND (0 Ω)** |
| VC0 | 35 |  | CB0 (pin 34) | **A10 / GND (0 Ω)** |

Expect BMW to disable the undervoltage comparators on these channels (`UV_DISABLE1/2`, 0x000C–0x000D); look for those writes in the captures.

Still to record: what each remaining VC and CB pin connects to (5 V rail, A10, INA240 output, HV divider, a
resistor/capacitor filter), and where **BAT (pin 1)** is fed from.

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
| A2 | No | — | | | | Unpopulated (confirmed) |
| A3 | Yes |  |  |  | | |
| A4 | Yes |  |  |  | | |
| A5 | Yes |  |  |  | | |
| A6 | Yes | LV / host | GND (host side) | ISO7721 pin 5 (GND2) | 0 V | Confirmed |
| A7 | Yes | LV / host | Host UART TX (→ BQ79616 RX) | ISO7721 pin 7 (INA) | Idle high | Confirmed. Sniff channel: host → BMS chain |
| A8 | Yes | LV / host | Host logic supply (ISO7721 VCC2) | ISO7721 pin 8 (VCC2) | 3.3 V or 5 V? (measure) | Confirmed. Supplied by the SME main board |
| A9 | No | — | | | | Unpopulated (confirmed) |
| A10 | Yes | **Isolated / BQ side** | BQ-side GND (ISO7721 GND1) | ISO7721 pin 4 (GND1) | Reference for the isolated domain | Confirmed. **Never connect to A6 or the analyser GND** |
| B1 | Yes | Chain (transformer-isolated) | Daisy-chain pair (P/N to confirm) | Isolation transformer → BQ79616 COMH? (to confirm) | | |
| B2 | No | — | | | | Unpopulated (confirmed) |
| B3 | Yes | | | | | |
| B4 | Yes |  |  |  | | |
| B5 | Yes |  |  |  | | |
| B6 | Yes |  |  |  | | |
| B7 | Yes | LV / host | Host UART RX (← BQ79616 TX) | ISO7721 pin 6 (OUTB) | Idle high | Confirmed. Sniff channel: BMS chain → host |
| B8 | Yes | | | | | |
| B9 | No | — | | | | Unpopulated (confirmed) |
| B10 | Yes | **Isolated / BQ side** | **Isolated-domain supply input** (return = A10) | TPS7A6650-Q1 pin 1 (VIN) **and** pin 2 (EN), directly (confirmed) | Unpowered: **1.2 kΩ to A10, same both polarities** | EN tied to VIN, so the LDO runs whenever B10 is powered. Check for a feed to BQ79616 BAT (pin 1). Measure the voltage powered (DMM only) |

## Findings log

| Date | Finding |
|---|---|
| | BQ79616 found on daughter board, used as base device |
| | ISO7721-Q1 (`7721Q`) found next to the header |
| | Header is 20-way with 4 pins missing, which is likely an isolation (creepage) gap |
| | CB1–CB8 (even pins 18–32) are tied directly to A10 / GND, as is CB0 |
| | Standard BQ79616 pin numbering confirmed (pins 46 CVSS and 34 CB0 = A10). VC14 (pin 7) and VC11 (pin 13) are tied to the 5 V rail (0 Ω) |
| | The 5 V LDO rail also feeds the HEF4021B. It connects to the BQ79616 too, pin not yet identified (candidates: 45 CVDD, 51 TSREF, 52 RX pull-up, 55–58 GPIO pull-ups, 62 NFAULT pull-up) |
| | TPS7A6650-Q1 5 V output (large SMD capacitors) feeds ISO7721 pin 1 (VCC1): the BQ side of the isolator runs at 5 V |
| | B10 goes directly to TPS7A6650-Q1 pins 1 (VIN) and 2 (EN): B10/A10 is the isolated domain's power input from the SME main board |
| | B10 to A10 = 1.2 kΩ unpowered, the same in both polarities (resistive path; diodes may not conduct at the meter's test voltage) |
| | B10 connects to the rear-side TI `46 PA1Q` = TPS7A6650-Q1 5 V LDO: B10 is the isolated domain's supply input |
| | A10 = ISO7721 pin 4 (GND1): the isolated BQ-side ground is on the header, behind the column-9 gap |
| | A8 = ISO7721 pin 8 (VCC2): host logic supply from the SME |
| | B7 = ISO7721 pin 6 (OUTB): host RX |
| | A7 = ISO7721 pin 7 (INA): host TX |
| | A6 = ISO7721 pin 5 (GND2): the header faces ISO7721 side 2 (pins 5–8) |
| | A2, B2, A9, B9 unpopulated: columns 2 and 9 are empty, so columns 1 and 10 are separated from the middle |
| | A1 + B1 (left column) go through isolation transformers: this is the daisy-chain pair to the modules |
| | Photos: INA240A1-Q1 ×2, 74HC595, HEF4021B and a HV network (BYG23M, 330 kΩ strings, ST DPAKs) point to a pack-monitor function |
