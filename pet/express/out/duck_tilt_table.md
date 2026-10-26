# Duck trunk tilt per take under stand61

As-built MuJoCo duck (saddle mass manifest), stand61 at zero command, head commands through walk_brain.Brain's own head path (EMA pre-inverted by pet/express/duck.py). Tilt = largest change of trunk roll/pitch from the 0.6 s before the call, over the 2.3 s response. Baseline = today's path: the target pose stepped in and smoothed by HEAD_ALPHA 0.2. Servo rail and read-drop values come from microduck-sim/CURRENT-STATE.json, whose entries were stale on 2026-10-26 (robot offline); the stress condition brackets them. Regenerate with `~/.venvs/microduck-dyn/bin/python pet/express/duck_sim.py --tilt`.

**Real condition**: 7.0 V servo rail, 4 % servo read drops, 20 calls per set, 3.5 s apart.

| set | calls | trunk tilt median / p95 / max (deg) | head latency median (s) | joint lag (s) | tracking rms (rad) | EMA saturated ticks | falls |
|---|---|---|---|---|---|---|---|
| baseline | 20 | 0.41 / 0.58 / 0.63 | 0.10 | 0.14 | 0.053 | 0 | 0 |
| quick_snap | 20 | 0.59 / 1.23 / 1.29 | 0.40 | 0.14 | 0.054 | 441 | 0 |
| curious_turn | 20 | 0.46 / 0.76 / 0.83 | 0.60 | 0.13 | 0.027 | 38 | 0 |
| double_take | 20 | 0.54 / 0.98 / 1.00 | 0.28 | 0.14 | 0.070 | 298 | 0 |
| groggy | 20 | 0.29 / 0.47 / 0.48 | 0.82 | 0.14 | 0.018 | 0 | 0 |
| glance | 20 | 0.19 / 0.32 / 0.36 | 0.39 | 0.16 | 0.021 | 0 | 0 |
| quick_snap_max | 20 | 0.63 / 1.01 / 1.19 | 0.32 | 0.14 | 0.074 | 427 | 0 |
| greet | 20 | 0.53 / 0.91 / 1.12 | 0.35 | 0.14 | 0.061 | 459 | 0 |
| startle | 20 | 0.53 / 1.09 / 1.10 | 0.16 | 0.14 | 0.071 | 846 | 0 |

**Stress condition**: 6.6 V servo rail, 8 % servo read drops, 20 calls per set, 3.5 s apart.

| set | calls | trunk tilt median / p95 / max (deg) | head latency median (s) | joint lag (s) | tracking rms (rad) | EMA saturated ticks | falls |
|---|---|---|---|---|---|---|---|
| baseline | 20 | 0.41 / 0.58 / 0.65 | 0.10 | 0.14 | 0.057 | 0 | 0 |
| quick_snap | 20 | 0.54 / 1.15 / 1.24 | 0.40 | 0.16 | 0.058 | 441 | 0 |
| curious_turn | 20 | 0.43 / 0.78 / 0.83 | 0.59 | 0.14 | 0.031 | 38 | 0 |
| double_take | 20 | 0.52 / 0.87 / 0.95 | 0.28 | 0.14 | 0.074 | 298 | 0 |
| groggy | 20 | 0.31 / 0.51 / 0.52 | 0.80 | 0.16 | 0.019 | 0 | 0 |
| glance | 20 | 0.22 / 0.37 / 0.45 | 0.40 | 0.16 | 0.024 | 0 | 0 |
| quick_snap_max | 20 | 0.54 / 0.71 / 1.01 | 0.32 | 0.14 | 0.083 | 427 | 0 |
| greet | 20 | 0.48 / 0.85 / 1.02 | 0.36 | 0.14 | 0.070 | 459 | 0 |
| startle | 20 | 0.61 / 1.04 / 1.13 | 0.17 | 0.14 | 0.079 | 846 | 0 |
