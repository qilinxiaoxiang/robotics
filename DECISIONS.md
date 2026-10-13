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
