# BMW SP51 pack

## Known facts

| Item | Value | Source |
|---|---|---|
| Modules | 9 | Observed |
| Cells per module | 12 in series | Observed |
| Pack configuration | 108S | Derived |
| Cell monitor | TI BQ79616-Q1, assumed one per module | Observed / to confirm per module |
| BMW master (SME) | In hand | Observed |
| SME host bridge | BQ79616-Q1 used as a **base device**, on a daughter board | Observed |
| Daughter-board UART isolation | TI ISO7721-Q1 (marking `7721Q`) | Observed |

## Derived numbers (NMC chemistry assumed; confirm cell chemistry)

| | |
|---|---|
| Pack voltage | ~324 V (3.0 V/cell), ~400 V nominal, ~454 V (4.2 V/cell) |
| Module voltage | Up to 50.4 V (12 × 4.2 V), which is below the 60 V DC threshold when a module stands alone |
| Temperature channels | Up to 72 GPIO inputs (8 per module), plus 2 die temperatures per device |
| Full stack cell read | About 9 × (24 data + 6 overhead) bytes, roughly 3–4 ms at 1 Mbps |

## Daisy chain as BMW built it

```
SME MCU ─UART─ ISO7721 ─ BQ79616 (base, addr 0) ══► Module 1 (addr 1) ══► … ══► Module 9 (addr 9, top of stack)
                                                ◄══════════ ring return? (to confirm) ═══════════╝
```

- The base device answers broadcast commands but not stack commands (`COMM_CTRL[STACK_DEV] = 0`).
- Stack devices return responses **top of stack first**.
- If the base device is used purely as a bridge, ignore its cell readings.

## To confirm at teardown

- [ ] One BQ79616 per module? What is the exact part (BQ79616 / BQ79616H / BQ79614 / BQ79612) and silicon revision?
- [ ] Cell-tap to VC-pin mapping, and how the 4 unused inputs are handled.
- [ ] NTC part number, and the GPIO mapping per module.
- [x] Chain isolation at the base device: **transformer** (daughter board, left 2 header pins)
- [ ] Chain isolation on the module CSC boards, and linear vs ring
- [ ] Cell chemistry and capacity.
- [ ] What the base BQ79616's VC/CB/GPIO pins on the daughter board connect to (a pure bridge, or measuring something?).
- [ ] How the daughter board's BQ79616 is powered (BAT, pin 1), and what its ground is referenced to.
