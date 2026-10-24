# MicroDuck foundation, 2026-10-23

This is the state of the CMU MicroDuck on the evening of 2026-10-23, the point at which Shawn declared the
current stage finished: "the functions we have now are the foundation; we can already train reinforcement
learning on top of it." Everything after this line is an extension (see the last section) and is tracked
separately. Current measured facts live in `CURRENT-STATE.json`; this file records what exists and what was
shown, with dates. Decision record: `DECISIONS.md` D-024.

## The robot as built

A 15-servo bipedal duck after Pollen Robotics' open-source MicroDuck, built from AI-FanGe's community build
tutorial (MIT) with our own changes, assembled at the CMU Robotics Club between 2026-09-30 and 2026-10-13 and
modified since. Four hardware blocks:

1. **Printed body** (looks and structure): the community part set (89 parts) plus our incremental releases
   V1.6 to V1.28 that are on the robot: the rear converter pack and its cap, the A7Z head cap and face
   (V1.17), the split ankle with slip-fit feet and bike-inner-tube soles (V1.22/V1.24/V1.25), the one-piece
   right lower-leg link (V1.28), and the battery backpack frame (V1.20, being replaced by V1.31). Colour scheme
   C: white shells, thighs and head cap, yellow and orange accents, black links. Printed on the RoboClub Bambu
   X1C and Elegoo Centauri Carbon.
2. **Servos and controller** (motion and skeleton): 15 ROBOTIS XL330-M288 in one daisy chain on a ROBOTIS
   OpenRB-150 running our `openrb_dual_host` firmware: the Mac drives the bus over USB for bring-up, or the head
   board drives it alone over the J12 UART at 500 kbaud. All servos run Shutdown 52 so they keep torque above the
   7.0 V default ceiling. Hip horns were refitted mechanically to remove play (ID5 half a turn 2026-10-19, ID3 a
   quarter turn 2026-10-23); every joint is read against a stance check before torque is enabled.
3. **Brain and senses**: a Radxa Cubie A7Z (Allwinner A733) in the head runs the 50 Hz control loop, the ONNX
   walking policy and the camera; a BNO085 IMU on TWI7 (engine-mode overlay) at a full 50 samples per second;
   a MAX98357 I2S amplifier and speaker (-3 dB software ceiling, real duck recordings); a Seeed XIAO ESP32-S3
   touch board reading five copper pads inside the head cap (L1, R1, L2, R2, M) over I2C, a sense the official
   MicroDuck does not have; the Radxa Camera 13M 214 (CSI) in the eye. The A7Z reaches the Mac over Wi-Fi and
   Tailscale. Known limit: in the closed V1.17 head the SoC reaches 85 C within minutes and the thermal governor
   caps both CPU clusters at 416 MHz; the 50 Hz loop then falls to about 36 Hz and the walking policy diverges.
   Shawn's working figure is about 30 minutes of running per session before the head must cool.
4. **Power**, two routes:
   - USB-C PD route (in daily use): a 20 V USB-C PD source into an Adafruit 5991 (HUSB238) decoy, then two
     XL4015 buck converters in the rear pack: #1 at 7.0 to 7.3 V to the OpenRB J4 for the servos, #2 at 5 V to the
     A7Z header. The source is either a 20 V 5 A wall charger or a power bank; on 2026-10-23 Shawn ran the robot
     from a Xiaomi 212W HyperCharge Power Bank 25000. A 20 V 3 A (60 W) charger folds back at the walking current
     peaks and freezes the A7Z (2026-10-22).
   - Battery route (D-010, parts bought, backpack being made, not yet installed): a Tattu 2S 650 mAh LiPo
     straight to the servos through an XT30 switch, a DFRobot DFR1202 in the same backpack making 5 V for the
     A7Z over an MR30 joint. Swapping backpacks is two plugs.

## What the robot does today

- **Stands and walks** on Pollen's official policies (`walk61` = BEST_alpha_walking, `stand61`, `groundpick61`)
  at 0.25 m/s, with KP 200 in policy modes and KP 400 in the open-loop stand. First free stand 2026-10-13, first
  walks 2026-10-16 (Pi Zero W head), A7Z head since 2026-10-18.
- **Walks straight and turns on command** (2026-10-22/23): a heading hold in `walk_brain.py` adds a learned yaw
  trim plus a PI loop on the IMU heading; arcs are held by the IMU too. Robot arcs reached 15 deg/s on the left;
  right arcs are limited by the robot's own left drift (left knee gives under load, left stance twice as long).
- **Head touch** (2026-10-20/21): all five pads work; a head grip during a walk stops the walk and holds the
  robot (graded hold, 2026-10-23: 6 of 6 lifts held).
- **Quacks** with the jaw moving (2026-10-23 fix: the jaw is pressed shut after the quack and held closed).
- **Sees**: the head camera streams the duck's-eye view into the MicroDuck desktop app's camera window
  (2026-10-23); the orange-target detector locked 57 of 57 frames and projected the target to the floor to
  1 mm on the earlier Pi camera, and must be recalibrated on the Radxa camera.
- **Reports itself**: a 10 Hz flight recorder on the A7Z, per-tick logs on the Mac, a robot monitor and remote
  control page in the app, and a hold file that survives reboots.

## Simulation, training and the gates around them

- As-built MuJoCo model of this robot (measured and estimated masses, camera and mouth-tip sites, measured
  7.87 deg forward gap) and a seven-case acceptance suite (`brain_sim_check.py --model asbuilt`) that takes the
  servo rail voltage, IMU rate, servo read drops and added delay from `CURRENT-STATE.json`; harsher stress cases
  are reported but never used to accept or reject a policy.
- Reinforcement-learning fine-tuning of walk61 on Modal (L4): ft1 learned to stand still while total reward
  tripled; the cause was a per-term reward audit (standing already earns 80 % of walking's reward in Pollen's
  environment). Two code gates now stand before any run: a launch gate that refuses to start without a passing
  reward audit, and a training guard on velocity-tracking error that excludes bad checkpoints and stops the run
  (D-016). ft3 with a filtered velocity reward did not drift and is sim-better than walk61 (D-017); on the robot
  it fell at 0.20 m/s, so walk61 stays deployed.
- Learned jaw control in simulation (PPO on the M1 Pro CPU, 0/12 to 12/12), and the aiming-crouch environment
  for the pickup (groundpick61's crouch with an object the beak must reach), audited but not yet trained.
- The team training repository: `qilinxiaoxiang/microduck_rl` (Pollen's `develop` plus our `cmu/` layer:
  as-built model variants, the sim check, the robot runtime, the simulator and app, the fine-tune pipeline).

## Final goal and where each step stands (D-019)

1. Find the item (orange printed part) with the head camera: detector works, camera recalibration pending.
2. Walk to it: walks straight with the heading hold; stops and arcs on command; falls still happen.
3. Crouch with the beak open and keep balance: Pollen's closed-beak crouch shown; the open-beak crouch policy is
   the next training target.
4. Pick it up with the beak: current-mode grip holds a finger; no object picked up by the robot yet.

## Public record

- Public build repository: `github.com/qilinxiaoxiang/cmu-microduck` (procurement, printing, wiring, assembly,
  bring-up and runtime for this foundation; created 2026-10-24).
- Project page: `shawnxiang.com/microduck`.
- LinkedIn build log (Shawn's posts, read from the activity page on 2026-10-23):
  - 2026-10-13 "Meet CMU's first (?) Microduck. Half-built for now." https://www.linkedin.com/feed/update/urn:li:activity:7515635733777551360/
  - 2026-10-16 "Learning to walk." https://www.linkedin.com/feed/update/urn:li:activity:7516994475253059584/
  - 2026-10-23 "My handmade microduck can finally walk and quack!" https://www.linkedin.com/feed/update/urn:li:activity:7519503040069021697/

## Extensions after this foundation (not part of it)

- A7Z out of the head into a roof saddle with a copper heatsink and a 5 V fan (D-022, V1.29, printed set delivered).
- Innomaker U20CAM USB camera on the face with a dia 11 left-rear cable exit (D-023, V1.30, printing).
- Two microphones for sound localisation and voice.
- Camera stabilisation (software and hardware), in progress in a parallel session (literature pass committed
  2026-10-23).

## Acknowledgements

Pollen Robotics for the MicroDuck design, the training environment and the policies; AI-FanGe for the community
build tutorial and the Raspberry Pi runtime this build started from; the CMU Robotics Club for the printers,
tools and parts drawers.
