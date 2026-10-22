# MicroDuck A7Z, 2026-10-22 afternoon (EDT): closed-head soak attempt, three resets in 25 minutes

D-021: the 6530B heatsink and the back-to-back head were dropped; the one-hour closed-head soak
(`../../pi/A7Z-CPU-COMPARE.md`, `a7z_cpu_compare.py run default --soak-min 55 --burn policy_burn.py`) was to decide
whether the A7Z stays in the head. The robot ran on the bench supply (`--supply bench`, 5991 at 15 V into the two
XL4015). Logs copied from the A7Z `~/duck-logs/`; tick logs and thermal.log gzipped, out of git. The A7Z journal is
volatile, so no boot keeps a record of how it ended; the A7Z clock runs 1 to 3 minutes slow until NTP sets it after
each boot, so A7Z-stamped times (progress log, early thermal rows) lag the Mac times below by up to that much.

## Timeline (Mac clock, EDT)

- 15:33 power-up by Shawn; brain `app1022-193343`; open-loop stands, then walk from 19:34:51Z.
  **Reset 1 at 19:35:01Z**, 10 s into the walk, hottest zone 45.6 C, servo rail 7.0-7.3 V in every tick before
  the cut. Brain log and thermal log stop in the same 20 ms tick; board back 26 s later.
- 15:35 brain `app1022-193550` (stand, KP 400, 10 min). 15:37 soak run 1 started (ORT one-thread fix confirmed on
  the board, `walk_brain.py:219`; `policy_burn` at 50.0 runs/s, 0.8 ms per run). Hottest 58.8 C at start, 68.4 C at
  minute 5 (p0 780 MHz, p6 416 MHz, loop p50 17.6 / p90 18.3 ms), 75.1 C at minute 8.
  **Reset 2 at 19:45:39Z**, 0.84 s after `mode -> walk`, hottest 77.5 C. Board back 25 s later.
- 15:46 boot lasted 80 s with no brain; back 10 s later (cause unknown, possibly a manual power cycle).
- 15:50 brain `app1022-195046` (Shawn: stand61, i.e. walk mode at zero command, and stands). 15:51 soak run 2
  started hot (77 C). Minute 5: 85.4 C, both clusters at 416 MHz (`scaling_max_freq` pulled down by the thermal
  governor, trips at 60 C), loop p50 20.2 / p90 27.0 ms. Minute 9: 93.5 C, 416/416 MHz, p50 23.6 / p90 24.6 ms
  (about 42 ticks/s). **Reset 3 at about 16:00**, brain in walk mode (stand61), last thermal row 89.6 C.
- 16:02 after the reboot, idle: every SoC zone 89-91 C, both clusters capped at 416 MHz.

## What this answers

1. Heat: with the brain and a policy load in the closed head the SoC passes 85 C in five minutes and the governor
   pins both clusters at 416 MHz (the lowest table entry); the loop runs at 23-24 ms, about 42 Hz. The acceptance
   (policy-row p90 <= 18 ms, >= 49 ticks/s) fails from minute 5. A CPU cap or big cores offline cannot improve on
   416 MHz, so the `cap` and `offline` runs were not made.
2. Resets: three in 25 minutes. Two came within 10 s and 0.84 s of a walk start at 45 C and 77 C (servo current
   step on the 5 V/15 V path), one at about 90 C in stand61. None left a kernel message (volatile journal), the
   kernel critical trip is 110 C. The PMIC (AXP8191) sits in the same 90 C air; a power-path brownout at the walk
   step and a PMIC over-temperature cut at 90 C are both consistent with the data, and neither is a kernel thermal
   shutdown. The 5 V and 15 V rails have not been measured at a walk start (no sysfs reading exists; the header has
   no ADC): multimeter MIN/MAX at the XL4015 #2 output and the 5991 output is the next measurement.
3. Not run: the full hour, the cap/offline variants, the copper heatsink.

Files: `cpu_compare_progress.log`, `cpu_compare_default*.out`, `policy_burn.out`, `thermal.log.gz`,
`duck_wired_*.out`, `duck_wired_log_*.jsonl.gz`. No `cpu_compare_*.json` result was written (both runs ended in a reset).
