# 90-day roadmap: from simulator evidence to a physical loop

> Start date: 2026-08-04. Dates are planning boundaries, not claims that future work is already complete.

## Days 0–30 — Establish a baseline and make failure visible

**Question:** Can we record and explain every failure in one reproducible manipulation task?

- Select one task with controllable perturbations in MuJoCo, LIBERO, or Isaac Lab.
- Reproduce a public policy baseline through LeRobot where practical.
- Define the rollout schema and failure taxonomy.
- Run multiple seeds across object pose, lighting/camera, dynamics, and instruction variants.
- Publish raw traces, aggregate metrics, and five representative failure replays.

**Gate:** Another person can reproduce the baseline and locate where each failed trajectory diverged. No real-robot purchase is justified before this gate.

## Days 31–60 — Close the first learning loop

**Question:** Can observed failures choose better data and improve the next policy?

- Integrate a progress/success model and deterministic task checks.
- Measure verifier precision, recall, calibration, and abstention under perturbation.
- Compare random extra demonstrations with failure-targeted demonstrations or interventions.
- Retrain or post-train the policy and run the same regression suite.
- Add an initial counterfactual baseline: policy confidence or a lightweight predictive model.

**Gate:** The targeted-data loop improves success or reduces intervention burden more efficiently than the random-data baseline without hiding regressions.

## Days 61–90 — Touch atoms

**Question:** Which parts of the loop survive contact with real hardware?

- Move the smallest complete loop to an available arm: a CMU platform, borrowed lab hardware, or a low-cost LeRobot-compatible arm.
- Calibrate cameras, frames, action limits, emergency stop, and data timing.
- Repeat at least three perturbation families and retain failed runs.
- Compare predicted versus observed failure modes and update the taxonomy.
- Publish a three-minute demo, evaluation report, and a decision on the next research bet.

**Gate:** At least one policy update is justified by physical failure evidence and re-evaluated on the same hardware. A negative result passes if the trace proves why transfer failed.

## Metrics that matter

| Category | Minimum metrics |
|---|---|
| Task | success rate, completion time, partial-progress score |
| Reliability | time-to-failure, recovery rate, irreversible-error rate |
| Human burden | interventions per hour, correction time, resets |
| Learning | success gain per corrected trajectory, regression count |
| Verifier | precision, recall, calibration error, abstention rate |
| System | control latency, dropped frames/actions, reproducibility across seeds |

## Twelve-month horizon

If the 90-day gates pass:

1. support a second embodiment and measure what transfers;
2. contribute the common rollout/failure tooling upstream to LeRobot or another open ecosystem;
3. add action-conditioned world-model ranking and real-world calibration;
4. run a multi-step task with autonomous recovery;
5. connect the loop to a scientific instrument or laboratory workflow;
6. publish a benchmark, technical report, and externally reviewable dataset.

Learning is pulled by these gates: MuJoCo, ROS 2, LeRobot, Isaac/GR00T, reward models, world models, calibration, and hardware safety are learned when the experiment requires them—not as an endless prerequisite list.
