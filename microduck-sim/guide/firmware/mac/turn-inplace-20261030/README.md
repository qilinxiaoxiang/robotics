# In-place turn stalls, 2026-10-30

Robot run `walk611030-160205` (walk61, `--supply bench`, A7Z time EDT). Shawn sent long in-place turns
(`vx 0`, `vtheta +-0.5`) from the app; the duck stepped in place without turning.

## Robot

`robot_walk611030-160205_tail20000.jsonl.gz` is the last 20000 ticks (16:06:41-16:13:31), copied with
`tail -n 20000` and analysed on the Mac. The brain ran at 48-49 Hz throughout.

- Every in-place turn starts turning for 1-4 s (15-35 deg/s, 40-90 deg), then stalls: the trunk yaw rocks
  +-10 deg/s with the steps and the net rate is about 0. Example: right turn 16:11:48, -70 deg in 4 s, then
  16:11:53-16:12:33 about -50 deg in 40 s. Left turns stall the same way (16:10:13: +75 deg in 3 s, then 13 s still).
- When the robot falls behind, `walk_brain.py` in-place turn = vtheta + 3.0 x heading error, with the error capped at
  ARC_LEAD 0.35 rad, so the command to walk61 sits at -1.55. That is outside walk61's trained range (-1, 1), but it
  follows from the stall and does not cause it (sim below).
- The servos follow 25-40 % of the hip-yaw goal swing and about 15 % of the hip-roll swing, the same in turning and in
  stalled seconds (`hy2.py`).
- Stall headings differ between turns (about -70, -41, -24, +72, 0, -25 deg from the start), and each turn direction
  stalls after it has turned some tens of degrees.

## Sim (as-built, `--volt 7.0 --drop 0.04`, 25 s at vx 0, `runs.sh`, `runs2.sh`, summaries in `sim/`)

- Default head, head pitch -0.75 or -0.25, floor mu 0.5, BAM friction x1.5, IMU pitch 4 deg: steady 26-29 deg/s
  for all 25 s, in both directions and both seeds. No stall. The command stays at -0.74 to -1.03 because the
  sim robot keeps up.
- The only condition that slows or stalls a turn is an external yaw torque on the trunk. With 0.010 N m to the left,
  right turns drop to -13 deg/s (command -1.50). With 0.020 N m, right turns reverse to +29 deg/s even though the
  command is pinned at -1.53. The policy's turning authority in place is about 0.010-0.015 N m.

## Reading

The policy and heading hold turn steadily in every sim condition without an external torque, so they do not explain
the stall. The robot's pattern fits an external yaw torque of about 0.015-0.02 N m that opposes the turn in either
direction and builds up as the turn goes on. The duck runs tethered to a USB-C PD charger lead (CURRENT-STATE `power`,
no battery on the robot); a lead dragged or wound by the turn gives that torque (0.1 N at 0.1-0.2 m). This is not yet
observed directly: the discriminating check is the same turn with the lead held up above the robot so it cannot drag
or wind. Stepping in place without turning then would rule the lead out.
