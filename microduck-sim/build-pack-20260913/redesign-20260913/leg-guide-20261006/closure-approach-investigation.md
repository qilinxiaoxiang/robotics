# Lower-link closure approach: stop before the fork

Problems P5/P6. Checked 2026-10-07. This new test moves the **lower link only**, unlike the earlier blocked preassembled link/motor/ring group. Its purpose is to make operation7 understandable by showing a source-based approach that stops before material contact. It does not validate complete closure.

## Scene and direction

The isolated bench subassembly contains the ankle, small sleeve and bare ankle motor. The lower link is the only moving solid. Screws, wires, the thigh and the knee are absent obstacles; the previously assembled thigh is outside this bench scene.

The source sleeve/boss axis is world Y. Approach from the passive side: left starts at world translation `[0,-12,0]`, right at `[0,+12,0]`. Keep the source orientation unchanged. Six cardinal-direction coarse probes informed this choice: the coaxial passive-side route was clear at10mm offset, whereas other routes encountered the motor or fork before approaching the seat. This is an engineering choice for an explanatory stopped preview, not documented author assembly instructions.

## Measured stopped motion

- Left lower30, fixed ankle66/sleeve62/motor6: stop at `[0.0, -6.91339111328125, 0.0]` mm. All approach samples have zero measured intersection against all three fixed parts. Minimum endpoint separation is 0.383031399mm.
- Right lower32, fixed ankle64/sleeve68/motor1: stop at `[0.0, 6.9178466796875, 0.0]` mm. All approach samples likewise have zero measured intersection. Minimum endpoint separation is 0.382364781mm.

The original route is sampled at0.25mm. The first overlap greater than the unchanged0.02mm³ criterion is bracketed by12 binary refinements (bracket width0.000061035mm). The visual stop retreats0.5mm from that boundary and is independently required to have zero intersection plus a positive endpoint gap; it is not the slightly penetrating threshold sample.

For the left, first criterion crossing is `[0.0, -6.413330078125, 0.0]` mm and the pair is `lower--ankle` with 0.020019778mm³ intersection. For the right it is `[0.0, 6.41778564453125, 0.0]` and `right_lower--right_ankle` with 0.020030211mm³. The first blocker of this chosen lower-only approach is the orange fork. Do not label it with the older group's sleeve/ankle collision or its16.48mm offset.

## What the guide should show

Use `CLOSURE.paths[buildSection]`. Its start/stop vectors are deltas added to the unchanged assembled mesh. `animation.frames` uses world millimetres and xyzw quaternions. At progress1, the lower link stays at `stopTranslation`; this is the visibly separated stopped pose, **not** the nominal assembled target. Highlight `contactPair`, show the approximate0.38mm remaining gap and explain that continuing this straight approach encounters the fork.

`contactTranslation` is an evidence point only; do not use it as the displayed endpoint. `thresholdLastSafeTranslation` is safe only under the volume threshold and may contain microscopic intersection; use `stopTranslation`/`lastClearTranslation`, whose intersection is0. Keep the ring/boss fit checkpoint explicit. The nominal target still has about14.9586mm³ sleeve/boss material overlap, so this work does not certify a fully rigid final fit. No force, tightening, elastic compliance or actual printed-fit result is simulated.

## Identity and evidence

The runnable investigation rereads the original community3MF and directly checks all six participating printed source IDs against their actual guide transforms, matching triangle counts and bidirectional vertices within2e−5mm float serialization tolerance. It imports all eight world meshes into the Manifold solid kernel with `NoError`, computes actual-solid intersection and endpoint separation, and binds decoded position/index SHA values and source transforms. The manufacturer motor STEP, original assembled XML and PROJECT-CONTEXT are separately file-hash bound.

The whole full-build JSON file hash is deliberately excluded to avoid a circular dependency if the guide embeds this report. Each actual participating geometry payload remains independently bound. Finite sampled clearance is not a continuous mathematical path certificate. Physical assembly, flexibility, tolerances and fit remain unverified; no CAD, viewer, full-build data or print project was changed.

Recompute with the existing CAD Python environment and `closure-approach-investigation.py`; it writes only its owned JSON. Expected marker: `CLOSURE_APPROACH_INVESTIGATION_PASS`.
