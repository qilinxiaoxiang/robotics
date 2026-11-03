# Independent research review of the final task plan

**Verdict: accepted for the stated task-planning scope and supplied CPU first increments. No blocking research defect found. New-body policy training, GPU affordability, physical transfer and complete fetching are not accepted by this review.** I reviewed the root-authored plan, not independently certified my own motion-package implementation. A separate cold-start reviewer should establish combined startup reproducibility.

Let T denote `microduck-sim/microduck_rl/cmu/planning/fetch-20261103/` in the robotics workspace. Exact reviewed file hashes are in `research.json`; later semantic edits invalidate the affected conclusion.

## Evidence and hypotheses

C names an observed head-down failure and starts from supplied exports and actual traces (`tasks/C-head-walking.md:3–15`). The motion readback shows default-head versus lowered-head jump rates 1.67 versus 14.04/s; that is historical evidence of the gap, not evidence that a reference penalty or memory is the correct remedy. The card appropriately separates a single leg-reference change from later history work and explicitly rejects motion/head avoidance as improvement. Similar local gyro sensitivity does not diagnose the cause.

D starts from an actual pick→stand trace and distinguishes the transition mismatch from proof of sole causation (`tasks/D-pick-and-rise.md:9`). A neck offset of 1.4903 rad and subsequent >45° tilt at 0.906 s localize a failure; they do not establish that interpolation or a Boolean holding change repairs it. The proposed current-task versus extended-terminal-objective comparison keeps timing/contact fixed and postpones additional history/reward changes (`:14–20`). It scores lift and retention separately from exit/stand success. Outcomes before versus after lifting select different next work.

B retains an actual detector's orange non-ball false selection, and requires additional frozen distractors/lighting splits rather than a one-image patch (`tasks/B-visual-approach.md:9–20`). Person identity and track scenarios remain fixtures; no real ball/person benchmark is falsely claimed (`INPUTS.md:6`). E's 18-case software composition checks sequencing/readback handling, while its real success estimators remain explicit implementation work (`tasks/E-fetch-execution.md:9–22`; `CONTRACT.md:16`). All these are useful first increments without demanding that fetching work already.

## Available inputs and matched comparisons

README:19 and INPUTS:7 correctly distinguish four ONNX inference/reference artifacts from optimizer checkpoints. No exact PPO resumption or recovered dock-e/f checkpoint is claimed. Approximate reconstruction, synthetic fixture inference and physical evidence have distinct labels. This avoids the former unsupported exact-reproduction claim.

F0 is an owned prerequisite with scan, mass/placement, static poses, timing, actuator/contact agreement and the known dynamic failure direction (`BODY-READINESS.md:3–11`). Old-body exports cannot certify the changed battery body. README:29 bootstraps D from stable baseline entries after F0 rather than circularly requiring a new C policy; final joint trials still preserve actual state/history. The contract requires supported regions and named semantic adapters, rather than equal array dimensions.

The first executable operations use supplied inputs. C/D are explicitly CPU replay/source increments now; future training waits for F0. Physical trial ranges are frozen before tuning and are based on reachable/consumer-supported states. The plan does not invent centimeter or success-percentage thresholds to manufacture acceptance.

## Resource and next-touch limits

The plan does not promise a run count or completed capability within the user-reported Kaggle/Modal $54/unknown AWS resources. Actual matched training feasibility remains unverified. Before launching, freeze the exact single-change config, step budget, initialization path, held-out cases and exact-task throughput/memory/export costs; identify which account supplies the resources. ONNX warm start still needs validation and cannot imply optimizer continuation. These are pending training prerequisites, not blockers to the advertised CPU increment or reasons to change the user's budget.

C's “at least two seeds if compute permits” is appropriate uncertainty labeling, not proof of robustness; even two seeds do not establish physical reliability. Historical logs lack forward odometry, so C cannot derive real travel/velocity tracking from these first traces; those fields require later measured evaluation. B/E need real identity/take/drop recordings for their live claims. The plan exposes these as future readback dependencies and does not substitute fixture success.

No simulation, training, robot operation or paid job was performed by this review. The later Chinese synthesis was not available in the reviewed set and is not covered by this acceptance.
