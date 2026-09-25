# BMW SP51 BQ79616 BMS

Reverse engineering the BMW SP51 high-voltage battery's TI BQ79616-based cell monitoring, and building a new
STM32-based BMS master to run it. The new master talks to a [ZombieVerter VCU](https://github.com/damienmaguire/Stm32-vcu)
using the SimpBMS / Victron CAN protocol.

> **⚠ High voltage.** A fully assembled SP51 pack is around 450 V DC. Read [docs/06-sniffing-guide.md](docs/06-sniffing-guide.md)
> before connecting any test equipment. Nothing in this repo is a substitute for proper HV training, PPE and isolation.

## Status

| Area | State |
|---|---|
| Pack topology | Known: 9 modules × 12S = 108S |
| Original BMW master (SME) | In hand. BQ79616 base device on a daughter board, UART isolated by an ISO7721-Q1 |
| Daughter-board header pinout | **Mostly mapped**: UART, host supply, isolated supply and chain pair known. See [docs/05](docs/05-sme-daughterboard.md) |
| Daughter-board function | Pack monitor: 2 × INA240A1-Q1 current channels on BQ79616 VC1/VC2, LM2904B front end, HV/insulation network, 74HC595/HEF4021B I/O |
| UART to base BQ79616 | **Working** on the bench (TTL-232R-5V cable, [tools/bq_uart.py](tools/bq_uart.py)). See [docs/09](docs/09-uart-bench-setup.md) |
| BMW configuration | Not in OTP (factory defaults), so it's written at runtime and needs to be sniffed from the SME |
| Bus captures | Not started |
| New master hardware | Architecture drafted |
| Firmware | Not started |

## Daughter-board header (summary)

Viewed from the component side, header at the bottom edge. Row A = surface-mount row, row B = through-hole row.
Columns 2 and 9 are unpopulated.

```
   A1 │ ·  │ A3 A4 A5 [A6 GND] [A7 TX] [A8 VCC] │ ·  │ [A10 ISO-GND]
   B1 │ ·  │ B3 B4 B5  B6      [B7 RX]  B8      │ ·  │ [B10 ISO-SUPPLY 9–40 V]
 chain│gap │          host / LV domain          │gap │  isolated (BQ) domain
```

| Pin | Function |
|---|---|
| A1, B1 | Daisy-chain pair to the modules, via isolation transformer |
| A6 | Host GND (ISO7721 GND2) |
| A7 | Host UART TX → BQ79616 RX (ISO7721 INA) |
| B7 | Host UART RX ← BQ79616 TX (ISO7721 OUTB) |
| A8 | Host logic supply 2.25–5.5 V (ISO7721 VCC2) |
| A10 | Isolated GND. **Never link to A6** |
| B10 | Isolated supply: BQ79616 BAT (through ~30 Ω) and TPS7A6650-Q1 5 V LDO |
| A3–A5, B3–B6, B8 | Not yet mapped |

## Where we stopped / next steps

1. Check the right-hand INA240's REF1/REF2 pins (pins 7 and 3). Its output sits at 1.95 V, while the left one is at 2.50 V.
2. Trace BQ79616 VC4 and VC8–VC16 (LM2904B outputs, HV network) to give the upper channels firm meanings.
3. Map the remaining middle header pins (A3–A5, B3–B6, B8).
4. Check whether the chain is a ring (a second transformer-coupled pair?).
5. Sniff the SME's UART on A6/A7/B7 during start-up to capture BMW's runtime configuration.
6. Identify the remaining parts: ST DPAKs, Würth magnetic, rear power stage.

## Pack summary

| | |
|---|---|
| Pack | BMW SP51 |
| Modules | 9 × 12 cells in series |
| Cells | 108S |
| Voltage (NMC assumed) | ~324 V at 3.0 V/cell, ~400 V nominal, ~454 V at 4.2 V/cell |
| Cell monitors | 1 × BQ79616-Q1 per module (addresses 1–9) |
| Host bridge (BMW) | BQ79616-Q1 as base device (address 0) on the SME daughter board |
| Chain devices | 10 in total |

## Architecture (new master)

```
12V ─► protection / low-Iq supply / wake (KL15, charger)
        │
     STM32G474 ──UART or SPI──► base BQ79616 (BMW style)  or  BQ79600-Q1 bridge
        │                                   ║ isolated daisy chain (ring)
        │                                   ╚══► Module 1 … Module 9 (BQ79616, 12S each)
        ├─ CAN1: ZombieVerter (SimpBMS/Victron) + ISA IVT-S shunt
        ├─ CAN2: diagnostics / per-cell data
        ├─ "BMS OK" hardware interlock in series with contactor coil supply
        └─ FRAM (SOC, fault log), SWD, UART console
```

## Repository layout

| Path | Contents |
|---|---|
| [docs/01-project-plan.md](docs/01-project-plan.md) | Phased plan, from teardown to validation |
| [docs/02-pack-bmw-sp51.md](docs/02-pack-bmw-sp51.md) | What is known about the pack and the BMW SME |
| [docs/03-bq79616-reference.md](docs/03-bq79616-reference.md) | BQ79616 pinout, UART protocol, CRC, auto-addressing, key registers |
| [docs/04-bq79600-reference.md](docs/04-bq79600-reference.md) | BQ79600 bridge pinout and SPI/UART selection |
| [docs/05-sme-daughterboard.md](docs/05-sme-daughterboard.md) | SME daughter board: ISO7721 isolator and header pinout worksheet |
| [docs/06-sniffing-guide.md](docs/06-sniffing-guide.md) | Safe setup and what to capture from the original SME |
| [docs/07-zombieverter-can.md](docs/07-zombieverter-can.md) | SimpBMS/Victron CAN as ZombieVerter decodes it, and the gotchas |
| [docs/08-master-hardware.md](docs/08-master-hardware.md) | New master board design notes |
| [docs/09-uart-bench-setup.md](docs/09-uart-bench-setup.md) | Wiring and first session for talking to the daughter-board BQ79616 directly over UART |
| [datasheets/](datasheets/) | TI datasheets (see [datasheets/README.md](datasheets/README.md)) |
| [tools/](tools/) | `bq_crc.py` (CRC calculator), `bq_uart.py` (wake and read/write registers over a USB-UART adapter) |
| [captures/](captures/) | Logic-analyser captures from the SME |
| `hardware/`, `firmware/` | Master board design and firmware (to come) |
