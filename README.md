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
| Daughter-board header pinout | **In progress**, see [docs/05-sme-daughterboard.md](docs/05-sme-daughterboard.md) |
| Bus captures | Not started |
| New master hardware | Architecture drafted |
| Firmware | Not started |

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
