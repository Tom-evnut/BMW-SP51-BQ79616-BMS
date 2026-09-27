# New BMS master hardware

Dedicated hardware: not based on ZombieVerter or other existing boards.

## Block diagram

```
12V/KL30 ─► reverse-polarity + load-dump protection ─► low-Iq supply (always-on domain + switched domain)
Wake inputs: KL15, charger / CP detect, chain reverse-wake (BQ79600 INH option)
             │
          STM32G474 ──► host interface (option A or B below) ══► 9 × BQ79616 modules (ring)
             │  ▲
             │  └── NFAULT
             ├─ FDCAN1: ZombieVerter (SimpBMS/Victron) + ISA IVT-S
             ├─ FDCAN2: diagnostics / per-cell data
             ├─ FDCAN3: spare (charger / service)
             ├─ "BMS OK" interlock output → in series with contactor coil supply
             ├─ FRAM/EEPROM: SOC, calibration, fault log
             └─ SWD + UART console
```

## MCU

**STM32G474**:
- 3 × FDCAN, 170 MHz.
- Independent and window watchdogs, hardware CRC unit.
- Dual-bank flash, for safe firmware updates over CAN.

An STM32H5 is the alternative if more headroom or security features are wanted.

## Host interface options

| Option | Description | Pros | Cons |
|---|---|---|---|
| **A: copy BMW** | BQ79616 base device over UART, through an ISO7721-class isolator | Captured SME traffic replays 1:1; proven with BMW's chain isolation | Large 64-pin part; UART only; BAT needs ≥ 9 V (may brown out during cranking unless boosted) |
| **B: BQ79600-Q1** | TI's dedicated bridge over SPI | Smaller; reverse wake; TI's current recommended design | Device map shifts slightly; isolation must match BMW's chain |

**Plan:** make the driver support both. Prototype with option A, ideally by plugging BMW's own daughter board into a Nucleo.

## Connector to the BMW daughter board (if reused)

- The daughter board carries an **IRISO IMSA-10120S-20Y915-derived socket** (2.0 mm pitch, floating Z-Move
  board-to-board, 12.35 mm tall). The master needs the mating **IMSA-10120B-20…** plug (drawing 110-410120-847).
- Match the original mated height (11–20 mm range, set by the plug/socket variant pair). Measure it on the SME.
  **Use the 7.95 mm plug (IMSA-10120B-20Y911 / -20Z02-GFN4, drawing 110-410120-847) with ~19.0 mm board spacing.**
  The daughter-board socket is 16.3 mm (Y504 type) and the SME boards measure 19.2 mm apart, which fits this plug
  (19.0 mm nominal, ±0.7 mm Z float). See docs/05. Confirm with the SME plug's `B**` marking if possible.
- Fix the two boards together with screws or standoffs near the connector. IRISO says not to rely on the connector alone.
- Keep columns 2 and 9 unused. They provide the creepage gap between the host and isolated domains, since the
  connector itself is only rated 125 V.
- The master must provide:
  - Host logic supply on A8 (2.25–5.5 V), with GND on A6.
  - UART on A7 (TX) and B7 (RX).
  - An isolated 9–40 V supply on B10/A10 (~12 V, ~100 mA peak). This needs a small isolated DC-DC with isolation
    rated for the pack voltage.
  - Chain transformer pair on A1/B1, routed to the module harness.

## Pack measurement

| Option | Parts | Notes |
|---|---|---|
| A (easiest) | ISA IVT-S on CAN1 + Bender IR155 | ZombieVerter and the BMS can both read the IVT-S broadcasts |
| B (integrated) | BQ79631-Q1 in the daisy chain | Current, HV and insulation resistance on the same protocol. Needs HV creepage/clearance on the board |

## HV ratings

The pack reaches about 454 V, so rate the contactors, precharge, fuse and connectors for at least 500 V DC.
ZombieVerter sequences precharge and the main contactors. The BMS master only provides the hardware interlock.

## Safety

- **Hardware OR shutdown:** NFAULT, the watchdog and the firmware each independently de-energise the "BMS OK" interlock.
- The BQ79616 on-chip OV/UV/OT/UT comparators stay configured, so protection doesn't depend on the MCU loop.
