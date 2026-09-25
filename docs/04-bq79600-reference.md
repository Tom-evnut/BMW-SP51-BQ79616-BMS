# BQ79600-Q1 quick reference

This is TI's dedicated SPI/UART-to-daisy-chain bridge. BMW's SME does **not** use it: the SME uses a BQ79616 as the
base device. It is documented here as an option for the new master.

Source: [SLUSDS1A](../datasheets/BQ79600-Q1_SLUSDS1A.pdf).

## Package

- 16-pin TSSOP (PW), about 5.1 × 6.6 mm including leads, 1.2 mm tall.
- 0.65 mm pitch. **No thermal pad.**
- Top marking: `BQ79600`.

## Pinout (top view)

```
  MCU side                            Daisy-chain side
           ┌────────── ● ──────────┐
    DVDD  1│                       │16  INH
  NFAULT  2│                       │15  BAT
     VIO  3│                       │14  CVDD
 MOSI/RX  4│       BQ79600         │13  COMHP ─┐ to bottom of stack
 MISO/TX  5│                       │12  COMHN ─┘
    SCLK  6│                       │11  COMLN ─┐ ring return
     nCS  7│                       │10  COMLP ─┘
nUART/SPI 8│ (SPI_RDY)             │ 9  GND
           └───────────────────────┘
```

## Interface selection

| Mode | Wiring |
|---|---|
| UART (1 Mbps) | SCLK, nCS and nUART/SPI tied to GND. RX and TX pulled up (10–100 kΩ) to VIO |
| SPI | nUART/SPI (SPI_RDY) pulled up to VIO and routed to an MCU GPIO. nCS pulled up, SCLK pulled down. **The host must wait for SPI_RDY** before each transaction |

## Support components (reference design)

| Pin | Component |
|---|---|
| DVDD | 0.22 µF (1.8 V) |
| CVDD | 0.22 µF (5 V) |
| BAT | 10 Ω series from 12 V, 0.1 µF to GND. 5.5–24 V with reverse wake, or a regulated 5 V without it |
| INH | 100 kΩ to GND and to the PMIC enable (reverse wake), or tied to BAT if not used |
| NFAULT | 100 kΩ pull-up to VIO |
| COM pins | Series 51 Ω / 1 kΩ, 100 pF to GND, PESD5V0L2BT ESD diode, 1:1 pulse transformer (TI recommends transformer isolation here), twisted pair |

## Differences from using a BQ79616 as the base device

- The bridge takes address 0 but has no cells.
- It supports reverse wake (INH) in ring configuration.
- SPI host interface.
- Smaller package, and it runs from 12 V (5.5–24 V) instead of the BQ79616's 9–80 V BAT range.
