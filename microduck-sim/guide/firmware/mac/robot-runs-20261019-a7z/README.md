# MicroDuck robot runs, 2026-10-19 evening: brain onboard the A7Z

`walk_wired.py --port /dev/ttyAS2 --baud 500000 --imu-bus 7 --supply bench` runs on the Radxa Cubie A7Z itself (venv `~/.venvs/duck-policy`, started by `~/duck-run.sh <suffix>`): servos over J12 UART2 through openrb_dual_host, BNO085 read locally on i2c-7. No Mac in the loop. Logs persist on the A7Z in `~/duck-logs/` and are copied here. Each log row adds the raw record: `acc`, `imu_seq`, `pos_tick`, `vel_tick`, `goal_tick` (ticks written that tick), `cmd`.

Feet: V1.22 slip-fit feet, no anti-slip sole yet. Ankle zeros +-90 deg after the refit (`pi/joint_signs.py`).

- **1019c**: stand from side-lying with the old ankle zeros; both ankles overloaded (targets about 100 deg off after the refit).
- **1019d**: stand with the +-90 deg zeros; left ankle never moved (it was mechanically jammed, freed by Shawn later), robot crept and fell forward after about 21 s in open-loop stand mode.
- **1019f** (walk_t0_1019f): walk61 0.25 m/s for_s 3 on a smooth surface. Tripped forward at 1.3 s (tilt 12 -> 37 deg in 0.1 s); actions mean 1.17 / max 2.69 rad in the first 1.2 s against 0.70 / 1.57 on the clean 10/18 walks.
- **1019f** (walk_t0_1019g): same walk on the floor. Walked 3 s and stopped standing. First 1.2 s matches 10/18 (actions mean 0.71, max 1.37, tilt 8.5 deg); later tilt reached 14.8 deg (10/18: at most 7) and actions 2.3 rad.

Timing onboard vs the Mac brain (10/18): servo sync read 8.5 vs 5.2 ms, loop 12.2 vs 5.7 ms, joint age used 12 vs 6 ms, IMU age used 21 vs 12.5 ms; 50 Hz held, 1-8 stale ticks per walk.
- **1019f** (walk_t0_1019h): same walk on the floor again. Tripped forward at 1.2 s (tilt 13 -> 37 deg in 0.1 s), like the first walk.
- **1019f** (walk_t0_1019i): walk61 0.25 m/s for_s 2 on a silicone mat. Clean: actions max 1.16 rad (10/18: 1.37-1.57), tilt at most 6.8 deg while stepping, 11.5 deg while stopping; stood afterwards. With grip the onboard brain walks as well as the Mac brain did, so the floor trips were the bare V1.22 feet slipping, not the A7Z latency.

## 2026-10-20 early morning: A7Z resets (logs in `a7z-logs-20261020/`)

- `duck_wired_log_1019m` and `duck_wired_log_1020a` are tick logs with 50 Hz round-robin servo input voltage (`servo_v`), fsynced every 50 ms. `thermal.log` is the 10 Hz SoC temperature and CPU frequency log; each `# boot` header starts a new boot.
- Reset 4 (1020a, 04:23:40 UTC) came 0.24 s into stand61 at zero command. The servo rail read 7.1-7.3 V up to the last tick, so the shared input did not sag. The SoC was at 84-86 °C (kernel critical trip 110 °C) and throttled between 416 MHz and 1.5 GHz, with loop time 24-33 ms.
- Open question: an A7Z 5 V dip under CPU load steps versus a board-level thermal reset. A 20 s full-CPU test with the servos untouched separates them; it has not been run yet.
