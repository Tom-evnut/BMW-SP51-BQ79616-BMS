# Sniffing the original SME

## Safe bench setup

1. **Remove the busbars between modules.** Each module then stands alone at ≤ 50.4 V (12 × 4.2 V), below 60 V DC.
2. Connect the SME to all 9 module boards through the original chain harness. The chain itself is isolated.
3. Leave the SME's HV connector unplugged. Expect HV, HVIL and isolation faults; the chain should still be initialised.
4. Power the SME from a current-limited 12 V supply on KL30, plus the wake/KL15 line.
5. BMW ECUs often need network-management or terminal-status CAN frames to stay awake. The chain init normally
   happens at power-up regardless, so capture from the moment power is applied.

## Where to probe

- **Only on the host (header) side of the ISO7721.** See [05-sme-daughterboard.md](05-sme-daughterboard.md).
- Solder thin (30 AWG) wires to series or pull-up resistors, vias, or the header. Don't clip fine-pitch IC pins.
- Never probe the daisy-chain COM lines or anything on the BQ side until its reference has been proven.

## Probe points on the daughter-board header (confirmed)

Pin numbering is described in [05-sme-daughterboard.md](05-sme-daughterboard.md).

| Header pin | Signal | Analyser |
|---|---|---|
| **A6** | Host-side GND (ISO7721 GND2) | Analyser GND |
| **A7** | Host TX → BQ79616 RX (ISO7721 INA) | CH0 |
| **B7** | Host RX ← BQ79616 TX (ISO7721 OUTB) | CH1 |

## Logic analyser settings

| Setting | Value |
|---|---|
| Channels | Host TX (→ BQ RX), host RX (← BQ TX), plus NFAULT and wake if available |
| Sample rate | ≥ 25 MS/s |
| Decoder | Async serial, 1 Mbps, 8N1, LSB first, idle high (try 250 kbps if nothing decodes) |
| Trigger | Falling edge on host TX, pre-trigger ≥ 100 ms |

Long low pulses on host TX are **pings, not bytes**: ~250 µs = sleep→active, ≥ 2 ms = WAKE, ~7 ms = shutdown,
~36 ms = HW reset.

## What to capture (priority order)

1. **Power-up**: WAKE, DLL-sync dummy write, auto-addressing, COMM_CTRL setup, every config write.
   This gives BMW's thresholds, ACTIVE_CELL, GPIO/NTC config and ADC settings.
2. **Steady state**: which registers are polled, stack vs single reads, and the interval.
3. **Balancing**: the CB_CELLx_CTRL and BAL_CTRLx writes. You may need to create some cell imbalance to trigger them.
4. **Faults**: unplug an NTC, break the chain, hold a cell out of range on a module.
5. **Sleep and shutdown sequence**.
6. **SME vehicle CAN** alongside, for reference.

Name captures as described in [../captures/README.md](../captures/README.md).
