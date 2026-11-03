## Place in the complete demo

Call Mochi → look at the caller → hear the orange-ball request → approach while watching → pick and rise → carry back to the **same person** → wait for the person to take the ball.

## Claim or hand over

This Issue starts **unassigned**. To claim a task or a week-one increment, comment with your intended scope, available time and first deliverable. Multiple people may split it by agreement in the comments. To hand it over, post the branch/revision, exact command, inputs, current result, blocker and next step; mark it open for takeover. The next claimant replies here. A successful starter run is the first step, not completion of this capability.

## Supplied starting point

[Task pack](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/README.md) · [CPU setup](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/starter/README.md) · [Shared interfaces](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/CONTRACT.md) · [New-body prerequisite](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/BODY-READINESS.md)

The tested starting revision is `80f2344f37bffe61f0756f14aca5d6c92a33299d`. Clone the team repository if needed, then from its root:

```sh
cd cmu/planning/fetch-20261103/starter
.venv/bin/python motion/replay.py locomotion --out out/locomotion.json
```

Before that command, create the CPU environment **inside `starter/`** once:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
```

## Task brief

**Where/why:** looking at a ball changes whole-body balance. A smooth policy that barely moves or refuses to lower its head does not solve the demo. Later the same controller must carry the ball. This advances P5/P6. **Difficulty 5/5; project novelty 3/5.** CPU baseline/diagnostic work starts now; new-body training waits for F0.

**Build:** improve the existing walker to follow head/neck and velocity requests together. Start with unloaded motion, then extend to D's real loaded exit. Preserve a named supported range for B/E.

### Start with supplied material

Use `starter/motion/README.md` to install its pinned CPU environment. Run `python replay.py locomotion --out out/gait.json` with that environment. The package contains real walk61 and t2b exports, bounded historical sensor/action traces, source snapshots and hashes. It reproduces the head-down jitter comparison. Raw 61-value observations were not logged: reconstructed-input inference is explicitly approximate, not exact controller parity. Historical models are not accepted for the new backpack.

### Suggested operations

1. Reproduce the default-head versus lowered-neck trace diagnostic. Inspect action jumps alongside head error, speed/distance and tilt. Check compensation/filtering/observation semantics; the package documents the opt-in compensation trap.
2. Inspect the supplied finetune/environment source. Prepare a two-condition evaluation using identical velocity commands, head commands and initial states. After F0, run it unchanged on the matched model. If it cannot reproduce the relevant failure, first fix model/actuator/timing agreement; do not hide mismatch by changing reward weights.
3. Compare **one** change: retain velocity/head tracking while adjusting the original-policy leg reference strength. Keep head joints outside an anchor that would force the old head pose. Reject changes that reduce jitter by not walking or not looking down. A short observation/action history is a later comparison if measured timing uncertainty is the unresolved limitation; its benefit alone does not prove the physical cause.
4. Evaluate B's recorded requests, then D's supported loaded exit. Export through the pinned input/action adapter and replay the same tests. Do not infer compatibility from equal vector length.

### Deliver and accept

Week 1: baseline readback, evaluation code/config and one precisely specified comparison; a CPU diagnostic is already possible. Supply action-jump rate, head error, travel/velocity tracking, tilt and falls together. Preserve failed traces. No new-body training claim before F0.

After F0: freeze a physically reachable head/velocity range and trial starts before tuning. Candidate must improve the preselected failure metric while retaining required head/velocity tracking and stable stop across the range. Record real-condition and stress results separately. Compare at least two training seeds if compute permits; one seed is exploratory, not established robustness. Only a matched exported version passing protected robot trials advances to live B/D integration.

**Handoff:** model/source/config hashes, units/joint mapping, supported head/velocity/payload range, previous-action/history initialization, all seeds and failures. D does not wait for this new model to begin isolated development: both start from the shared historical baseline after F0. Loaded walking is the next increment after D supplies a validated exit and payload.

[Original task card and source references](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/tasks/C-head-walking.md)

## Coordination with the other tasks

[B: Continuous vision and approach](https://github.com/qilinxiaoxiang/microduck_rl/issues/3) · [D: Visual pickup through a stable loaded rise](https://github.com/qilinxiaoxiang/microduck_rl/issues/5) · [E: Full fetch execution, return and handover](https://github.com/qilinxiaoxiang/microduck_rl/issues/6)

Use the shared contract above for the boundary. Producer and consumer jointly accept each continuous handoff; no reset between skills in the final integration check.
