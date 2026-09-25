# Captures

Logic-analyser and CAN captures from the original BMW SME.

## Naming

`YYYY-MM-DD_<what>_<setup>.<ext>`

For example: `2026-10-01_powerup_9mod-nobusbar.sal`, `2026-10-01_steady-state_9mod-nobusbar.csv`

## For each capture, record

- Analyser, sample rate, channels and what each is connected to.
- Pack or module setup: modules connected, busbars fitted or not, SME inputs powered.
- What was done during the capture (power-up, NTC unplugged, …).
- Export the decoded UART as CSV alongside the native file, so the tools can parse it.
