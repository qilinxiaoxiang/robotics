# Non-head assembly review — 2026-10-08

This review advances P5/P6: a seated assembly is insufficient evidence for an insertion route or later driver access. It preserves the existing complete leg instructions and all ankle/foot geometry.

## Current corrections

The IMU clamp now approaches from −X. The previous +X path crossed the power support, regulator insert and regulator. `imu-corrected-path.json` records the replacement sampled against prior assembled parts. The canonical generator change is in `../reviewed_motion.py`; `source_compatibility.py` distinguishes that metadata change and the recorded canonical rebuild from unrelated geometry changes.

The closed torso rings must be installed before the upper yaw joints close. Six axial approaches for each entire finished leg into the torso core failed; this bounded search is not proof that every possible rigid motion fails. A working service route is now provided for any hip-yaw joint already fastened. It temporarily reuses seven screws on that side, leaves the four lower joints and their fasteners assembled, installs the loose torso rings/motors, then reconnects the intact lower leg. A side not yet fastened should not be assembled merely to undo it. A fresh build begins at service step 11 with loose yaw motors/links and separate four-joint units; the evidence covers these joining stations, not the entire fresh-build workflow.

The power support is installed last. Installing it before the two yaw-side case/rear attachments blocks four driver paths, recorded in `service-sequence-early-support-negative.json`.

## Authoritative service payload and gate

- `torso-service-steps.json`: 28 exact scenes, explicit moving groups, retained screw groups, extraction/insertion waypoints, screw removal/refastening IDs and action labels. `integrationReady` is set only by the gate.
- `verify_torso_service.py` → `torso-service-verification.json`: current source-bound geometry checks at 0.25 mm increments, plus refined final ring checks, retained screw envelopes and 34 straight driver paths. The source contact exceptions below are pair-specific; there is no global subtraction of seated overlap.
- `build_service_steps.py`: regenerates the payload with readiness false. Run the verifier afterward. The report binds this generator and the early-support negative control through `inputHashes`.

The content binding is SHA256 of UTF-8 `json.dumps` with `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=True`, after removing only `integrationReady` and `verificationSha256` from the payload. All scenes, paths, screw IDs, source metadata and text remain bound. The payload separately binds the final report bytes. A source change during the run fails verification.

## Narrow source-contact bounds

Existing motor9/yaw and motor4/right_yaw nominal contacts occupy a ≤0.00102 mm Z slab at Z≈−8 mm, volume ≤0.341 mm³. Only these named pairs may retain that thin contact during parallel X withdrawal/insertion. This does not accept new contact elsewhere.

Yaw/ring10_torso and right_yaw/ring5_torso source contacts occupy a ≤0.00101 mm Z slab at Z≈−5 mm, volume ≤0.0563 mm³, and are allowed only within 0.00101 mm of the seated endpoint. The last 0.003 mm are resampled every 0.0001 mm. Motor10/torso_base and motor5/torso_base permit only their numerical seated intersection in Z≈0…0.00000017 mm, volume ≤0.00002 mm³, with translation norm ≤0.000001 mm.

These are exact digital source bounds, not measured assembly tolerance. The shaft and head envelopes follow the source screw axis, length and washer offset; the head is the guide's conservative Ø5 × 1.5 mm envelope. Tool clearance checks a Ø3 mm shaft from 0.5 to 40 mm outward from the same head origin. No claim is made about an unmodelled handle, cable routing, printed stiffness, torque or physical fit.

## Remaining scope

The existing power-carrier paths and neck staging were checked against cumulative assembly context. Original shell/neck source-fit contacts are preserved as source limitations and are not newly certified as physical fits. This review does not change completed ankle/foot joints. No new hardware is required for the torso service route.
