# MicroDuck assembly and wiring workbench

Use the existing [Mac mini assembly page](http://today.tailfc7c94.ts.net:8766/LEFT-LEG.html). `LEFT-LEG.html` is its bundled deployment artifact; do not open a local file as the review handoff. The existing filename is retained, but the build-section selector now covers both legs, torso, power carrier, IMU, neck, head/jaw, head electronics, camera and final head closure. The document embeds its actual geometry, viewer and wiring data; it works offline in a modern Chrome browser. Geometry is losslessly compressed inside the HTML.

Problem **P5 / P6**: identify the printed stock and fasteners, make hidden joints understandable, expose assembly-access problems, and prepare the unpowered harness. The evidence that changes an assembly decision is a measured hole/axis mismatch, insertion interference, actual fit, or verified electrical endpoint.

## Use at the workbench

1. Choose the build section. **Identify parts** shows their saved print colors and actual shapes; click a part card to isolate it.
2. **Prepare screws** lists the specified fasteners. Machine-thread screws with nuts and TAP screws are distinct. Screw heads and threads in the 3D preview are schematic; use the listed specification.
3. **Assemble** alternates placing parts with fastening or retention checks. Reviewed operations provide **Prepare / Assemble / Check** phases; cable prerequisites appear before the operation that closes the socket. Click a part or its button to highlight it. **Pull apart**, **Play insertion**, **Pause**, and the progress slider reveal the approach and seats.
4. **Where are the washers?** opens an enlarged separated stack. The highlighted metal washer retains its actual dimensions. All four leg rear-center washers, four camera washers and seventeen machine-joint nuts are represented. The camera hinge has one washer outside each ear.
5. **Ankle fitting check** compares two sampled clear partial motions with the blocked preassembled-group approach. The blocked example stops before overlap and highlights the small ring and orange ankle.
6. Complete **Wire** before closing the head. Choose the current module's cable list. Each leg has its own four routes; whole-robot power and head wiring have separate entries. **On robot · 3D** shows installed components and the selected cable route; click either endpoint to focus it. **Connector · 3D** enlarges the named terminals, Pi header, servo three-pin plugs or camera ribbon. **Pi header pin map** shows all 40 contacts in 3D. **Trace cable** reveals the selected route and can pause. Nothing on the page sends a print job, powers the robot or commands a motor.

## The ankle access finding

Do not treat a final assembled pose as proof that parts can slide into it. The untouched small sleeve has an approximately 9.65 mm bore against a 10 mm link boss; their nominal final solids overlap by about 14.96 mm³. The preassembled link/motor/sleeve group also collides with the orange fork during a straight approach.

For the left leg, the geometry investigation supports two isolated bench motions: put the sleeve into the empty fork from its inner side, then bring the loose motor into the fork from above. The lower-link closure remains a physical fit/compliance checkpoint. Operation 7 now animates the black lower link toward the loose ankle, stopping before the orange fork. Play, pause and the slider end at the measured stop, not the seated source pose. The ring/link isolation view explains the separate bore mismatch. Only after that fit succeeds should the scheduled fasteners be snugged and the ankle/link module connected to the knee. The page does not certify the printed part's flexibility or a complete collision-free assembly trajectory.

The right sleeve path also passed the sampled check. The native right motor/fork pose has a thin 0.00093 mm contact layer and does not pass the strict overlap threshold; its approach is explicitly a source-contact fit check.

Generic approach previews are illustrative. The dedicated ankle paths have finite sampled collision readback, not a continuous mathematical clearance guarantee. The original guide retains its source CAD and print dimensions. The separately labeled `ANKLE-REDESIGN.html` now presents an optional removable-side prototype; see `../ankle-redesign-20261007/README.md` for its independent checks and pending physical acceptance.

## Assembly-order review — 8 October 2026

The revised order fastens each hip-yaw output before its roll motor closes the tool opening, builds the perpendicular hip joints as separate subassemblies, and keeps the torso shells off until the neck rear-center screws are complete. Head yaw, head roll, Pi, camera and audio now have explicit bench-assembly stages. The final cap screws require the lower jaw held open about 30° with the upper pad still absent.

Use [ASSEMBLY-REVIEW-METHOD.md](ASSEMBLY-REVIEW-METHOD.md) for the reusable review procedure and [nonleg-assembly-audit.md](nonleg-assembly-audit.md) for the source-based findings. Tool-access checks, sampled insertion paths, nut holding/entry, cable routing and physical fitting are separate checks. Several source joints still have a measured obstruction or nominal interference; their previews stop before contact and the following fastening step is conditional on actual fitting. A successful stopped preview does not establish a complete assembly route.

## Sources and coverage

- `leg-data.json`: original left-leg source meshes and 35-hole fastener schedule; exact geometry retained.
- `full-build-data.json`: complete installed-part selection, source hashes, stock allocation, modules, per-hole fasteners and washer/nut envelopes.
- `closure-approach-investigation.json` and `.md`: side-specific lower-link approaches; each stops with about 0.38 mm surface clearance before the orange fork. `closure3d.js` owns the operation-7 explanation and controls.
- `assembly-path-investigation.json` and `.md`: actual-solid insertion checks, sampled paths, stop boundary and physical checkpoint.
- `assembly-wiring-source-map.json` and `.md`: community geometry, current redesign sources, official OMX-AI tutorial organization and electrical references.
- `wiring-guide-data.json`: current single-source endpoints, fused motor groups, DATA chain and physical header map.
- `full-guide-review.json`: independent source geometry, stock, motor placement and fastener-stack audit.
- `leg-assembly-access.json` and `nonleg-access-audit.json`: original trapped-tool regressions, corrected sequence checks and source-solid tool envelopes; the latter applies the open-jaw pose to actual obstacle meshes.
- `motion-path-audit.json`: sampled translations of the current operations, including their grouped, segmented and stopped approaches. Inspect its crossing count and final-contact records separately.
- `nut-approach-verification.json`: six cap-nut stopped approaches and their retained straight-entry failures; hand fitting and retention remain conditional.
- `head-shell-fit-check.json` and `audit-20261008/head-articulation-access.json`: source-bound shell approach and jaw articulation/access evidence. `nonleg-subassembly-paths.json` retains bounded component-path investigations rather than replacing the final integrated audit.
- `wiring-spatial-data.json`: 40 spatial anchors and 85 electrical segments across the same 51 connections; source CAD centers, proposed accessory positions and illustrative curves are explicitly distinguished.
- `wiring3d.js`: installed and connector rendering, endpoint selection and cable tracing.
- `serve_guide.py`: loopback-only, allowlisted threaded server for the existing port8766 URL; idle connections time out after three seconds.
- `bundle-manifest.json`: lossless embedded-data identity.

The 89 printed stock instances include retained alternatives and spare copies; not all 89 should be installed. The full-data coverage manifest explicitly allocates installed pieces and retained stock. Planned motor IDs do not establish the addresses currently stored in the user's motors. Mechanical alignment and motor-zero calibration remain separate.

The current electrical plan keeps the Mac as the controller/policy computer and the Pi as the sensor acquisition/forwarding node. Its physical USB motor bridge and software bus ownership still need commissioning. The available boards are a first-generation Zero W with a soldered 40-pin header and a Pi 3 Model B V1.2. Actual loose cable fit, polarity, loaded voltages, thermal behavior, joint fit and visual pickup have not been verified by this digital guide. DigiKey receipt and printed-stock completion are user confirmed; no new purchase or print is requested.

## Rebuild and check

The current source of scope and evidence is `../../../PROJECT-CONTEXT.json`, with its linked workflow. Use the current geometry and operation overlays; do not rerun the historical generators as a blanket rebuild. In particular, `build_wiring_guidance.py` and `build_wiring_spatial.py` regenerate the superseded fuse-array/numeric-chain plan. `build_full_guide_data.py` is the historical geometry baseline, not the current integration owner.

For current viewer changes, use:

```sh
python bundle_guide.py --full
node test_assembly_phases.cjs
node test_wiring_context.cjs
node test_checked_leg_wiring.cjs
```

The bundle applies current stock fasteners and the verified torso service sequence before the current assembly-motion overlay. The overlay binds each changed operation to its source and carries its tool/path receipts. Cable prerequisites use stable operation IDs, so reordering a step does not move its prerequisite to the wrong component. `build_leg_wiring_adapter.py` is the source-bound eight-route projection; rerun it only when changing that projection, preserving newer accepted power/head integrations.

Keep geometry work bounded and local to affected interfaces. Current checks must retain the old failed motion/tool position as a negative case. Run the project-linked design verifier before a hardware-plan handoff; its historical baseline pass does not release the active head/harness repair or physical commissioning.

For viewer-only changes, `bundle_guide.py --full` reuses the source-bound geometry without changing it. Run this serialization-only job under the existing resource guard in exclusive mode with a 768 MiB ceiling; the latest full body/IMU build took 15 seconds and peaked at 700 MiB. CAD workers retain their separate 512 MiB limits. Payload compression and final HTML output are streamed, and decompressed hashes are checked before the HTML is atomically replaced. If geometry or source metadata changes, regenerate its dependent path/audit records before bundling. Browser acceptance must use the rebuilt HTML, including start/middle/end motion, pause, washer visibility, each module, wiring pins and stable idle frames.

`verify_wiring_3d.py --source-only` checks the electrical/spatial sources and intentionally does not claim delivered-UI acceptance. Its full mode also checks browser receipts and the original server under incomplete concurrent requests. `wiring-3d-ui-20261007.json` and the earlier closure/UI receipts are historical and may reject a new bundle hash; do not reuse them as evidence for the revised guide. Current rendered acceptance belongs in `assembly-revision-ui-20261008.json` and must identify the delivered bundle and the operations actually observed.

The eight local-leg routes now render the exact checked STL coordinates, including their retained spare-length contexts. Their isolated plug animation represents the declared receiving envelope on the open motor bench. It does not establish a closed-leg insertion or full flexible motion. Historical power/head curves remain distinct until replaced by the current complete integration; the former eleven-fuse array is withdrawn.

Three.js and OrbitControls are embedded from the existing local dependency; their MIT license headers are preserved.

Historical operation-7 acceptance is recorded in `closure-ui-20261007.json` and checked with `verify_closure_guide.py`. Those original bundle hashes remain unchanged; current browser evidence must be recorded separately after rebuilding.


The 8 October live-browser receipt is `assembly-revision-ui-20261008.json`; run `python verify_assembly_revision.py` after refreshing that receipt and `audit-20261008/deployment.json`. Its current checks bind the original URL, exact bundle and source hashes, all ten modules, knee trajectories, yaw access, stopped head-shell motion, pause/scrub, open-jaw cap fastening, upper-pad path and wiring navigation. `audit-20261008/revision-acceptance.json` deliberately retains 14 nominal source-contact findings and does not certify full rigid insertion or physical assembly. The final motion scan used by this gate is regenerated with `python audit_motion_paths.py --step 0.25 --output audit-20261008/final-motion-paths.json`.


## Torso service and continuous availability — 8 October 2026

The live full guide remains available at the original Mac mini URL while the separate head candidate is revised. A response-write timeout inherited from the short request-header timeout caused large downloads to truncate. The repaired server uses separate idle-write timing, gzip and content ETag revalidation. `hosting/main-restored-acceptance.json` binds the exact delivered full response and actual Chrome screenshot; `hosting/server-live-regression.json` covers the original paused-download failure and server regressions.

`non-head-review/torso-service-steps.json` overlays the torso section only. It handles already fastened hips without dismantling the ankle, foot or other lower joints: retain and reuse seven screws per closed side, remove the rear washer before translating the complete four-joint leg, install the base and closed rings on the bench, reconnect the legs, and install the power support last. Open hip connections skip the removal steps; do not close them merely to reopen them. The original nominal torso placement cannot pass both closed rings around complete legs, and early power support blocks four driver corridors.

The service verifier checks 17 part/group paths at 0.25 mm and 34 Ø3 mm driver corridors, including 28 retained screw envelopes moving with each leg. The actual screw-head withdrawal envelope, printed fit and strength are separate physical checks. Original mating contacts have named pair-specific thin bounds, never a blanket allowance. Payload, report, verifier and negative-control hashes must all match before the bundle is built. Independent review is in `non-head-review/service-independent-review.json`; current Chrome observations include all 28 operations at 0%, 50% and 100%.

The IMU clamp approach is −X28 rather than +X28. `non-head-review/verify_imu_path.py` reproduces 113 clear poses and the old positive-X collisions against the current full source. Head geometry and complete camera/USB cabling retain the separate acceptance boundaries in `../head-redesign-20261008/README.md`.


## Current body and sensor integration — 9 October 2026

The build applies the mechanical-motion, body-power, IMU, body-DATA/housing and 20 V input overlays in that order. They consume hashed source receipts and never regenerate CAD during webpage packaging. The IMU has six stations: open holder, board, plug, cover, four fasteners and cable retention. The revised holder/cover replace their former meshes; the inherited “no holder reprint” note is retired. Both motor-zone plugs are connected before the torso shells. The external 20 V pair enters through the existing rear bay gap before its onboard terminations are made.

Checked keyed housings move along their registered 12 mm bench approach while the motor remains fixed. Soldered routes use endpoint inspection rather than invented plug animation. Operation-to-wire navigation restores the originating phase, progress and screw visibility. The Pi header view overrides local-route rendering and retains all 40 physical contacts. Tests cover these interactions and source-chain failures. Full head, integrated moving harness and the new incremental print release retain their own pending acceptance; these body overlays do not substitute for them.
