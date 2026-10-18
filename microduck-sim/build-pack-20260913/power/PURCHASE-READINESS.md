# Historical Phase 2 reference — not a purchasing route

The active build is [Phase 1 single-source revision](../phase1/START-HERE.html). The battery, two-regulator, charger and related figures below are retained only as history. Do not use them to buy or wire Phase 1.

# Power purchase readiness

**Phase1nowuses the [current illustrated handbook](../phase1/START-HERE.html): complete15-servo tethered walking/pickup with Mean Well5V6A motor supply. Camera,audio,onboardbattery,regulatorsandcharger remainPhase2holds. The material below is earlier design/reference evidence and is not the current shopping instruction.**

The [sourcing policy](../procurement/sourcing-policy.json) governs every actual purchase. Raspberry Pi stays borrowing-first and RoboClub supplies printing materials, fasteners and general consumables first. The calculations and software checks below remain reference evidence for the deferred onboard design, not purchasing clearance. Historical store-cart observations require reconciliation before handoff.

## What the calculations do and do not settle

- The eight fused groups now supply **15 independent power tails**. In the assessed 20°C wiring/contact scenario, the lowest servo endpoint improves from 4.398V in the previous wiring/supply to 4.583V with independent tails and the new regulator tolerance. This is not a claim for every possible wire length, hot contact, simultaneous stall or battery state.
- Pi's fixed 5V regulator can legally output 4.85V at its −3% tolerance. With 2.25A through 200mm of 20AWG wire in each direction and an assumed 20mΩ combined connector/solder resistance, Pi receives **4.775V**, below our 4.8V requirement. Even a 100mm wire does not remove every contact-resistance case. The 288-case sensitivity is in [purchase-margin.json](purchase-margin.json). This is a genuine specification-margin gap, not proof that a purchased board has failed. First try the shortest fitted wire and screen loaded board/endpoint voltages. Do not raise voltage blindly or parallel the two supplies. [Regulator specification](https://www.pololu.com/product/4082)
- The design walking load assumption gives 3.26–4.85A at the battery and roughly 8–11 minutes. These are planning estimates. Fifteen simultaneous 5V stalls require 22.05A at the servo rail; this configuration must stop instead of sustaining that load.
- Calculated regulator loss is not a temperature result. The design walking assumption dissipates about 1–4.75W in the large regulator; enclosed thermal resistance is unknown. A bench result cannot automatically clear the enclosed print.
- Regenerative braking can raise the servo rail. Neither a 5V output label nor a generic “5V TVS” proves it stays below the 5.5V project ceiling. Capture the actual pulse before selecting a discharge circuit. [Pololu explanation](https://www.pololu.com/category/249/shunt-regulators)

## Software gaps repaired locally

The original scheduler already requests torque-off when exiting normally, on Ctrl+C, on its stop file, or after repeated serial-read failures. Its normal mapping includes only 14 joints. The 61D walk adapter's fall branch merely stops changing targets; it does not itself remove holding torque. IMU age was only a warning. Model loading can also fail after startup has already enabled torque.

The independent [supervised launcher](runtime-supervisor/README.md) now:

- Checks the actual body orientation and host-receipt age before motion; at 60° tilt, invalid IMU or more than 100ms host age it requests torque-off for IDs **1–15**, including the jaw.
- Reads all 15 actual servo input currents at up to 10Hz. Sustained readings above 5.0A total, 2.25A in a fused group, or 1.3A in one servo trigger a latched stop after a 200ms observed dwell. These are conservative bench-screening thresholds, not a mode-3 hardware current clamp or validated grip control.
- Prevents re-enabling after a trip, requests torque-off during startup/model exceptions and process exit, and imposes a default 120-second supervised session limit.

It passed **19 fault-injection tests using the real community Observer, Scheduler, main and IMU conversion with substituted hardware**. It has not run on the Pi or changed the original repository. Extra current reads consume bus time; the existing gait-delay acceptance must be rechecked on the Pi before walking. No claim of bounded physical stop latency follows from these tests. A weakly loaded stalled joint can remain below the current threshold, so obstruction detection is not universally solved.

## Actual stop chain and remaining hardware gap

1. If the process, IMU and bus work, the supervised launcher detects its conditions and sends `Torque Enable=False` to all 15 IDs. The request must be verified on the bench; a successful serial write is not a readback of disabled torque.
2. If the process hangs, the bus fails, the Pi loses power, or a remote Wi-Fi command stops arriving, this software is not an independent power cutoff. The operator supports the robot and moves the physically accessible switch to ground the large regulator's ENA pin. OpenRB's reset or DXL indicator is not that switch.
3. EC2 disconnection removes the battery feed to both regulators. The balance-port alarm remains powered until its connector is also removed.
4. The cell alarm is audible only. The Pi has no installed per-cell ADC, the alarm has no validated digital interface, and regulated servo voltage cannot reveal raw battery cell voltage. Software cannot invent those readings. A session timer is not low-voltage protection. Keep this prototype attended, plan to stop near 3.5V/cell under load, and treat 3.3V alarm as backup. Automatic unattended battery protection needs additional selected, mounted and tested hardware.

## Acceptance status

Recomputed seven load scenarios and 288 Pi margin cases. The existing 14 design/data-gate tests and the new 19 supervisor tests pass offline. The actual measurement template correctly returns **NOT_MEASURED_OR_INCOMPLETE, exit 2**. Hardware measurements performed: **zero**.

Before unsupported walking: verify Pi 4.8–5.25V, all 15 servo endpoints 4.5–5.5V including startup/deceleration, loaded cell voltages, actual fuse/connector/PLA/regulator temperatures, torque-off and ENA behavior, USB stability, and the additional current-read timing. Follow [FIRST-POWER-TEST.md](FIRST-POWER-TEST.md). This is the remaining acceptance work, not a reason to call the existing simulations power validation.
