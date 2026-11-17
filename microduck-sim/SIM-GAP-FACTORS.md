# Sim-to-real gap factors

The base lists for analysing a gap between a robot and its simulation. List 1 is every factor; list 2 is what an
analysis checks, after removing the factors the sim model absorbs or that are minor. Measured values and findings
for a particular robot do not belong here: they live in that robot's `CURRENT-STATE.json` and analysis notes.

Structure: a pyramid, at most four children per node, children MECE under the split named at the node
(rule `~/code/claude-config/rules/common/managing-up-communication.md` §2).

Leaf tags (cross-cutting, never branches): **F** fixed / **V** varies with time or use; **E** encoder sees it /
**X** needs an external measurement; **U** differs between units of the same servo or part.

## List 1: all factors

The gap comes from the four parts of the sim model not matching the robot (split: model component).

1. **Actuation: the servo does not match its model** (split: the servo model's parameter classes)
   1. Static accuracy: does not reach the commanded position
      - Internal servo backlash [V E U]
      - Stiction deadband: small commands ignored, worse under load [V E U]
   2. Dynamic response: wrong speed or timing
      - Gain [F E]
      - Lag [F E U]
   3. Operating conditions: same servo, different behaviour
      - Supply voltage [V E]
      - Temperature [V E U]
2. **Structure: parts and joints do not match the model** (split: the model's four structural assumptions)
   1. Dimensions and zeros differ from CAD
      - Part dimensions [F X U]
      - Assembly zero: horn off by a spline tooth, wrong software zero [F X]
   2. Parts are not rigid
      - Elastic deformation: bends under load and returns [F X U]
      - Permanent deformation: creep, heat softening [V X]
   3. Joints are not ideal
      - Play in the rotation direction [V X U]
      - Play in other directions (fit between horn, shaft and part) [V X U]
      - Range limited by part interference [F E]
   4. Mass distribution differs from the model
      - Part mass and centre of mass [F X]
      - Position of electronics and battery [F X]
3. **External forces: forces the model does not have** (split: source)
   1. Cables
      - Stiffness pulling on the parts it spans [V X]
      - Cable weight shifting the centre of mass [F X]
      - Cable snag limiting range [V X]
   2. Ground
      - Friction coefficient [V X]
      - Contact stiffness and damping [V X]
      - Sole geometry [F X U]
4. **Sensing and control: signals and timing differ from training** (split: the three stages a signal passes)
   1. Sensor
      - IMU mount offset [F X]
      - Sensor latency [F X]
      - IMU mount vibration [V X]
   2. Communication
      - Dropped reads [V E]
   3. Computation
      - Loop stalls [V E]
      - Processing mismatch: filters and action scaling differ from training [F E]

## Removal criterion

A factor leaves list 1 only for one of two reasons. Not having measured it is never a reason.

- **Absorbed by the model**: the sim takes it as an input or parameter set from one measured number, so once that
  number is measured the factor no longer produces a gap. Gain, supply voltage, sensor latency, dropped reads.
- **Minor**: its effect is bounded below what the analysis can resolve. Part dimensions, bounded by print tolerance.

## List 2: factors an analysis checks

1. **Actuation**
   1. Static accuracy
      - Internal servo backlash
      - Stiction deadband
   2. Dynamic response
      - Lag
   3. Operating conditions
      - Temperature
2. **Structure**
   1. Zeros
      - Assembly zero
   2. Parts are not rigid
      - Elastic deformation
      - Permanent deformation
   3. Joints are not ideal
      - Play in the rotation direction
      - Play in other directions
      - Range limited by part interference
   4. Mass distribution
      - Part mass and centre of mass
      - Position of electronics and battery
3. **External forces**
   1. Cables
      - Stiffness
      - Weight
      - Snag
   2. Ground
      - Friction coefficient
      - Contact stiffness and damping
      - Sole geometry
4. **Sensing and control**
   1. Sensor
      - IMU mount offset
      - IMU mount vibration
   2. Computation
      - Loop stalls
      - Processing mismatch

## Measurement methods

A method is listed only if it gives a number, follows a fixed protocol (fixed script, pose, load and repeat count),
repeats within a stated spread, and one person can run it in minutes. Anything that relies on a hand holding or
pushing a part fails the protocol test and is not listed.

Split: the instrument that produces the number. Tags (cross-cutting): **P** passive, uses logs of normal runs;
**A** active, a dedicated motion script; **C** control, change one condition (cable on or off, floor, load) and
compare before and after.

1. **The robot's own sensors** (split: which signals are compared)
   1. Command against encoder: fixed step, sweep and full-range scripts per joint; output lag, deadband width,
      reached fraction, range end and the current spike at it [A C].
      Covers: stiction deadband, lag, range limited by part interference, cable snag; with C, cable stiffness.
   2. IMU against encoder kinematics: trunk attitude from the IMU against the attitude the encoders and the rigid
      model give, in fixed stances; output the residual, split by load and by motion direction [P A].
      Covers: assembly zero, IMU mount offset, play, elastic deformation (as one sum, separated by method 2.2).
   3. Run statistics: servo temperature registers, loop time, dropped reads, over each run [P].
      Covers: temperature, loop stalls.
   4. Replay: feed recorded robot observations through the training environment's processing code and compare the
      outputs term by term [P].
      Covers: processing mismatch.
2. **External camera** (split: what the camera tracks)
   1. Markerless pose: fit the CAD model to each frame; output trunk and link angles against the encoders [P A].
      Covers: assembly zero, large deformation, whole-chain residual.
   2. Marker tracking: printed fiducial markers on each link, high frame rate; output each link's six-axis pose
      against the encoders and the IMU [A C].
      Covers: play in both directions, elastic deformation, IMU mount vibration, internal servo backlash
      (with the link loaded by gravity in a fixed pose).
   3. Foot contact video: side view, high frame rate, fixed floor and step script; output slip distance and
      impact duration per step [A C].
      Covers: contact stiffness and damping, friction in use.
3. **3D scan** (split: what is compared)
   1. Scan against CAD in a fixed pose; output per-part pose and shape error [A].
      Covers: assembly zero, permanent deformation (repeated over time), electronics position, sole geometry.
   2. Scan pairs of the same pose under two loads; output the difference [A C].
      Covers: elastic deformation.
4. **Bench measurements** (split: the quantity measured)
   1. Weighing and suspension: weigh each part and cable, hang the robot from two points for the centre of mass
      [A].
      Covers: part mass and centre of mass, cable weight.
   2. Tilt test: sole on a board of the floor material, raise it until slip; friction coefficient is the tangent
      of the angle [A].
      Covers: friction coefficient.
   3. Locked-output sweep: the link held in a fixture, the servo sweeps slowly at a low current limit; output the
      zero-current band (play) and the slope (stiffness) [A].
      Covers: play in the rotation direction, elastic deformation, internal servo backlash.
