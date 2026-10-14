# Decision log

## D-001 — Treat the robotics thesis as the north star

- **Date:** 2026-08-04
- **Decision:** Treat robots as AI's interface to observe, act in, and learn from the physical world. The project exists to advance this direction, not to repeatedly relitigate it.
- **Correction retained:** A body alone does not create self-improvement. Goals, action-grounded prediction, verification, data selection, learning, safety, and deployment must form a closed loop.

## D-002 — Rank by problem importance before personal fit

- **Date:** 2026-08-04
- **Decision:** Choose work by its effect on the embodied self-improvement bottleneck. Existing skills may alter the route and probability of success, but not the definition of what matters.

## D-003 — Make the Embodied Iteration Engine the first flagship bet

- **Date:** 2026-08-04
- **Decision:** Build an open loop from rollout capture to success detection, failure diagnosis, corrective-data selection, policy update, regression testing, and deployment.
- **Why:** Independent frontier efforts now converge on learning from deployment, reward/success models, online corrections, and action-grounded evaluation. This is the gradient required for recursive improvement.
- **Revisit when:** Evidence shows that the loop does not improve task success or data efficiency across at least one simulated and one physical task.

## D-004 — Stay embodiment-agnostic

- **Date:** 2026-08-04
- **Decision:** Humanoids are important but not doctrine. The engine should work first on a tractable arm or simulation and preserve interfaces for humanoids, mobile manipulators, quadrupeds, and laboratory robots.

## D-005 — Keep personal context private

- **Date:** 2026-08-04
- **Decision:** Public documents contain the thesis, research decisions, and reproducible evidence. Personal facts remain in the private memory repository and are consulted locally when needed.

## D-006 — MicroDuck runs on USB-C 5 V with no soldered power wiring

- **Date:** 2026-10-13
- **Decision:** The robot's supply is a USB-C PD charger into an Adafruit 5991 (HUSB238) set to 5 V on the bench, a 22 AWG solid pair screwed into the OpenRB-150 J4 terminal, and two jumper wires sharing those screws for the Raspberry Pi. No converter, XT30, 12 V adapter or power soldering on the robot. Contract and review-passed picture: `microduck-sim/bringup/build/power-diagram/`.
- **Why:** The earlier 20 V and 12 V chains existed only to give headroom over *simulated* walking peaks (about 2 A mean, 5.4 A for 20 ms at 5 V) against the 3 A limit of USB-C PD at 5 V, and every converter route forced soldering on bare pads. Bring-up draws far less than 3 A. Measured evidence, not a simulation, decides whether a converter comes back.
- **Revisit when:** the guide's `current` step (OpenRB `current_watch.py`) or a charger brown-out shows the 5 V/3 A budget is exceeded. First response is the 5991 `ISet` cut (3.25 A request); only then a converter in the pack channel kept empty for it, with the 5991 switched to 12 V.

## D-007 — MicroDuck servo rail runs at 7.0 V from an onboard XL4015, Pi on its own 5 V

- **Date:** 2026-10-14
- **Decision:** Supersedes D-006's 5 V rail. The robot is powered through one USB-C PD charger into the Adafruit 5991 set to 15 V, then two ROBOTIS OMX-AI kit XL4015 buck modules: one adjusted to 6.8 V (the "7 V rail": 6.75–6.85 V accepted) into the OpenRB-150 J4 (JP1 on VIN(DXL), every servo on that rail through the DXL ports), one adjusted to 5.0 V for the Raspberry Pi's two jumper leads. The three boards ride on the robot in a new two-piece rear frame and lid that replaces the pack cover, flush with the shells (`microduck-sim/guide/print/back-plate/`): the two XL4015 stand vertically side by side, the 5991 lies flat at the bottom with its USB-C socket out of the −y wall. Still no soldering, no converter in the pack channel, no fuses. Two cables reach the floor: USB-C power and the OpenRB USB data cable.
- **Why:** The official Pollen policies that we run (walk61/stand61 are byte-identical to `BEST_alpha_walking.onnx` / `BEST_alpha_stand.onnx` from pollen-robotics/microduck-simulator) were trained with the bus voltage randomised in 6.5–8.2 V (`microduck_rl/src/mjlab_microduck/robot/microduck_constants.py:126`), and Pollen's robot feeds the XL330s straight from a 7.2 V NP-F550 pack (pollen-robotics/microduck issue 294). At 5 V the as-built simulation tolerates only 2.5 mm of forward COM error; at 7.4 V, 7.5 mm. A 6.8 V set point is inside the training range and 0.15 V under the XL330's Max Voltage Limit default (EEPROM 32 = 70, 7.0 V), so no servo register changes, the factory Shutdown value stays, and meter error or no-load overshoot cannot trip the over-voltage latch. The XL330-M288 e-Manual rates 3.7–6.0 V; running above it is Pollen's production practice, accepted here with the 7.0 V ceiling.
- **Order of work:** the free fixes come first (closed-loop takeover instead of the 1.5 s open-loop ramp, joint-zero and IMU-mount corrections from the three bench measurements), then the 7 V plate. Retraining is not on the plan unless both the official policy and the AI-FanGe community policy fail on hardware at 7 V with logged torque saturation.
- **Revisit when:** a servo reports Input Voltage Error or overheats at 7 V, the 5991/charger browns out at 15 V/3 A, or the XL4015 cannot hold 7.0 V under the measured walking peaks (`current` step).
