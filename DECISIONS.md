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
- **Decision:** Supersedes D-006's 5 V rail. The robot is powered through one USB-C PD charger into the Adafruit 5991 set to 15 V, then two ROBOTIS OMX-AI kit XL4015 buck modules: one adjusted to 6.8 V (the "7 V rail": 6.75–6.85 V accepted) into the OpenRB-150 J4 (JP1 on VIN(DXL), every servo on that rail through the DXL ports), one adjusted to 5.0 V for the Raspberry Pi's two jumper leads. The three boards ride on the robot in a new two-piece rear frame and lid that replaces the pack cover, flush with the shells and no taller than them (layout F, `microduck-sim/guide/print/back-plate/layout-D-20261014/layout-F/`): both XL4015 lie horizontal and stacked (7 V on top, 5 V in the middle, IN ends on +y, OUT ends on −y), the 5991 lies at the bottom in a narrowed tier with its USB-C socket out of the −y wall; every screw terminal has a side window and its wires loop out and back into a lane behind the boards, so all runs are inside the box and reach the pack through one front passage; outer edges are rounded to follow the shells. The printed V1.8 pack stays as built. Layouts C2 (vertical boards, box raised above the shells), D (horizontal boards with no internal path to the IN terminals) and E (vertical boards, top windows) were rendered and rejected on looks and wiring on 2026-10-14. Still no soldering, no converter in the pack channel, no fuses. Two cables reach the floor: USB-C power and the OpenRB USB data cable.
- **Why:** The official Pollen policies that we run (walk61/stand61 are byte-identical to `BEST_alpha_walking.onnx` / `BEST_alpha_stand.onnx` from pollen-robotics/microduck-simulator) were trained with the bus voltage randomised in 6.5–8.2 V (`microduck_rl/src/mjlab_microduck/robot/microduck_constants.py:126`), and Pollen's robot feeds the XL330s straight from a 7.2 V NP-F550 pack (pollen-robotics/microduck issue 294). At 5 V the as-built simulation tolerates only 2.5 mm of forward COM error; at 7.4 V, 7.5 mm. A 6.8 V set point is inside the training range and 0.15 V under the XL330's Max Voltage Limit default (EEPROM 32 = 70, 7.0 V), so no servo register changes, the factory Shutdown value stays, and meter error or no-load overshoot cannot trip the over-voltage latch. The XL330-M288 e-Manual rates 3.7–6.0 V; running above it is Pollen's production practice, accepted here with the 7.0 V ceiling.
- **Order of work:** the free fixes come first (closed-loop takeover instead of the 1.5 s open-loop ramp, joint-zero and IMU-mount corrections from the three bench measurements), then the 7 V plate. Retraining is not on the plan unless both the official policy and the AI-FanGe community policy fail on hardware at 7 V with logged torque saturation.
- **Revisit when:** a servo reports Input Voltage Error or overheats at 7 V, the 5991/charger browns out at 15 V/3 A, or the XL4015 cannot hold 7.0 V under the measured walking peaks (`current` step).

## D-008 — MicroDuck audio: no GAIN resistor, software volume ceiling; speaker on foam tape

- **Date:** 2026-10-14
- **Decision:** The MAX98357A amplifier's GAIN and SD holes stay empty (default 9 dB gain); the 100 kΩ GAIN-to-Vin resistor planned on 2026-10-13 is dropped. The 1 W CMS-30204-18SP speaker is protected by the ALSA softvol ceiling `max_dB -6.0` in `/etc/asound.conf`, and programs play through the default device, never `hw:MAX98357A`. The speaker sits on a closed loop of 1 mm foam double-sided tape (two strips of about 40 x 1.5 mm) on the cap collar's lip ring instead of a cut foam ring; the speaker's factory metal grille faces the roof and does not replace the tape, which clamps the speaker and seals its edge. Bring-up step 13 is now five soldered wires, two speaker leads, meter check, Pi pins, Pi setup, listening test and the ceiling.
- **Why:** The datasheet gives output level = input (dBFS) + 2.1 dB + gain, so 9 dB with a −6 dB ceiling puts 0.4 W into 8 Ω at full scale, exactly what the 3 dB resistor setting gave at full scale. The resistor cost the only fiddly steps in the guide (lead forming, a hook round the Vin wire tail, Kapton, a paper shim, two meter readings) for no extra protection as long as the ceiling is in place. Shawn has no foam sheet; the 2026-10-13 handoff already allowed foam tape.
- **Revisit when:** a program is found opening the hardware device directly (then the resistor comes back as a hardware floor: about 1.6 W at full scale without it), or the ceiling does not read −6.00 dB on the real Pi.

## D-009 — MicroDuck converter box: hidden cap screw, solid front plate, wires over the top through a notch

- **Date:** 2026-10-14
- **Decision:** The layout F rear converter box (D-007) is released as V1.15 with three changes Shawn chose on 2026-10-14. The cap loses its two screw ears: it is held by its two top tongues, one stock M2 × 10 driven from a hole in the cap back down a column inside the cap into the Adafruit 5991's upper mounting boss, and a hook tab that engages the top edge of the 5991 terminal window when the cap is lifted onto its tongues. The front plate is solid: the wire passage P1 between the converter tiers is deleted. Every box wire leaves its terminal straight out through the side window beside it and runs outside the wall; the 7 V servo pair and the Pi 5 V lead climb the outside of the left wall, cross the box top and drop into the rear pack through a 9.2 mm notch at the front edge of the top wall, under the side-shell lip, hidden in the crevice between the box and the shell.
- **Why:** Shawn fitted the V1.11 geometry on the robot and found the passage made assembly hard and left a seam between the boards ("开了个洞不仅难装 而且两个板子中间又加了一条缝"), and the cap's screw ear looked like a tail. Routing the wires over the top keeps the box outline clean and needs no fold-back inside the box; the hidden screw reuses a stocked M2 length and the existing 5991 boss. The regenerated frame passes the layout checks (manifold, fit, wires, hip sweep with 9.25 mm minimum wire clearance, printability, insertion) and the guide's print gate.
- **Revisit when:** the printed V1.15 cap does not hold on the tongues, hook and single screw, or the four wires do not pass the notch under the shell lip with the 22 AWG pairs and the Pi jumper chains actually in hand.

