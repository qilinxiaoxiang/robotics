# MicroDuck robot runs, 2026-10-21 early morning: brain onboard the A7Z, remote control

`walk_wired.py` on the Radxa Cubie A7Z (servos over J12 UART2, BNO085 on i2c-7), driven from the remote page `microduck_rl/cmu/simulator/app/robot-live.html`. Logs copied from the A7Z `~/duck-logs/`; tick logs are gzipped here and stay out of git like the earlier runs. Row format as in `robot-runs-20261019-a7z/README.md`, plus `sit_phase` and `sit_flag` on sit rows.

- **app1021-035737** (319 s): open-loop stands and stand61 at zero command only. No sit command reached the control file.
- **app1021-040436** (332 s): two sits from stand61, seven quacks while "seated", stand61 episodes.

## The sit stalls standing (both sits)

- The command path worked: `mode -> sit`, `sit: posture flag 1` 0.80 s later, `sit_phase` seated by the 2.0 s timer, `policy` sitstand, `kp` 200 on every seated row; no refusal, no `STOP ->`, no IMU loss.
- The legs never folded. Mean leg joints over the 2,448 seated rows (98.7-156.1 s from the first row): left knee 0.025 rad, right knee -0.034 rad (the plugged as-built sim seats at 1.335 / -1.36 rad, trunk 58 mm lower); body gravity [0.076, -0.068, -0.995], about 6 deg, unchanged from standing.
- The policy's own seated actions stayed under 0.21 rad. An offline replay of `sitstand61.onnx` on the logged observations reproduces them to 0.001 rad, so the Brain fed the policy correctly. The policy's descent starts from the physical response to its first 0.1-0.3 rad moves; the loaded leg servos did not follow them, the observation never changed, and the policy stayed at its standing fixed point.
- In the as-built sim, `brain_sim_check.py --bam-friction-scale 3.0` (a proxy for the measured weak servo response, not a measurement) gives the same signature: "seated" declared, trunk height unchanged. `--kp-rl 300/400` and `--breakaway` do not restore the sit there.
- The first sit was ended 4.0 s after it began by an explicit zero walk command (the page's sit/stand toggle pressed again, or the closed-loop stand key).

Analysis, patch (a `sit: STALLED` notice when the knees have not folded at the seated phase) and the acceptance procedure for the next powered session: `~/code/reports/20261021-microduck-sit-button.html`. The notice is in `walk_brain.py` (`SIT_KNEE_MIN`, test `test_sit_stall.py`) and reaches the robot with the next install.

## Stands

Open-loop stand (KP 400) episodes rest 5.5-14.9 deg and fall forward within about 20 s; stand61 episodes hold 4-6 deg for 4-8 s and then tip within 0.5 s, each starting from an open-loop stand already leaning forward. Study: `stand-gap-20261021/README.md`; feet and stand page: `~/code/reports/20261021-microduck-stand-falls-and-feet.html`.

Cause found later on 2026-10-21 (`../investigation-20261021/policy-churn/README.md`): KP 400 held every leg joint to 0.01-0.03 rad; at leans under 8 deg the body rocked about the ankle axis with all ten leg encoders frozen (pitch swing p90 2.2 deg, up to 3.3 deg; 10/19: p90 0.06 deg), and every stand61 run oscillated at 3.5-4.5 Hz (leg actions 180-620 mrad, trunk yaw rate 1.2-3.1 rad/s) until it tipped. The as-built sim reproduces the oscillation and the forward fall with +-8 deg of free play between the ankle servo output and the foot, and the sit stall as well when the servo friction proxy x3 is added. Both days ran the same slip-fit feet; the ankles on 10/21 were the V1.24/V1.25 two-half ankle (Shawn, 2026-10-21), the stock bracket cut at mid shaft and held together only by the slip-fit foot and the toe screw, where 10/19 had the one-piece bracket. Acceptance after the repair: `stand_check.py` on the next log.

## What these runs used, and what changed in code afterwards (not on the robot yet)

- These runs used the runtime installed on the A7Z before commit 82d5f87: quack head move 1.6 s with 0.5 s ramps on stand61 only, open-loop stand KP 400 and KP_RL 200 on every logged tick.
- Committed 2026-10-21 after the runs, not deployed: 82d5f87 (quack head move also seated and after a walk), 1652f88 (`sit: STALLED` notice; `QUACK_HEAD_S` 0.6 s, `QUACK_HEAD_RAMP_S` 0.15 s), 4f5c2c6 (servo Present Current read from address 126 and the five head touch pads in the tick log). They reach the robot with the next `install_teleop.sh` run; until then the robot behaves as in these logs.
- Withdrawn, never applied: open-loop stand KP 600 (stand page and `stand-gap-20261021/README.md`). KP 400 already held the joints to 0.01-0.03 rad on 10/19 and 10/21; the falls come from play below the encoders, which a higher gain cannot remove. Stand mode stays at KP 400 (`microduck-sim/CURRENT-STATE.json` `walking_policy`).
