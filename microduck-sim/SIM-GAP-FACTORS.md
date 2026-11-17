# MicroDuck sim-to-real gap factors

The base list every sim-to-real gap analysis starts from. List 1 is the complete factor tree; list 2 keeps only the
open candidates: a factor leaves it only with evidence that it is small on this robot or already modelled in the sim
with its measured value. Being hard to measure is never a reason to drop a factor.
Current values live in `CURRENT-STATE.json` (fact names in brackets), never in this file.

Structure: a pyramid, at most four children per node, children MECE under the split named at the node
(rule `~/code/claude-config/rules/common/managing-up-communication.md` §2). Agreed with Shawn 2026-11-17.

Leaf tags (cross-cutting, never branches): **F** fixed / **V** varies with time or use; **E** encoder sees it /
**X** needs an external measurement; **U** differs between units of the same servo or part.

## List 1: all factors

The gap comes from the four parts of the sim model not matching the robot (split: model component).

1. **Actuation: the servo does not match its model** (split: the servo model's parameter classes)
   1. Static accuracy: does not reach the commanded position
      - Internal servo backlash [V E U]
      - Stiction deadband: small commands ignored, worse under load [V E U]
   2. Dynamic response: wrong speed or timing
      - Gain: XL330 P acts as P/256 [F E]
      - Lag: real 4-5 ticks, sim 7 [F E U]
   3. Operating conditions: same servo, different behaviour
      - Supply voltage: real 7.2-8.2 V, sim constant [V E]
      - Temperature: torque drops when hot [V E U]
2. **Structure: parts and joints do not match the model** (split: the model's four structural assumptions)
   1. Dimensions and zeros differ from CAD
      - Part dimensions: printed length [F X U]
      - Assembly zero: horn one spline tooth off, software zero wrong [F X]
   2. Parts are not rigid
      - Elastic deformation: bends under load, returns; print layer direction matters [F X U]
      - Permanent deformation: creep, heat softening [V X]
   3. Joints are not ideal
      - Play in the rotation direction [V X U]
      - Play in other directions (fit between horn, shaft and part) [V X U]
      - Range limited by part interference [F E]
   4. Mass distribution differs from the manifest
      - Part mass and centre of mass: infill against solid-CAD estimates [F X]
      - Position of electronics and battery [F X]
3. **External forces: forces the model does not have** (split: source)
   1. Cables
      - Stiffness pulling on head and neck (USB camera lead) [V X]
      - Cable weight shifting the centre of mass [F X]
      - Cable snag limiting range [V X]
   2. Ground
      - Friction coefficient: slip [V X]
      - Contact stiffness and damping: impact [V X]
      - Sole geometry: shape and flatness [F X U]
4. **Sensing and control: signals and timing differ from training** (split: the three stages a signal passes)
   1. Sensor
      - IMU mount offset [F X]
      - IMU latency [F X]
      - IMU mount vibration [V X]
   2. Communication
      - Dropped servo reads [V E]
   3. Computation
      - Loop stalls [V E]
      - Processing mismatch: filters and action scaling differ from training [F E]

## List 2: open candidates

List 1 minus the six factors below. Every other leaf stays open, including all unmeasured ones.

Removed, each with its evidence:

1. **Actuation**
   - Gain: the sim's XL330 model uses the same P/256 the register dump confirmed (10/15), and static knee sag matches
     (sim 0.041 rad, robot 0.05)
   - Supply voltage: the sim runs at the measured walking voltage (`robot_state_check.py --print-sim-args` passes
     `--volt` from [servo_rail_v])
2. **Structure**
   - Part dimensions: bounded small. Assumption, not measured: FDM holes within about 0.2 mm on 50 mm links give
     under 0.3 deg and 0.5 mm, an order below the gaps seen ([leg_play] 7 deg, [head_pose_vs_chain_scan] 10 deg)
3. **Sensing and control**
   - IMU latency: measured with no delay beyond the normal pipeline, which the sim has [imu_added_delay_ms]
   - Dropped servo reads: the sim runs at the measured fraction (`--drop` from [servo_read_drop_fraction]), and
     adding them did not raise sim jitter (10/17)
   - (IMU rate is fed the same way through `--imu-hz`; it was never a list 1 leaf.)

Open candidates with a direct lead from an observed gap, so they are examined first:

- [leg_play] left single stance, trunk pitches about 10 deg beyond the encoders (sim 3): play in either direction,
  elastic deformation of the left leg or foot, ground contact
- [stand_posture_asbuilt] lean with the left sole's outer edge 5-6 deg low: assembly zero, IMU mount offset,
  elastic deformation, sole geometry
- [head_pose_vs_chain_scan] about 10 deg constant at trunk or neck: assembly zero, IMU mount offset, cable stiffness
  on the head
- Trunk gyro shake 4-6 times the sim at 5-25 Hz with matching joint spectra (10/17): play, deformation, ground
  impact, IMU mount vibration
- [ankle_bend_stall] ankles stop at 1.25 rad in the bend: range limited by interference (plug against the foot)
