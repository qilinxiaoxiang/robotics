# MicroDuck sim-to-real gap factors

The base list every sim-to-real gap analysis starts from. List 1 is the complete factor tree; list 2 keeps only the
factors we already measure; the removed factors are the blind spots, where an unexplained gap is most likely to hide.
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

## List 2: factors we already measure

Same tree, unmeasured leaves removed; a node with no measured leaf is removed.

1. **Actuation**
   1. Static accuracy
      - Stiction deadband: 10/15 gain sweep, unloaded probes [leg_joint_friction_unloaded]
   2. Dynamic response
      - Gain: register dump 10/15
      - Lag: tick logs, sim-real comparison 10/17
   3. Operating conditions
      - Supply voltage: servo-reported voltage in every walk [servo_rail_v]
2. **Structure**
   1. Dimensions and zeros
      - Assembly zero: scans through `scan-20261101/floor_truth.py`, `guide/firmware/mac/measure_gap.py`
        [sensor_and_zero_offsets_in_code, stand_posture_asbuilt, head_pose_vs_chain_scan]
   2. Joints
      - Play in the rotation direction, indirectly: trunk motion against leg encoders in stance [leg_play]
      - Range limited by interference: print gate `pairs.py`, bend scan [ankle_bend_stall]
   3. Mass distribution
      - Part mass and electronics position: sourced mass manifest, some parts estimated
        [battery_sim_model_20261104]
3. **Sensing and control**
   1. Sensor
      - IMU mount offset [imu_mount_trim]
      - IMU latency [imu_added_delay_ms]
   2. Communication
      - Dropped servo reads [servo_read_drop_fraction]
   3. Computation
      - Loop stalls: `loop_ms` in every tick log
      - Processing mismatch: code compared with Pollen's runtime 10/17

## Removed: not measured, or hard to measure

Each removed leaf and why. A gap that list 2 cannot explain is looked for here first.

1. **Actuation**
   - Internal servo backlash: never separated from joint play
   - Temperature: servo temperature is readable but not logged; only the A7Z SoC is
2. **Structure**
   - Part dimensions: not measured; scans resolve about 2 mm
   - Elastic and permanent deformation: need a fixture or a camera on the part
   - Play in other directions: encoders cannot see it, no external measurement yet
3. **External forces** (whole branch)
   - Cable stiffness, weight and snag: not measured
   - Ground friction, contact stiffness, sole geometry: not measured
4. **Sensing and control**
   - IMU mount vibration: trunk gyro shake is measured, but not separated from impacts and play

Example of why this matters: [leg_play] shows the trunk pitching about 10 deg beyond the left leg's encoders in
left single stance (sim 3 deg). List 2 sees the gap; its cause lies among the removed leaves (play in other
directions, part deformation, ground contact).
