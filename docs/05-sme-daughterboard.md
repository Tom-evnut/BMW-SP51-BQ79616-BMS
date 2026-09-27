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
| `46K` / `2904B` (read as `29048`) / TI logo (×2, upper-left of BQ79616) | 8-pin TSSOP/VSSOP | TI **LM2904B** dual op-amp, 36 V, 1.2 MHz. If a Q, A or T follows the B, it's the automotive LM2904B-Q1 | High (TI marking lookup: 2904B) | Analog front end: buffering or scaling the shunt/HV signals into the BQ79616's VC/GPIO inputs (4 channels) |
| `BYG23M` | SMA | Vishay BYG23M, ~1 kV-class rectifier | Medium (check rating) | HV network |
| `3303` | 1206 resistors | 330 kΩ | High | HV divider / insulation-measurement resistor strings |
| ST logo, DPAK (several, some under grey silicone) | DPAK | ST, unidentified | — | Likely HV MOSFETs switching the measurement network |
| onsemi `RXB BH-16` | SOT-223 | onsemi **BCP56-16** NPN, 80 V, 1 A, hFE 100–250 (`BH-16` = BCP56-16T1G/T3G marking) | High | BQ79616 external NPN pre-regulator (BAT → LDOIN). It's the transistor closest to the HEF4021 (confirmed in use) |
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

- 2 rows of 10, **both surface-mount**. Row A's tails exit towards the board centre (ISO7721 side) and row B's towards
  the board edge. The holes seen below the connector in the photos are vias, not connector pins.
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

### Connector: IRISO 10120 series (Z-Move floating board-to-board)

The daughter-board header is an **IRISO 10120S socket**, apparently a derivative of **IMSA-10120S-20Y915**, possibly a
BMW-specific version with columns 2 and 9 unpopulated. The **mating plug (IMSA-10120B-20…) sits on the SME main
board**, and on a replacement master or bench breakout.

| IMSA-10120S-20Y915 | Value |
|---|---|
| Type | Socket (female), vertical top entry, SMT, 20 positions, 2.0 mm pitch |
| Size | 26.5 × 5.5 mm footprint (as listed), **12.35 mm tall** |
| Contacts | Gold, 0.1 µm min |
| Rating | 125 V, 1 A, 50 mΩ max |
| Mates with | IMSA-10120B-20… plug (e.g. Y911 / Z02–Z03: 7.95 mm tall; Y913: 8.95 mm tall) |
| **Measured on the SME** | **Boards ~19.2 mm apart when mated** |

**Which plug the SME uses (derived):** the series' mated-height range tops out at 20.0 mm. With the 12.35 mm socket:

| Plug | Socket + plug | Nominal mated height (1.3 mm engagement) |
|---|---|---|
| 8.95 mm (Y913) | 21.30 mm | 20.0 mm (the series maximum) |
| **7.95 mm (Y911 / Z02–Z03)** | 20.30 mm | **19.0 mm**, which matches the measured 19.2 mm |

So the SME main board almost certainly has the **7.95 mm IMSA-10120B-20 plug**, which is the part on drawing 110-410120-847.
The +0.2 mm difference is within the connector's Z float (±0.7 mm) and measurement tolerance. The 1.3 mm engagement
is inferred from the series' 20.0 mm maximum; confirm it against IRISO's socket drawing if possible.

Series data from IRISO's 10120 series sheet, the product pages and specification IS-10120-003:

| Parameter | Value |
|---|---|
| Type | Floating ("Z-Move") board-to-board stacking connector, straight, SMT |
| Pitch / rows | 2.00 mm, 2 rows (20-way = 2 × 10) |
| Parts | **IMSA-10120B-…** = plug (male, centre-strip contacts). **IMSA-10120S-…** = socket (female) |
| Rating | 1 A per contact, 125 V AC/DC, 500 V AC withstand, −40 to +125 °C |
| Floating range | X/Y ±0.65 mm, Z ±0.7 mm (spec IS-10120-003; the brochure says ±0.8 mm) |
| Mated height | 11.0–20.0 mm, depending on the plug/socket variant pair (plugs Z02–Z05, sockets Z10/Z11 or Z18/Z19; odd numbers = without locating boss) |

- The **125 V rating** is well below the pack voltage. This supports the empty columns 2 and 9 being a **creepage gap**
  between the host domain and the isolated domain, which is HV-referenced in the car.
- **IRISO does not number the contacts.** Drawing 110-410120-847 (IMSA-10120B-**Z**-GFN4, Z02/Z03) has no pin numbers
  or pin-1 mark; the only markings are the `IRS` logo, a `*` mark on one long side of the insulator and a `B**` lot
  code. **The A/B convention below is the project's official numbering.**

> The original IRISO drawing 110-410120-847 and specification IS-10120-003 are proprietary, so they are not in this
> repo. They're kept in the owner's private companion repository.

#### Mating plug: IMSA-10120B-20Z02/Z03-GFN4 (drawing 110-410120-847 rev 5)

This is the part the SME main board, a replacement master or a bench breakout needs in order to mate with the daughter board.

| Item | Value |
|---|---|
| Plug height | 7.95 mm |
| Dimensions (20-way) | A (first to last contact) = 18.0 mm, B (boss to boss) = 25.7 mm, C (body length) = 28.7 mm, D (hold-downs) = 26.85 mm; width (13) mm |
| Terminals | Both rows SMT, 2.0 mm pitch, on opposite long sides of the body |
| Recommended PCB pads | 1.0 × 2.6 mm signal pads at 2.0 mm pitch; 2.2 mm wide hold-down pads; Ø1.2 (+0.1/0) mm boss holes (Z02 = with boss, Z03 = without); row pads 14 mm outside-to-outside |
| Materials | PA9T black insulator; Corson bronze contacts; Au 0.12 µm min on the contact area, Ni underplate; Sn 2–7 µm on the tails |
| Coplanarity | 0.1 mm max |

#### Product specification IS-10120-003 (10120S/B series)

| Item | Value |
|---|---|
| Parts covered | Socket IMSA-10120S-**(Z10–Z19)-GFN4 (back-surface-reflow capable); plug IMSA-10120B-**(Z02–Z05)-GFN4 |
| Rating | 125 V AC/DC (IEC 60664-1, material group I, pollution degree 2), 1 A per contact, −40 to +125 °C |
| Contact resistance | 50 mΩ max, initial and after every test |
| Insulation resistance | 100 MΩ min at 250 V DC |
| Dielectric withstand | 500 V AC for 60 s |
| Temperature rise | ≤ 30 °C at 1 A |
| Leakage current | 50 µA max at 14 V DC |
| Insertion / extraction force | ≤ 2.0 N / ≥ 0.1 N per terminal |
| Durability | 30 mating cycles |
| Shock / vibration | 490 m/s², 11 ms; 10–2000 Hz, 98 m/s², 2 h per axis; Z-move ±20 µm × 10⁷ cycles, no discontinuity > 1 µs |
| Reflow | Peak 260 °C max; hand soldering 350 °C, 3 s |
| Handling | Mate straight (≤ 1° mating angle, ≤ 3° guiding angle); don't hold the boards by the connector alone, fix them with screws near the connector |

- The socket is designed for the plug's centre-strip contacts, so generic 2 mm pins or jumper leads won't mate
  reliably. For bench work, use a matching **IMSA-10120B-20…** plug on a small breakout board.
- To pick the right plug variant (7.95 or 8.95 mm) for a replacement master, measure the stack height between the SME main board and the
  daughter board.

### Pin numbering convention

Use this until the connector's own pin-1 marking or part number is known. View the **component side** with the header
at the **bottom edge** of the board:

```
            (board centre / ISO7721 above)
   A1  A2  A3  A4  A5  A6  A7  A8  A9  A10   ← Row A: tails towards the board centre / ISO7721
   B1  B2  B3  B4  B5  B6  B7  B8  B9  B10   ← Row B: tails towards the board edge
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

### INA240A1-Q1 current-sense amplifiers (×2)

SOIC-8 pinout (datasheet SBOS808E):

| Pin | Name | Pin | Name |
|---|---|---|---|
| 1 | IN− (load side of shunt) | 8 | IN+ (supply side of shunt) |
| 2 | GND | 7 | REF1 |
| 3 | REF2 | 6 | VS (2.7–5.5 V) |
| 4 | NC | 5 | OUT |

| | INA240 #1, left (`AEDJ`) | INA240 #2, right (`AEDE`) |
|---|---|---|
| VS (6) | 5 V rail (confirmed) | 5 V rail (confirmed) |
| GND (2) | A10 (confirmed) | A10 (confirmed) |
| IN+ (8) / IN− (1) | ? (trace to the shunt connection) | ? |
| REF1 (7) / REF2 (3) | ? (GND, 5 V, or split for 2.5 V bidirectional mid-point) | ? |
| OUT (5) | **BQ79616 pin 33 = VC1** (confirmed) | **BQ79616 pin 31 = VC2** (confirmed) |

The INA240 input common-mode range is −4 V to 80 V **relative to its GND (A10)**. The shunt must therefore sit close to
the isolated ground's potential. This suggests the **isolated domain is referenced to pack negative (HV−)**, with a
shunt in the HV− path.

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
| VC2 | 31 | **INA240 #2 (right) OUT** | CB2 (pin 30) | **A10 / GND (0 Ω)** |
| VC1 | 33 | **INA240 #1 (left) OUT** | CB1 (pin 32) | **A10 / GND (0 Ω)** |
| VC0 | 35 | **A10 / GND (0 Ω)** | CB0 (pin 34) | **A10 / GND (0 Ω)** |

Expect BMW to disable the undervoltage comparators on these channels (`UV_DISABLE1/2`, 0x000C–0x000D); look for those writes in the captures.

**The pack current channels land on device 0 "cells" 1 and 2.** The BQ79616 measures differences between adjacent VC pins:

| Device 0 reading | Register | Equals | Meaning |
|---|---|---|---|
| Cell 1 | `VCELL1_HI/LO` 0x0586 | VC1 − VC0 | INA240 #1 (left) output (VC0 at GND, confirmed) |
| Cell 2 | `VCELL2_HI/LO` 0x0584 | VC2 − VC1 | INA240 #2 output **minus** INA240 #1 output |
| Cell 1 + cell 2 | — | VC2 − VC0 | INA240 #2 (right) output |

Cell 2 can go negative; the results are two's complement. If both INA240s measure the same shunt, cell 2 is close to
zero and acts as a plausibility check between the two channels.

Still to record: what each remaining VC and CB pin connects to (5 V rail, A10, INA240 output, HV divider, a
resistor/capacitor filter), and the BQ79616's external NPN pre-regulator (BAT → collector, NPNB pin 48 → base, LDOIN pin 47 → emitter). This is the onsemi BCP56-16 (SOT-223) closest to the HEF4021B (confirmed).

BAT (pin 1) is fed from header **B10 through about 30 Ω** (confirmed).

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
| B10 | Yes | **Isolated / BQ side** | **Isolated-domain supply input** (return = A10) | TPS7A6650-Q1 pin 1 (VIN) **and** pin 2 (EN), directly (confirmed) | Unpowered: **1.2 kΩ to A10, same both polarities** | EN tied to VIN, so the LDO runs whenever B10 is powered. **Also feeds BQ79616 BAT (pin 1) through about 30 Ω**, so the supply must be 9–40 V. Measure the voltage powered (DMM only) |

## Findings log

| Date | Finding |
|---|---|
| | BQ79616 found on daughter board, used as base device |
| | ISO7721-Q1 (`7721Q`) found next to the header |
| | Header is 20-way with 4 pins missing, which is likely an isolation (creepage) gap |
| | The BQ79616's NPN pre-regulator is the SOT-223 next to the HEF4021B, marked `BH-16` = onsemi BCP56-16 |
| | BQ79616 BAT (pin 1) reads about 30 Ω to B10: the isolated supply powers the BQ79616 directly, so it must be 9–40 V (probably about 12 V) |
| | CB1–CB8 (even pins 18–32) are tied directly to A10 / GND, as is CB0 |
| | Standard BQ79616 pin numbering confirmed (pins 46 CVSS and 34 CB0 = A10). VC14 (pin 7) and VC11 (pin 13) are tied to the 5 V rail (0 Ω) |
| | Both INA240A1-Q1s: VS on the 5 V rail, GND on A10 |
| | BQ79616 pins 34 (CB0), 35 (VC0) and 36 (REFHM) are tied to GND (A10), as expected |
| | Left INA240 (#1) OUT (pin 5) → BQ79616 pin 33 (VC1) |
| | Right INA240 (#2) OUT (pin 5) → BQ79616 pin 31 (VC2): current is measured on device 0 cell channel 2 |
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
| | Header identified as IRISO 10120 series (2.0 mm pitch Z-Move floating board-to-board, 125 V rating): a socket derived from **IMSA-10120S-20Y915** (12.35 mm tall). The mating plug IMSA-10120B-20 is on the SME main board |
| | A2, B2, A9, B9 unpopulated: columns 2 and 9 are empty, so columns 1 and 10 are separated from the middle |
| | A1 + B1 (left column) go through isolation transformers: this is the daisy-chain pair to the modules |
| | Photos: INA240A1-Q1 ×2, 74HC595, HEF4021B and a HV network (BYG23M, 330 kΩ strings, ST DPAKs) point to a pack-monitor function |
