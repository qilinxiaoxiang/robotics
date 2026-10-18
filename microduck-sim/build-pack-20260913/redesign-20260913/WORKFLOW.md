# MicroDuck hardware design workflow

Purpose: deliver an inexpensive, assembleable visual-pickup robot by adapting the existing open-source body and trained-policy work. Problems P0, P5 and P6. The goal and training history remain in [PROJECT-CONTEXT.json](../../PROJECT-CONTEXT.json).

## Current staged review — 9 October 2026

Follow [the practical print-and-fit workflow](workflow-review-20261009/WORKFLOW.md). The central battery clamp is withdrawn: preserve the original body and use the original battery location for DFR1202. The current release is [V1.5, the complete incremental 12-piece set](printing/15-COMPLETE-INCREMENTAL-20261009/PRINTING.md): four colors and eight machine alternatives. It supersedes V1.4 and the head-only trial for this printing trip. Its source-bound native print checks pass; internal USB plug selection, populated closure and physical commissioning remain open. Use the current Mac-mini assembly guide and preconnect inaccessible sockets before covers; do not use historical head or fuse-carrier instructions.

## 1. Fix the task and available resources

Read the goal and existing training evidence before selecting parts. Record purchased, owned, borrowed and proposed items separately. Read the current servo/controller order and bundle state from `../procurement/sourcing-policy.json`; an old receipt does not establish current supply. The existing MDY-14-ED charger is available. Raspberry Pi and general fabrication supplies retain their existing sourcing decisions. A prototype phase may simplify the environment, but cannot remove the camera-guided pickup objective.

## 2. Reuse the baseline before designing changes

Identify the original body, controller firmware, walking policy, jaw checkpoint, sensors and operating system. For each change, state what it replaces and why it is necessary. Prefer standard cables and local bracket changes. Reject a compute substitution until the camera, IMU, motor transport, timing and fault-stop paths are all accounted for.

## 3. Review three bounded subsystems in parallel

- Power reviewer: source protocol, complete load budget, startup and fault behavior, conductor lengths, connector ratings and endpoint voltage.
- Compute reviewer: real observations, control timing, operating-system dependencies, camera and audio paths, connector ends and software transfer work.
- Mechanical reviewer: actual CAD envelopes, mounting, moving-part clearance, wire exits, mass placement, service access and future battery interface.

Each reviewer returns source references, calculations or checks, exact interfaces, proposed parts and unresolved physical measurements. Reviewers do not independently change the shared cart or redefine the task. The integrating agent owns the complete design.

## 4. Integrate and challenge the complete design

Maintain one component and connection contract. Every cable has two named endpoints, a connector type, a purpose, a length and a termination method. Every load appears in the common power budget. Every installed item has a mounting or retention method. Coverage must include all 15 motors, logic, camera, audio, storage, fasteners and fabrication supplies.

Replay previous failures through the acceptance entry: omitted perception, lost trained model, duplicated power sources, mismatched cable ends, insufficient complete-load power, missing bracket, insufficient quantities and duplicate purchases. Independent reviewers attempt to falsify the integrated result before handoff.

## 5. Price the remaining complete order

Use the current authorized bundle mapping for servos/controller and exclude duplicate component purchases. Preserve borrow/club holds. Compare complete remaining baskets with shipping and duties, not individual prices alone. Exact source substitutions invalidate old cart evidence. A product quote is not a verified shopping cart. Mark any cart containing superseded items stale until reconciled.

## 6. Deliver at the correct acceptance level

- Design acceptance: interfaces, quantities, rated electrical operation, modeled fit, software architecture and the complete procurement plan have been checked. This is sufficient to review an assembly plan.
- Physical commissioning: the actual source negotiates the required voltage; the assembled harness passes polarity, loaded voltage, current, temperature and stop tests; the printed parts fit.
- Task acceptance: camera observations drive alignment and the learned pickup pipeline; actual trials record grasp, lift, hold and release, with failure cases retained.

A design may pass before parts arrive. That pass cannot be relabeled physical or task success. Missing hardware blocks its dependent measurement only; available research, implementation and calculation continue. Update the current handbook and executable acceptance entry together whenever the design changes.

## Printing preparation

Before preparing or revising any printing job, follow [PRINTING/WORKFLOW.md](PRINTING/WORKFLOW.md). It requires per-part bottom/first-layer checks, compact centering of the full support/brim footprint on both axes, machine-specific slicing, embedded thumbnail validation, and preservation of prior files. Inspect each part; apply orientation or geometry changes only where evidence requires them.

## Current executable entry

Run `python3 verify_current_build.py --scope design` from this directory. It invokes the procurement policy checks, rechecks Pi/IMU and all motor cable reach, checks the header housing and actual print project, and rebuilds the guide before the integration regressions. `--scope project` additionally rejects a complete-project claim until real visual trials exist.

The 2026-10-08 assembly review uses Python3.12.11 at `/tmp/microduck-cad-venv/bin/python`. `requirements-design.txt` is the design dependency manifest; verify available package versions when recreating the environment and pass `--cad-python <environment>/bin/python`. A missing CAD runtime fails rather than accepting stale geometry output.

## Assembly-guide review

Before revising assembly order or an animated path, use [the source-based review method](leg-guide-20261006/ASSEMBLY-REVIEW-METHOD.md). Reproduce the original blocked insertion or tool corridor, then check the corrected order against the actual parts present at that bench station. A detached subassembly must have an explicit later joining step. Check both screw-driving and nut-holding access, connector passage before latching, and cable exits before enclosure closure.

The current assembly-guide rebuild and test commands are maintained in [the workbench README](leg-guide-20261006/README.md#rebuild-and-check). They add leg/non-leg tool access, head articulation, nut entry, stopped shell approach and integrated motion sampling to the existing source/fastener/wiring checks. Keep source-fit conflicts and incomplete insertion routes explicit; a stopped animation or passing design verifier cannot establish physical fit or the visual-pickup goal.

## Optional ankle prototype — 7 October 2026

[Removable-side ankle review](ankle-redesign-20261007/README.md) advances P5/P6 by separating the obstructing passive cheek during assembly and revising the sleeve fit. The original accepted meshes and motor/foot interfaces remain the baseline. This proposal is not a replacement print order or physical acceptance.

Run the candidate with the CAD environment: `python ankle-redesign-20261007/verify_redesign.py`; run `python ankle-redesign-20261007/verify_redesign_delivery.py` after rebuilding, deploying and observing the exact Mac mini page. The candidate checker includes original failure reproduction, both assembly paths, source-range rotation comparisons and fastener geometry. Printed fit, play, thread retention and loaded stiffness are still required before adopting it. The whole current build continues to use `verify_current_build.py --scope design`; the candidate does not redefine that baseline.


## Head review — 8 October 2026

The user reports the ankle/foot already seated and defers their redesign. [Head fit and eye-camera review](head-redesign-20261008/README.md) evaluates the remaining captured jaw/shell/cap interfaces and moves the camera spatial candidate into the existing single eye. Local clearance candidates establish the proposed direction; they do not supersede the baseline build until retention, complete insertion, cable routing and actual fit have passed. The head review must keep those pending items separate from the baseline design check.

## Web delivery and board identity — user correction, 8 October 2026

Guide and design-review handoffs use the existing Mac mini service: [assembly guide](http://today.tailfc7c94.ts.net:8766/LEFT-LEG.html) and [eye-camera review](http://today.tailfc7c94.ts.net:8766/HEAD-EYE-REVIEW.html). Follow [hosting instructions](leg-guide-20261006/hosting/README.md); canonical edits remain on the MacBook Pro. Deploy, compare served bytes, and inspect the actual Chrome page. Opening a local file does not satisfy delivery.

The user has identified **first-generation Pi Zero W with a soldered 40-pin header** and **Pi 3 Model B V1.2**. Zero W is the engineering preference for curved-head integration; runtime and populated-board fit remain unverified. Current head CAD uses a Zero-form-factor reference; its fit and existing wiring do not validate Pi 3 mounting, camera cable, connectors or power. Preserve this distinction in generated guides and verification reports.

## 2026-10-08 assembly correction handoff (P5 / P6)

The live Mac mini full guide remains `http://today.tailfc7c94.ts.net:8766/LEFT-LEG.html`. The separate replacement list and prototype STL archive are `/REPRINT-PLAN.html` and `/REPRINT-PARTS.zip`; canonical sources are in `reprint-review-20261008/`. Five primary mechanical prototypes and two optional fresh-build lower links are included; six camera/audio-dependent parts are explicitly held. Native slicing and physical fitting remain separate.

The current full guide derives three integral-seat parts and fourteen exact M2×6 screw changes from the immutable baseline using `fastener-review-20261008/fastener-patch-proposal.json`. Its source-bound geometry/context reports and negative gates must pass before `leg-guide-20261006/bundle_guide.py --full`. The user confirmed existing knee screws are M2×6 at ID7 and ID2, four each. Do not infer damage from the nominal 3.2 mm depth or treat a fresh-build replacement as a proven disassembly route. The separate small-OD washer repair is conditional on exact metal-washer dimensions, flat recessed seating and available stock; its passing bounded reports retain `integrationReady:false`.

Run `reprint-review-20261008/verify_review.py`, `leg-guide-20261006/verify_full_guide.py` and `leg-guide-20261006/verify_assembly_revision.py` for this supplement. The latter requires the deployed-byte receipt and real Chrome frames; source tests alone do not satisfy it. The baseline `verify_current_build.py --scope design` remains necessary but does not certify candidate geometry, physical commissioning or the visual pickup goal. Its regenerated fastener provenance is reconciled only by the exact canonical metadata proof under `leg-guide-20261006/non-head-review/baseline_refresh_proof.py`.

`software-board-review-20261008/` distinguishes ARMv6/32-bit runtime compatibility from float32 policy weights. Actual policies load on the Mac; the intended Mac-policy/Pi-sensor runtime migration is not implemented. `head-redesign-20261008/cabling-release-20261008/` preserves audio/GPIO routing candidates separately from the published curved head. The 51 schematic electrical curves do not establish cable-body, connector, neck-motion or prewired-installation clearance. Follow the current cable release report before changing the six held print parts.
