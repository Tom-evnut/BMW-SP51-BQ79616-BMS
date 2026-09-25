# SME daughter board

The BMW SME carries a daughter board with:

- A **TI BQ79616-Q1**, used as the daisy-chain **base device** (UART host interface).
- A **TI ISO7721-Q1** digital isolator next to the header. Marking: `7721Q` / `47T` / `ARE JG4`.

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

Fill this in as it's traced.

| Header pin | Net | Connects to | Voltage (powered) | Notes |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |

## Findings log

| Date | Finding |
|---|---|
| | BQ79616 found on daughter board, used as base device |
| | ISO7721-Q1 (`7721Q`) found next to the header |
