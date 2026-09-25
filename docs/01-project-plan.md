# Project plan

## Phase 0: Teardown and documentation (unpowered)

- For each module CSC board, record:
  - BQ79616 part number and silicon revision.
  - Which cell taps go to which VC/CB pins. With 12 cells on a 16-input part, check how the unused inputs are wired.
  - NTC count and part, and which GPIO each NTC is on.
  - Balancing resistor values.
  - Daisy-chain isolation: capacitors, capacitors plus chokes, or transformers.
  - Chain connector pinout.
- Chain topology: linear or ring? How many wires run between modules?
- SME: connectors, host MCU, the BQ79616 daughter board and its header, the CAN buses, and the wake inputs.
- Pack HV hardware: contactors, precharge, fuse, current sensor, HVIL routing.

## Phase 1: Sniff the original SME

See [06-sniffing-guide.md](06-sniffing-guide.md).

- Capture the host UART on the header side of the ISO7721 isolator.
- Record:
  1. Power-up: WAKE, auto-addressing, and every config write.
  2. Steady-state polling: which registers are read, and how often.
  3. Balancing commands.
  4. Responses to faults: open NTC, broken chain.
  5. Sleep and shutdown.
- Capture the SME's vehicle CAN at the same time, for reference.

## Phase 2: Bench bring-up

- Hardware: a Nucleo-G474, plus either the BMW daughter board (if it is on a connector) or a BQ79600EVM.
- Start with **one module**, standalone and not bus-barred (≤ 50.4 V), or a resistor-ladder cell simulator.
- Milestones:
  1. Wake the device.
  2. Read PARTID/DEV_REVID.
  3. Auto-address.
  4. Read 12 cells, the NTCs and die temperature.
  5. Read and clear faults.
  6. Balance one cell.

## Phase 3: Master PCB, revision A

See [08-master-hardware.md](08-master-hardware.md). Design it in parallel with Phase 2, once the host interface works on the bench.

## Phase 4: Driver layer

| Module | Responsibility |
|---|---|
| `bq_link` | Frame build/parse, CRC, timeouts, retries (plus SPI_RDY if using the BQ79600) |
| `bq_stack` | Wake, shutdown, auto-address, stack reads, ring-direction switching, comm-fault recovery |
| `bq_protect` | On-chip OV/UV/OT/UT comparators and NFAULT, so protection works without the MCU |
| `bq_balance` | Per-cell CB timers, VCB_DONE threshold, thermal pause |

Make the host type (base BQ79616 over UART, or BQ79600 over SPI) a build or config option. Both speak the same frame protocol.

## Phase 5: Full 9-module stack

- Add modules incrementally: 1 → 3 → 9.
- Break the ring at several points (between modules 1/2, 5/6 and 8/9) and confirm it recovers.
- Check accuracy against a calibrated DMM, and cross-check with the AUX ADC.

## Phase 6: BMS application

- State machine: Sleep → Wake → Self-test → Run/Charge → Fault latch.
- SOC by coulomb counting with rest-time OCV correction.
- Charge and discharge current limits, derated by cell voltage, temperature and SOC.
- Balancing strategy, periodic wake-up while parked, fault log.

## Phase 7: Integration and validation

- SimpBMS/Victron CAN output to ZombieVerter. See [07-zombieverter-can.md](07-zombieverter-can.md).
- Fault injection:
  - Open cell tap.
  - Broken chain.
  - Unplugged NTC.
  - OV/UV on the simulator.
  - Firmware halted: the interlock must still open the contactors.
  - CAN loss.
- Connect to the real HV pack last: fused, with isolation checks in place.
