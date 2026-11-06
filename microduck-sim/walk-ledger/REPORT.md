# Walk ledger report

Generated 2026-11-06 14:55 from `walk-ledger/ledger.jsonl` (14 walks). Angles in degrees, model frame; error = present - goal after the lag shift. Built by `guide/firmware/mac/walk_ledger.py`.

## Newest walks

- 2026-10-23 18:56:15 (duck_wired_log_app1023-225437.jsonl, 1023 bench): 3.64 s, vx 0.25 vth 0.3, drift -12.01 deg/s, tilt mean 4.8 max 14.1, 48.0 Hz, stance L/R 0.47/0.34
- 2026-10-23 18:55:58 (duck_wired_log_app1023-225437.jsonl, 1023 bench): 16.16 s, vx 0.243 vth 0.094, drift -1.61 deg/s, tilt mean 4.51 max 16.1, 48.1 Hz, stance L/R 0.58/0.2
- 2026-10-23 18:55:35 (duck_wired_log_app1023-225437.jsonl, 1023 bench): 3.98 s, vx 0.25 vth -0.3, drift +14.86 deg/s, tilt mean 3.42 max 9.9, 48.5 Hz, stance L/R 0.64/0.15
- 2026-10-23 18:55:31 (duck_wired_log_app1023-225437.jsonl, 1023 bench): 3.39 s, vx 0.25 vth 0.0, drift +0.71 deg/s, tilt mean 3.61 max 7.2, 48.5 Hz, stance L/R 0.6/0.2
- 2026-10-23 18:55:24 (duck_wired_log_app1023-225437.jsonl, 1023 bench): 3.44 s, vx 0.25 vth 0.0, drift +0.56 deg/s, tilt mean 3.52 max 7.7, 47.6 Hz, stance L/R 0.5/0.23
- 2026-10-23 18:35:43 (duck_wired_log_app1023-223352.jsonl, 1023 bench): 8.5 s, vx 0.244 vth -0.029, drift +3.83 deg/s, tilt mean 3.51 max 9.7, 47.8 Hz, stance L/R 0.58/0.17
- 2026-10-23 18:35:37 (duck_wired_log_app1023-223352.jsonl, 1023 bench): 4.87 s, vx 0.25 vth 0.0, drift +0.68 deg/s, tilt mean 3.53 max 9.0, 48.6 Hz, stance L/R 0.52/0.24
- 2026-10-23 18:35:26 (duck_wired_log_app1023-223352.jsonl, 1023 bench): 6.22 s, vx 0.232 vth 0.0, drift -2.13 deg/s, tilt mean 3.24 max 8.1, 48.2 Hz, stance L/R 0.46/0.25
- 2026-10-23 17:03:25 (duck_wired_log_app1023-210115.jsonl, 1023 bench): 1.21 s, vx 0.25 vth 0.0, drift +6.09 deg/s, tilt mean 6.59 max 26.3, 34.2 Hz, stance L/R 0.21/0.53, FELL (log-end)
- 2026-10-23 16:42:37 (duck_wired_log_app1023-204119.jsonl, 1023 bench): 7.31 s, vx 0.25 vth -0.8, drift +47.98 deg/s, tilt mean 3.24 max 9.1, 48.7 Hz, stance L/R 0.55/0.19

## Left against right, newest 10 walks

- hip_yaw: bias L +2.2 R +0.4; in own stance L +4.2 R +1.0; rms L +7.9 R +6.3; lag L 104.0 R 118.0 ms; amplitude L 0.36 R 0.45
- hip_roll: bias L -1.2 R +2.9; in own stance L -0.2 R +1.6; rms L +9.1 R +10.3; lag L 104.0 R 102.0 ms; amplitude L 0.3 R 0.21
- hip_pitch: bias L -4.2 R +1.3; in own stance L -3.0 R -0.8; rms L +15.2 R +15.1; lag L 120.0 R 116.0 ms; amplitude L 0.42 R 0.45
- knee: bias L +14.2 R -6.4; in own stance L +22.6 R -15.2; rms L +23.0 R +19.6; lag L 112.0 R 104.0 ms; amplitude L 0.36 R 0.45
- ankle: bias L -4.9 R +0.1; in own stance L -4.6 R -3.1; rms L +9.1 R +9.3; lag L 112.0 R 108.0 ms; amplitude L 0.6 R 0.42

## Flags (what to look at; nothing here is applied to the robot)

- left hip_yaw sags more under its own stance (+4.2 vs +1.0)
- left knee sags more under its own stance (+22.6 vs -15.2)
- ankle amplitude differs L 0.6 R 0.42
- stance time uneven: left 0.51, right 0.25 of ticks
- control loop under 45 Hz on 1 walks (lowest 34.2 Hz; the 50 Hz policy diverged at 36 Hz on 10/23): check CPU clock and temperature
- falls: 1 of 10 newest walks

## Newest 10 against the 4 before

- hip_yaw stance bias: L +1.9 -> +4.2, R +1.3 -> +1.0
- hip_roll stance bias: L +0.1 -> -0.2, R +4.3 -> +1.6
- hip_pitch stance bias: L -3.0 -> -3.0, R -0.7 -> -0.8
- knee stance bias: L +17.9 -> +22.6, R -10.0 -> -15.2
- ankle stance bias: L -4.1 -> -4.6, R -0.7 -> -3.1
- drift: +0.6 -> +5.9 deg/s; falls 0/4 -> 1/10
