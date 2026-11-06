# Walk ledger report

Generated 2026-11-06 15:55 from `walk-ledger/ledger.jsonl` (123 walks). Angles in degrees, model frame; error = present - goal after the lag shift. Built by `guide/firmware/mac/walk_ledger.py`.

## Newest walks

- 2026-11-06 15:49:07 (duck_wired_log_app1106-154805.jsonl, 11/02-11/06 saddle, USB lead hanging left): 2.18 s, vx 0.0 vth 0.5, drift -8.52 deg/s, tilt mean 5.56 max 13.3, 48.3 Hz, stance L/R 0.38/0.24
- 2026-11-06 15:49:02 (duck_wired_log_app1106-154805.jsonl, 11/02-11/06 saddle, USB lead hanging left): 2.7 s, vx 0.25 vth 0.0, drift +0.03 deg/s, tilt mean 4.91 max 10.6, 48.4 Hz, stance L/R 0.49/0.23
- 2026-11-06 14:12:38 (duck_wired_log_app1106-140704.jsonl, 11/02-11/06 saddle, USB lead hanging left): 2.87 s, vx 0.25 vth 0.0, drift -6.13 deg/s, tilt mean 39.14 max 117.8, 48.4 Hz, stance L/R 0.49/0.19, FELL (stand)
- 2026-11-06 14:12:34 (duck_wired_log_app1106-140704.jsonl, 11/02-11/06 saddle, USB lead hanging left): 2.81 s, vx 0.25 vth 0.0, drift -11.2 deg/s, tilt mean 6.65 max 16.2, 48.6 Hz, stance L/R 0.53/0.29
- 2026-11-06 14:12:30 (duck_wired_log_app1106-140704.jsonl, 11/02-11/06 saddle, USB lead hanging left): 3.76 s, vx 0.0 vth -0.5, drift +0.58 deg/s, tilt mean 4.63 max 11.5, 47.6 Hz, stance L/R 0.6/0.18
- 2026-11-06 14:12:22 (duck_wired_log_app1106-140704.jsonl, 11/02-11/06 saddle, USB lead hanging left): 6.72 s, vx 0.25 vth 0.0, drift -0.34 deg/s, tilt mean 4.69 max 12.6, 48.9 Hz, stance L/R 0.51/0.23
- 2026-11-06 14:12:17 (duck_wired_log_app1106-140704.jsonl, 11/02-11/06 saddle, USB lead hanging left): 2.53 s, vx 0.0 vth 0.5, drift -2.12 deg/s, tilt mean 6.2 max 15.6, 48.6 Hz, stance L/R 0.52/0.21
- 2026-11-06 14:12:07 (duck_wired_log_app1106-140704.jsonl, 11/02-11/06 saddle, USB lead hanging left): 7.22 s, vx 0.25 vth 0.0, drift -2.38 deg/s, tilt mean 6.33 max 14.0, 47.9 Hz, stance L/R 0.61/0.15
- 2026-11-06 14:12:04 (duck_wired_log_app1106-140704.jsonl, 11/02-11/06 saddle, USB lead hanging left): 1.13 s, vx 0.0 vth -0.5, drift -7.63 deg/s, tilt mean 4.52 max 14.3, 48.4 Hz, stance L/R 0.58/0.16
- 2026-11-06 14:07:14 (duck_wired_log_app1106-140704.jsonl, 11/02-11/06 saddle, USB lead hanging left): 286.83 s, vx 0.246 vth 0.0, drift -0.03 deg/s, tilt mean 4.81 max 12.0, 48.4 Hz, stance L/R 0.59/0.16

## Left against right, newest 10 walks

- hip_yaw: bias L -0.2 R -0.3; in own stance L -0.9 R +0.6; rms L +5.4 R +4.5; lag L 118.0 R 130.0 ms; amplitude L 0.44 R 0.66
- hip_roll: bias L +0.1 R +3.2; in own stance L +1.0 R +1.8; rms L +8.2 R +8.8; lag L 106.0 R 112.0 ms; amplitude L 0.28 R 0.21
- hip_pitch: bias L -0.3 R +0.3; in own stance L +1.2 R -1.4; rms L +12.3 R +12.6; lag L 104.0 R 112.0 ms; amplitude L 0.37 R 0.5
- knee: bias L +14.3 R -5.9; in own stance L +21.3 R -16.2; rms L +21.4 R +15.2; lag L 104.0 R 106.0 ms; amplitude L 0.31 R 0.48
- ankle: bias L -2.1 R +0.7; in own stance L -2.2 R -0.0; rms L +8.7 R +7.7; lag L 106.0 R 100.0 ms; amplitude L 0.4 R 0.54

## Flags (what to look at; nothing here is applied to the robot)

- hip_yaw amplitude differs L 0.44 R 0.66
- left knee sags more under its own stance (+21.3 vs -16.2)
- knee amplitude differs L 0.31 R 0.48
- stance time uneven: left 0.53, right 0.20 of ticks
- falls: 1 of 10 newest walks

## Newest 10 against the 113 before

- hip_yaw stance bias: L +0.6 -> -0.9, R +0.8 -> +0.6
- hip_roll stance bias: L +0.8 -> +1.0, R +1.8 -> +1.8
- hip_pitch stance bias: L +0.4 -> +1.2, R -2.4 -> -1.4
- knee stance bias: L +17.1 -> +21.3, R -14.3 -> -16.2
- ankle stance bias: L -2.0 -> -2.2, R -0.2 -> -0.0
- drift: +3.8 -> -3.8 deg/s; falls 13/113 -> 1/10

## By condition (--note)

- 10/19-10/23 A7Z in head, no USB camera lead, standing still: left leg share 0.59, roll -0.5 deg (+ = leaning left), 5 logs
- 11/02-11/06 saddle, USB lead hanging left, standing still: left leg share 0.54, roll +2.4 deg (+ = leaning left), 8 logs
- 10/19-10/23 A7Z in head, no USB camera lead: 28 walks, drift +14.8 deg/s, falls 6, knee stance L +19.8 R -13.3
- 11/02-11/06 saddle, USB lead hanging left: 95 walks, drift -0.2 deg/s, falls 8, knee stance L +16.8 R -14.7
