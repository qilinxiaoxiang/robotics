# Registered XL330 ports: one left-knee station

Checked 2026-10-09. This is an independent source registration and local assembly review. It changes no motor, print, electrical topology or published tutorial.

## What is now known

The ROBOTIS-authored `X330_3d.stp` contains two named **B3B-EH** header solids, indices 13/14. Their three square pins have 2.5 mm pitch. Both insertion axes point in the same direction; the two opposite side locations do not imply opposite insertion directions.

In the existing guide's motor-local frame, the mouth references are **[8.4, −7.7, −9] mm** and **[8.4, +7.7, −9] mm**. Both outward directions are **+X**; insertion is **−X**. The reference is the shroud mouth plane through the pin-row centre, not a motor bounding-box centre. `registered-ports.json` supplies the exact rigid transforms and the source STEP-to-motor transform. It does not infer electrical pin order from world left/right.

For left knee ID7, the two references are approximately **[−39.4771, 63.4, −30.5]** and **[−24.0771, 63.4, −30.5] mm**; withdrawal is world **+Y**. Eight shroud-mouth and pin-end surface witnesses from the manufacturer CAD agree with the actual guide mesh within **0.00000153 mm**. This measures digital registration, not production tolerance. The STEP itself declares about 0.00494 mm assembly closure uncertainty.

The broader 20-face centroid screen was retained, including its failed 0.03 mm criterion: centroids of trimmed faces are not necessarily points on those faces. The mouth/pin registration uses explicit surface witnesses, not a relaxed whole-surface threshold. The separate centroid diagnostic records the source-face distance for those points.

## What the actual local test shows

The reviewed station contains thigh, knee motor7, motor8, black plate and knee ring7 after source step04. The six source case/rear fasteners were also checked using oversized bounding envelopes. Mating internals of the receiving header are outside this surrounding-part clearance test.

The complete EHR-3 receiving box uses the public JST dimensions: 9.5 mm row width, 3.8 mm thickness, and a 7.1 mm overall bound including the 0.6 mm lip. The seated depth uses the catalog's 8.1 mm top-entry assembly height from the identified header board plane. This is an external receiving envelope, **not a detailed mating-solid model or a certified stock tolerance**.

- Both seated housing envelopes clear the surrounding printed parts.
- A 20 mm straight approach from behind fails against the **orange thigh rear lip**, with maximum envelope intersections of 37.3321 and 36.1000 mm³ at 0.25 mm samples.
- Near seating, one envelope is clear through the last 3.0 mm and the other through 3.75 mm of the sampled stroke. These are local clearance observations, not certified electrical disengagement distances.
- The **black plate is clear for the entire tested housing and handling approaches**. Its opposite-side location is not a reason to remove it.
- A receiving allowance extending 2 mm around the housing and 12 mm behind it intersects the thigh. No hand or pliers access is certified. The neighbour-motor bound also intersects one expanded handling allowance; that bound-only result remains inconclusive.
- The six retained fasteners are separated from the entire housing sweep by conservative bounding-box checks; their omission is not being used to produce a false housing pass.

A large-envelope intersection is not proof that every actual housing tilt or side-entry method fails. Exact stock seating, a short axial stroke after side placement, and physical grip access remain unverified. There is no instruction here to dismantle a completed leg.

## Bounded improvement: pre-seat the knee plugs

Use the source step01 motor approach, **[0, −45, 0] → [0, 0, 0] mm**, before adding the black plate. Carry the two housing envelopes with motor7. Both added bodies have **zero intersection** with the actual thigh and a conservative bound of motor8, for an exact continuous rectangular sweep and 181 sampled positions per pair. `preconnected-delta.json` preserves this positive result against the failed post-closure approach.

This supports reviewing **knee lead preconnection before source step01**. It does not qualify the whole prewired assembly: wire departure, bend and slack, strain relief, both lead destinations, actual seating and grip must still be checked. The previous bare-motor test does not automatically cover those remaining cable features.

## Files for the next review

- `registered-ports.json`: machine-readable local frames, current ID7 transform, evidence, source hashes and scoped station results.
- `xl330-registered-motor-local.step`: manufacturer motor in the guide motor-local frame; 12 valid solids, excluding the unused rear idler/cap/screw. `header-13-motor-local.step` and `header-14-motor-local.step` isolate the real headers. Native exports were read back and validated.
- `knee-station-initial.json`: all 81 positions for each tested approach/obstacle, including failures.
- `preconnected-delta.json`: added housing continuous-sweep and sampled checks for step01.
- `native-registration-readback.json` and `mesh-registration-check.json`: CAD validity and installed-mesh registration evidence.

Only this motor and station were reviewed. Do not assign these world coordinates to another motor; apply the relative frame to its independently confirmed source transform and review its local obstacles. No whole-robot or full-pose sweep was run.

The independent workers stayed under the existing 512 MiB/120 s guard. Two preparation/export attempts exceeded the guard and stopped; they are retained as failed receipts. Separating native export from the large tessellation read resolved the resource issue without raising the budget. Final native export used 450.5 MiB; readback used 452 MiB; station and preconnected checks used about 306/294 MiB.

## Primary geometry references

- [ROBOTIS XL330 manual](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/): connector type and pin functions.
- ROBOTIS-authored X330 STEP and drawing in `../../fastener-audit/sources/`; their existing source register records the distributor-hosted original files.
- [JST EH catalog](https://www.jst-mfg.com/product/pdf/eng/eEH.pdf): EHR-3 dimensions, header and mated height.
- [JST product CAD index](https://www.jst-mfg.com/product/index.php?series=58): detailed EHR-3 CAD is currently sent by email after company/name/email submission. No personal information was submitted. The saved HTML requests are not STEP/PDF geometry and are named accordingly.

AI assistance was used to draft.
