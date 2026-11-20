# Soft power switch with hardware low-voltage cutoff (proposal, 2026-11-19)

Status: proposal for Shawn's approval. Nothing bought, no PCB drawn. Replaces the REV-31-1387 XT30 switch of the
battery backpack (`../battery-backpack-20261015/README.md` section 4).

## Problems (Shawn, 2026-11-19)

1. The hard switch gets left on. The pack then drains slowly: the A7Z drops out first (the DFR1202 needs 6 V in), the
   brain and its battery guard stop with it, and the OpenRB plus 15 servos (about 0.26 A standby) keep pulling the
   pack down. Seen as servos at factory settings (FAULTS.json `servo-factory-reset`) and one Tattu pack with a dead
   cell (CURRENT-STATE.json `parts_battery_charging`, 2026-11-19).
2. Power should behave like a household button: press once, light on; after shutdown the light goes out by itself.
3. A software shutdown should also switch the hardware off.

## Design

```
battery XT30 --> Pololu #2813 VIN    VOUT --> OpenRB J4 (servos) and DFR1202 (A7Z 5 V), as today
                 A/B   <-- panel momentary button (LED ring lit from VOUT)
                 OFF   <-- A7Z GPIO, one high pulse at the end of shutdown (100 k pull-down on the board)
                 OFF   <-- XIAO pulse when VOUT stays under 6.0 V for 3 s (diode-OR with the A7Z line)
```

Feature registry (ID, problem, why, simpler option considered, validation, when to change or delete):

- **PS-1 Latching switch: Pololu Big Pushbutton Power Switch with Reverse Voltage Protection, HP, #2813.**
  Problems 1-3. 4.5-32 V, 6 A continuous at 55 C, 90 A maximum, off-state draw under 0.2 uA, 2.7 g, 0.8 x 1.0 in,
  $8.95 (pololu.com/product/2813, read 2026-11-19). Robot current: walking 1.3-2.2 A, sit-to-stand peak about 8 A,
  all servos stalled 25-29 A briefly (`../battery-backpack-20261015/README.md` section 2), inside its 90 A maximum.
  Simpler option: keep the REV switch and rely on memory; that is the failure being fixed. Validation: bench rail
  current walk test, MOSFET temperature after 10 min walking. Change if a sustained load above 6 A appears.
- **PS-2 Hardware cutoff: Seeed XIAO SAMD21 on VOUT (fed by a small 5 V buck), reading VOUT through a 100 k / 33 k
  divider and pulsing the switch's OFF pin through a 1N4148 (A7Z GPIO joins OFF through a second 1N4148, 100 k
  pull-down on OFF).** Problem 1 when the brain is not running. Cutoff 6.0 V (3.0 V per cell) held for 3 s, so a
  foot-strike sag does not trip it, with a 3 s grace after power-on; the software guard (6.6 V stop, 6.2 V floor,
  `guide/firmware/pi/battery.py`) still acts first. Pressing the button on a flat pack switches on and off again
  after the grace, so a flat pack cannot be drained further. The XIAO is powered after the switch, so it draws
  nothing when off. A TPS3710 supervisor with an RC on SENSE was the first draft and is rejected: the RC holds SENSE
  low for about 2 s after power-on, so the supervisor would switch the robot off at every press. Simpler options rejected: a per-cell
  2S BMS (HX-2S-JH20: 2.4-2.6 V per cell, 10 A trip, below the 8 A sit-to-stand peak margin and the stall current,
  and it needs the balance plug on the robot); off-the-shelf LVD modules start at 10-12 V. Validation: bench supply
  ramp, trip at 6.0 V +-0.1 V, no trip on a 0.3 s dip to 5.5 V.
- **PS-3 Software power-off: one A7Z GPIO to OFF, pulsed by a systemd-shutdown hook after the filesystems are
  read-only.** Problem 3; the battery guard's shutdown then also removes power. Needs a pin that stays low through
  boot (pull-down on the board). Validation: `sudo poweroff` ends with the LED dark and zero rail current.
- **PS-4 Panel button with LED ring.** Problem 2. The ring is fed from VOUT, so it is lit exactly while the robot has
  power. Mounts in the backpack where the REV switch sits now; the cutout changes, so the cap is reprinted.
- **PS-5 Idle timeout on the A7Z (software).** Problem 1 for the case "A7Z on, brain stopped": no brain and no ssh
  session for 30 min, shut down, which with PS-3 removes power.

## Open before CAD

- The free A7Z header pin for OFF (head wiring uses the inner row, memory `microduck-a7z-head`).
- PS-2 is modules and through-hole parts only (XIAO, buck, two resistors, two diodes): no PCB, no SMD.
- XT30 pigtails soldered to the Pololu's large VIN/VOUT holes.
