> **Historical research brief — final task plan supersedes the assignment and proposed gate sections below.** The current five-task plan and actual portable inputs are in [the accepted task package](../../microduck-sim/microduck_rl/cmu/planning/fetch-20261103/README.md); independent execution/review is in [final acceptance](final-acceptance/recipient-final.md). This earlier brief remains as source analysis, not a current task dispatch or physical-readiness certificate.

# MicroDuck: from component skills to a pet that fetches

Decision brief, 3 November 2026. Organizing axis: the dependency path from a grounded request to a verified physical handover. Problems advanced: P0 (success judgement), P1 (aligned failure data), P4 (long-task recovery), P5 (body and contact), P6 (transfer and deployment).

**Recommendation:** preserve the existing PPO/mjlab training stack; establish one measured battery-body baseline; diagnose the latest docking plateau; then improve continuous visual docking, stable pickup-to-carry transitions and caller-relative return. In parallel, complete hearing, caller binding and spoken-command integration. Spend the next compute allocation on a discriminating comparison, with a frozen evaluation set.

The current review did not launch training, change policies, command the robot or publish GitHub issues. Numerical gates below are proposed development targets, not new measured results or already agreed product requirements.

## Product contract

Shawn's goal is a real pet robot. The requested demonstration is:

1. Call its name; it looks at the caller and waits.
2. Say “go fetch that orange ball”; it binds the request to the correct ball and remembers the initiating person.
3. Search and approach using its head camera, maintaining useful visual feedback and memory through short occlusions.
4. Bend, bite, lift and regain a stable posture.
5. Carry the ball back to the original caller.
6. Stop in front of that person, keep holding the ball, and wait for them to take it.

The last step is user-confirmed: “回到叫它的人面前，等人从嘴里取走”. Dropping at the start point does not satisfy it. Ball size/mass/material, desired travel speed, stopping distance and take/release sensing still need engineering validation. The previously used approximately 12 mm printed ball is historical evidence, not a new product specification. The older 4–9 cm target description cannot silently be reused either.

Keep the established head-only response to a name and the animal-like sensor placement: forward-facing head cameras; no chest or under-beak camera. The earlier throw-tracking request remains an expansion after the first floor-ball chain. First validate a bounded open-floor scenario with a stationary caller, then a moved caller, distractor person, moving/occluded ball and more varied surfaces. This changes test order, not the final capability.

## What the evidence supports

Current measured/configured facts come only from [CURRENT-STATE.json](../../microduck-sim/CURRENT-STATE.json). Today's battery-pack change has been recorded there, with the old charger entry preserved as superseded. Its check still flags stale IMU rate/delay, walking-policy verification and servo voltage; local probes had no fresh measurement files. No new-body readiness claim follows from this audit.

- **Hearing and gaze have real component evidence.** The 2 November run recorded nine calls/nine quacks, faces found on eight, and one wrong-side glance. The later namecall service was enabled, but cold-start acceptance on that release was still open. Hearing during walking has weaker evidence than quiet standing. See [pet log](../../docs/PET_ROBOT_LOG.md) and [requirements](../../microduck-sim/guide/firmware/mac/namecall-20261029/REQUIREMENTS.json).
- **Language and identity components exist.** `pet/voice` has speech/intent tests; `pet/identity` has face/voice matching components. These do not establish a live spoken fetch or original-caller return. The existing runner can treat any detected person as owner. Its fixed-duration primitives do not complete the continuous visual goal. See [voice](../../pet/voice/README.md), [identity](../../pet/identity/README.md) and [runner](../../pet/mind/RUNNER.md).
- **Visual pickup has happened, but reliability and transition remain open.** One 30 October pickup used a tape-corrected target position and held the ball through a rise. A 1 November T2 attempt approached and gripped the ball, then fell 0.9 seconds after switching to stand61. Later attempts missed; the real image feature disappeared early and the bite stayed near a fixed spot. See [T2 evidence](../../microduck-sim/guide/firmware/mac/t2-chain-20261101/README.md).
- **The latest dock result is training telemetry.** Dock-e/f plateaued at roughly 17–23% on the logged recent docking metric, with 2–4% fall telemetry. Held-out final checkpoint evaluation and robot acceptance were not done. “5 cm” names the initial curriculum window; actual starts are a mixture and are not all within 5 cm of the bite point. The oracle audit scored 69%; this is a diagnostic failure to investigate, not a physical success ceiling. See [reward audit](rewards-compute.md).
- **Carry and handover are new proof obligations.** There is no accepted loaded walking, original-caller reacquisition and human-take chain. A current/angle “holding” flag can confuse a real ball with contact or a jam; delivery needs an independently checked object transfer.
- **Runtime faults can break every stage.** The fault checker leaves spin stall and camera USB disconnect open. A stale shared frame has been mistaken for a missing ball; real get-up evidence also fails to match simulation. These require separating tests and an honest stop/recovery result. See [fault register](../../microduck-sim/FAULTS.json). A mitigation or a service process staying alive does not prove recovery.

The migration is incomplete at the experiment-package level. Latest dock source was found in a plain Mac-mini directory without Git metadata. Its inspected task code is saved with hashes in [source-manifest.json](sources/dock-snapshot/source-manifest.json). The final dock-e/f checkpoints were absent from its expected policies directory, and the logged branch/commit could not be resolved in local/GitHub refs. Source logic is now reviewable; exact run reproduction is not yet established.

## Sim-to-real: make the experiment refer to this robot

The new scan addresses geometry. It cannot supply component masses, friction, compliance, sensor age or loaded actuator response. The model needs both the scan and measurements.

1. **Inventory and identify the changed body.** Register the battery, cradle, back plate, retention, head boards/audio, cables and payload in their actual positions. Weigh the changed assembly and removable parts; account for uncertainty explicitly. Do not emulate a known missing/moved battery with an arbitrary centre-of-mass offset.
2. **Separate mechanical hypotheses.** Match standing, intermediate and bending poses with synchronized joint/IMU readings and a floor reference. The old scan could not separate joint-chain bias from compliance. Main now models a 1.36 rad heel stop; dock explicitly applies 1.25 rad, and whether the real ankle cable has moved still needs current evidence. Refit near-mouth camera geometry after the actual stop changes.
3. **Match training and deployment computations.** Freeze joint/action mapping, observation slots and normalizer, actuator model, timestep, contact solver, geometry, grip setting, policy-switch behavior and camera delays. Earlier apparent policy failures came from stale collision structures and differing contact solvers. Test exported actions against the training actor before interpreting robot transfer.
4. **Identify uncertainty, then randomize it.** First measure healthy sensor timing, joint lag, backlash/friction, supply response and plausible mounting variation. Domain randomization means varying these quantities during training; its range should represent uncertainty in this robot. Keep jam/failure states and harsher stress cases separately labelled. The recorded 17% servo-drop value is a fault-state sample, not a healthy baseline.
5. **Use history for hidden state.** Compare current-frame image features against a short history of target centre/size/confidence/age, head/joints, IMU and previous actions. The history must know when a frame was captured. A remembered ball with rising uncertainty is different from a frozen box labelled fresh. No policy may receive simulator-only ball coordinates at deployment.
6. **Transfer through the complete runtime.** Rehearse start/stop, head motion, docking, bite, rise and policy handoff with the actual control stack; then use guarded physical trials on the same hashed release. The real failure modes, not a visually convincing simulation, decide promotion.

## Reward audit: preserve the lessons and test the remaining hypothesis

The latest dock code, rather than stale sections of DOCK.md, defines v4. It rewards new best distance progress (weight 40 per metre), dense closeness (up to 10 per second, 5 cm scale) and docked hold (6 per second). Falling and walking over the ball incur one-off costs of 120 and 60. Ball motion, being behind the target, view/alignment error and action changes carry costs; upright/pose bonuses and the previous continuous error cost are zero; the entropy coefficient is zero. These are inspected settings, not recommended settings for the changed body. [Exact audit and code references](rewards-compute.md).

Three failure mechanisms are already supported:

- Negative running error cost let early failure avoid future cost: walking over the ball shortened episodes while improving return. Audit entire episodes, including termination and discounting.
- Removing dense guidance made the signal sparse; the exploration bonus increased action variability and falls. More exploration is not automatically more useful exploration.
- v4 learned some docking and then plateaued. Closeness alone still pays about 7 per second at 3 cm error and 9.6 at 1 cm, even if stillness or orientation fails. A near-goal compromise is a plausible hypothesis, not a diagnosed cause.

**The next experiment should leave v4 unchanged initially.** Recover final checkpoints; inspect why the oracle fails, and classify the policy's failures as overshoot, stops short, never settles, loses sight, wrong heading, contact or fall. The current “recent docked” test is an exponential average, not a literal uninterrupted half-second hold. Decide which definition represents useful physical docking before changing the metric. Do not raise a score by relaxing the acceptance after seeing results.

Then change one mechanism:

- If visibility loss dominates, compare current frame versus short history, holding physics/rewards fixed.
- If near-goal hovering or never-settling dominates, compare v4 against stage-conditioned approach/settle rewards; taper approach payoff after arrival and pay sustained useful terminal behavior. Audit standing, oscillation, walk-over and deliberate-fall alternatives before training.
- If the motion is unreachable or the body model wrong, correct the model/action envelope before touching reward weights.
- If the rise/handoff fails, train the loaded transition through a stable carrying posture. Do not optimize the bite while ending the episode before the dangerous transition.

For return, reward progress toward the identified caller only while a verified payload is held, then stable waiting. For handover, distinguish human removal from accidental drop. Keep these independent success checks outside the reward: correct request/ball/person, real lift, sustained retention, safe return and actual take. The original isolated learned-jaw experiment is separate from T2's scripted jaw schedule; integrating a learned grip/release policy remains a later explicit task.

## Methods and open resources worth using

These recommendations are project inferences from primary sources checked on 3 November. [The research brief](frontier-methods.md) includes pinned repositories, weight availability, licenses and transfer limits.

- **Use the existing platform first.** [Pollen MicroDuck RL](https://github.com/pollen-robotics/microduck_rl) already provides PPO training, actuator randomization and ONNX export. [BAM](https://github.com/Rhoban/bam) provides actuator identification and XL330 models. They address the immediate body/actuator mismatch; library parameters still need assembly-specific checks.
- **Train a deployable actor with a better-informed critic.** [Asymmetric actor–critic](https://arxiv.org/abs/1710.06542) gives simulator truth to the training critic while the action policy uses real-available observations. T2 already uses this principle. Add teacher-to-student distillation if a state-informed teacher succeeds where the visual/history actor fails; evaluate only the student for transfer.
- **Test memory before a larger adaptation system.** [RMA](https://ashish-kmr.github.io/rma-legged-robots/) demonstrates history-based adaptation to dynamics. For this duck, compare simple history with the existing behavior-cloning anchor first; adaptation must outperform that baseline on held-out body/load conditions.
- **Borrow visual ball-control and recovery design.** [DribbleBot](https://arxiv.org/abs/2304.01159) is a useful locomotion-plus-ball precedent, while [Helpful DoggyBot](https://arxiv.org/abs/2410.00231) is closer to fetch semantics. Their body, camera and training setups differ. Borrow observations, curricula and failure tests; their weights cannot simply drive MicroDuck.
- **Preserve pet-like expression while controlling balance.** [Disney's bipedal character control](https://arxiv.org/abs/2501.05204) couples commanded expressive motion with learned robust control. This supports independently commanded gaze/expression under a balance controller. It does not supply an autonomous fetch solution.
- **Use human corrections after the base motion is reliable.** [HIL-SERL](https://hil-serl.github.io/) offers demonstrations, success classification and intervention-driven learning. Collect meaningful corrections to target/gaze/skill choices first; its manipulator results do not justify unrestricted joint-level exploration on a free-standing biped.

Defer a simulator migration, large vision-language-action fine-tune, full sparse-reward spoken-command-to-fetch training and generic human-motion imitation. Each would consume the current budget without resolving the measured model, observation or transition gap. ACT/Diffusion Policy, AMP and openpi remain conditional resources with explicit adoption tests in the research brief.

## Capability work packages and joint integration

The initial four fixed lanes and later six audit-oriented cards were withdrawn after user review. Use the current [four capability briefs](../../microduck-sim/microduck_rl/cmu/planning/fetch-20261103/index.html): caller interaction, continuous target approach, head-conditioned locomotion, and visual pickup through stable rise. Each states its context, method, acceptance and adjacent dependencies. Inputs still requiring consolidation are explicit in [INPUTS.md](../../microduck-sim/microduck_rl/cmu/planning/fetch-20261103/INPUTS.md).

There are five humans including Shawn; tasks can be claimed/shared/reassigned. One runtime owns motor output, while teammates may own the controller implementations. Adjacent owners jointly test approach → pick/rise → carry without state resets. Shawn coordinates robot acceptance; source/checkpoint archaeology is coordinator preparation, not an unexplained task for a new teammate. See the [Chinese overview](../../../reports/20261103-microduck-collaboration.html) for the revised plan.

## Stages and evidence needed to advance

1. **G0 — Reproducible current body.** Recover source/checkpoints and run configurations; reconcile stale state, inventory, mass, ankle stop, camera geometry and known physical faults. Compare measured held poses and healthy timing. No new-body simulation verdict before this pass. A/C and diagnostic work in B/D proceed independently while scan inputs are pending.
2. **G1 — Controlled locomotion and useful perception.** Validate quiet/walking name response, continuous tracking, head-conditioned start/stop/turn and command/cancel. Candidate must improve its intended skill without losing walking, neck reach or timely stops. Reject a smooth policy that achieves smoothness by refusing movement.
3. **G2 — Visual approach, pick, lift and loaded stand.** Frozen held-out start sets, no hand positioning or hidden coordinate override; target identity and valid visual/history input throughout; count empty bites and handoff falls. Proposed development gate: at least 8 of 10 physical successes plus 10 seconds of retained stable hold, zero falls, with all attempts retained. Simulation screens use at least 100 episodes per normal condition and confidence intervals; stress cases are reported separately.
4. **G3 — Carry, original-caller return and human take.** Start with short straight carrying, then turning/stopping, then return to a stationary caller, then changed caller position and a distractor. Proposed gate: at least 8 of 10 complete retained-ball returns, with correct caller for every completed return and no false handover completion. Learn release from tested take cues, not a timer or jaw current alone.
5. **G4 — Complete pet interaction.** One release runs name→gaze→spoken fetch→pick→return→wait→take. Proposed first demonstration acceptance: 8 of 10 complete trials in a predeclared bounded scenario; then at least 30 across multiple sessions before making a broader reliability claim. Report full-chain success, conditional stage rates, time, human interventions, drops, wrong targets/persons and recovery. Add throw/occlusion, lighting/surface and moving-caller cases progressively. These trial counts are development gates, not statistical proof of high reliability.

Across stages, camera unavailable/stale, cancelled request, dropped ball, lost caller and communication loss need explicit detect→stop/reacquire/recover outcomes. A fall remains a failed trial until autonomous get-up is physically validated; an honest safe wait for assistance is preferable to scoring a reset as recovery.

## Compute allocation

Use the user-reported **$54 Modal credit as a planning ceiling**; account balance/expiry was not independently inspected. Suggested split: $4 exact-task installation/smoke/throughput/resume/export checks, $30 for the selected ablation, $10 held-out evaluation/reproduction and $10 uncommitted contingency. These are spending buckets, not guaranteed experiment counts.

At checked [Modal list rates](https://modal.com/pricing), one GPU plus the existing launcher's 4 physical CPU cores and 16 GiB costs approximately $0.91/hour on T4, $1.12/hour on L4 or $1.42/hour on A10, before other billed usage. GPU hourly price alone is insufficient: compare cost per equal-fidelity finished experiment, including startup, evaluation and failures. Bound total concurrent spend and retries; reserve funds before launching a job, and verify checkpoint/resume rather than trusting a time cap.

Kaggle is suitable for reproducible baseline/paired seeds when its current quota permits; historical remaining-hours notes are not today's entitlement. Two T4s can run independent seeds; they do not automatically form one larger-memory GPU. Teammates should report AWS GPU type, VRAM, usable credits/expiry and concurrency first. Give each machine independent comparable seeds/evaluation batches; avoid distributing one tightly coupled run across mixed clouds. Use CPU for contracts, replay, metric audits and deterministic checks. Keep geometry-heavy work bounded and separate from timing-sensitive tests.

## Immediate backlog

- Done in this review: record the full fetch/human-take requirement and changed battery pack; verify latest records and actual dock reward code; locate the missing source snapshot; draft four task cards and this staged plan.
- Next independent deliverables: reconcile the exact dock run/checkpoint package; diagnose oracle and policy plateau without changing v4; freeze shared contracts and held-out scenario IDs; prepare shared audio/caller tests and new-body capture/measurement protocol.
- After the new scan and measurements: publish a single internal model baseline, replay existing policies with matched runtime, select one observation/reward/control ablation based on failure counts, then assign the bounded GPU runs.
- Before any physical promotion: resolve the relevant camera/turn fault tests, verify the live power/guard and current sensor timing, and schedule one supervised same-release acceptance sequence.

The first discussion should settle the next experiment, not a complete new reward vector: whether the dock plateau comes from a defective success test, near-goal reward compromise, limited motion reach or insufficient observation history. The saved code and prior failures now make those alternatives testable.
