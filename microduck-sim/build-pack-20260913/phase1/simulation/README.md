# Phase 1 gait and stopping regression

The final candidate passed **33 of 33** simulated mass/perturbation cases at the original walking gate plus a stronger stopping check. The jaw remains physically represented in the source head inertia and held closed for these gait runs; this does not simulate object pickup.

## Candidate configuration

- Use the frozen official 61-input standing policy for the initial two seconds.
- Once movement starts, keep the frozen official 61-input walking policy active. To stop, set forward and sideways velocity commands to zero while retaining heading feedback.
- Forward command is 0.30 m/s. Actual model speed is reported below; the command is not a measured robot speed.
- BAM proportional gain is 275, nominal5V, current-model limit1.47A, action delay20ms. This is a model/commissioning candidate; the physical safety monitor remains independently required.
- Heading feedback gain2, yaw-rate-command ceiling0.8rad/s, continuing after translation stops. No policy-output blending.
- Prediction is disabled. The program does not infer sensor sample age from host receipt age.

The real runtime must match policy selection, action ordering, command scale, gain and stop behavior before the simulation is considered applicable. Sensor I/O and motor behavior remain hardware measurements.

## What changed and what was tested

The Phase 1 mass manifest removes the new onboard battery, both regulator boards, camera, amplifier, speaker and their deferred mounts. It retains Pi, OpenRB, IMU, structural torso support, empty regulator cover, current jaw support/cap and fuse carrier. Source-model inertias combine several components, so original battery removal is swept as0/60/120g rather than pretending one teardown mass is known. Head fastener and wire allocations remain explicit; extra20g and40g trunk-harness cases extend the retained25g allocation.

The first27 cases retain the prior controller settings and abrupt walk-to-stand switch: **20/27 pass**. Seven failures are retained in mass-regression.json. This exposed a real mass-dependent startup/stopping regression. Candidate scans and unsuccessful blending results remain in this directory; they were not removed from the record.

The final33 cases span three old-battery mass hypotheses. Each has a baseline,4.75V,4.0V,5.25V,friction0.6,40ms sensor delay,40ms action delay, velocity perturbation, initial joint noise, extra20g harness and extra40g harness. Perturbations are applied one at a time, not every combination. The model completes30s with no fall, no solver warning, no non-foot floor contact, average x speed at least0.03m/s, maximum trunk tilt at most30 degrees and heading deviation at most30 degrees in the original scoring window. The new stop test sends zero translation at25s and requires no more than20mm maximum planar movement from the27s position through30s.

An extra9-case no-prediction check covers three masses at0/20/40ms sensor delays and passes9/9. The final33-case report also has prediction disabled, including its40ms cases. No claim is made about unknown longer physical delays.

## Quantitative readback

- Modeled total mass: 691.0091–851.0091 g.
- Mean forward speed in existing scoring window: 0.1009–0.1814 m/s.
- Maximum trunk tilt: 4.7555–7.0423 degrees.
- Maximum heading deviation in scoring window: 4.7414–15.4284 degrees.
- Final three-second maximum planar excursion: 0.0741–0.8137 mm.
- Mean walking current proxy summed over14motor channels: 2.2344–3.6295 A.
- Peak summed motor current proxy: 4.3670–6.6115 A.

The current numbers are torque-based model proxies, not battery or DC-supply current measurements. They exclude jaw actuation and do not establish the5A supply budget. The original model contact geometry approximates the community printed feet; friction and print compliance are not measured. The visual manifest also removes the source bearing mesh family while retaining the original non-jaw lumped inertias; this has no collision role because those source meshes are visual-only. No flexible cable, tether force, actual fuse, supply transient, hardware temperature or printed strength is simulated.

Command0.20m/s was checked in seven mass/voltage cases: six remain nearly stationary and fail the required forward-speed gate, while one passes. Reducing the policy command is therefore not established as a way to obtain slower walking. Physical commissioning starts with a supported robot and bounded movement, measuring actual speed before releasing it.

## Reproduce

From the Phase 1 directory:

```sh
/tmp/microduck-cad-venv/bin/python build_assembly_evidence.py
/tmp/microduck-dynamics-venv/bin/python run_mass_regression.py
/tmp/microduck-dynamics-venv/bin/python run_candidate_regression.py
```

The original evaluator, input mass manifest, geometry and source print files remain unchanged; source-hashes.json records their hashes. Final run inputs and their hashes are recorded in final-evidence-hashes.json. Full trajectories accompany every case, and candidate-before-heading, candidate-kp300 and candidate-with-prediction preserve earlier candidate results. Source evaluator differences are confined to Phase1's independent copy. This evidence supports proceeding to measured assembly/commissioning, not a promise of successful first-power walking or physical pickup.
