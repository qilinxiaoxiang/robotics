## Place in the complete demo

Call Mochi → look at the caller → hear the orange-ball request → approach while watching → pick and rise → carry back to the **same person** → wait for the person to take the ball.

## Claim or hand over

This Issue starts **unassigned**. To claim a task or a week-one increment, comment with your intended scope, available time and first deliverable. Multiple people may split it by agreement in the comments. To hand it over, post the branch/revision, exact command, inputs, current result, blocker and next step; mark it open for takeover. The next claimant replies here. A successful starter run is the first step, not completion of this capability.

## Supplied starting point

[Task pack](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/README.md) · [CPU setup](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/starter/README.md) · [Shared interfaces](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/CONTRACT.md) · [New-body prerequisite](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/BODY-READINESS.md)

The tested starting revision is `80f2344f37bffe61f0756f14aca5d6c92a33299d`. Clone the team repository if needed, then from its root:

```sh
cd cmu/planning/fetch-20261103/starter
.venv/bin/python motion/replay.py pickup --out out/pickup.json
```

Before that command, create the CPU environment **inside `starter/`** once:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
```

## Task brief

**Where/why:** a closed beak is not delivery. Historical pickup has failed from visual loss, empty bites and a fall after switching to standing. This advances P0/P5/P6. **Difficulty 5/5; project novelty 4/5.** Replay/source work starts now; a changed physical policy waits for F0.

**Build:** a continuous visual pickup through stable loaded rise, with explicit failure/readback and compatible entry/exit regions. Keep visual history through near-mouth occlusion. The final result must be safe for C to carry, not merely a terminal reward at bite time.

### Start with supplied material

In the CPU environment described by `starter/motion/README.md`, run `python replay.py pickup --out out/handoff.json`. Actual pixel-pick and stand exports, bounded robot traces and source snapshots are supplied. Inspect the neck mismatch and observed fall timing around the pick→stand switch. This locates a concrete transition problem; it does not prove that the mismatch alone caused the fall or that smoothing alone fixes it.

### Suggested operations

1. Reproduce the failed transition and compare sensor state, outgoing action and incoming controller target. Read `reference/T2-PIXEL.md` and the copied environment/worker. The actor gets image features/age/visibility; simulator-only object truth must stay out of the deployed actor.
2. Extend the task through a stable loaded exit and a short carry/stop segment. Start after F0 from measured stable baseline entry states, so D need not wait for a new C model. Publish the tested entry/exit region. B/C then generate actual entry samples; replace ideal starts with those samples.
3. Keep source timing/contact settings fixed. Audit rewards against standing still, empty closing, floor contact, early termination and the intended pick. Require lifted-and-held success and stable exit; score each component. Compare the current task with the extended terminal objective before adding history or extra reward terms.
4. Implement named pick/stand/walk adapters preserving actual pose, velocity, previous action and visual history. Do not blend two raw 61-input/14-action policies. Add empty-bite, visual-loss and drop outcomes, and a supported cancel exit consumed by E.

### Deliver and accept

Week 1: reproduced handoff trace, executable continuous-transition evaluation, and the exact single comparison. State what outcome would change the next action: failure before lifting changes perception/contact work; failure after lift changes exit/control work.

After F0: freeze starts drawn from B/C exits. In one uninterrupted trial, the ball leaves the floor, remains held through rise, then C carries and stops. Record entry compatibility, lift, retained grip, tilt/falls, empty bites and drops separately; retain every failure. Validate payload sensing on real positive/negative examples—jaw current alone can mean floor contact or a jam. Simulator contact truth may judge training but cannot certify the robot.

**Handoff:** actor/config, entry/exit profile, payload/exit readback, supported abort and failure cases. B/D and D/C jointly accept transitions without resetting body or ball. E owns return and human-take logic; D supplies the grip/payload evidence it needs. Full physical pickup within two weeks is an aim, not a guaranteed output.

[Original task card and source references](https://github.com/qilinxiaoxiang/microduck_rl/blob/80f2344f37bffe61f0756f14aca5d6c92a33299d/cmu/planning/fetch-20261103/tasks/D-pick-and-rise.md)

## Coordination with the other tasks

[B: Continuous vision and approach](https://github.com/qilinxiaoxiang/microduck_rl/issues/3) · [C: Head-aware walking and carrying](https://github.com/qilinxiaoxiang/microduck_rl/issues/4) · [E: Full fetch execution, return and handover](https://github.com/qilinxiaoxiang/microduck_rl/issues/6)

Use the shared contract above for the boundary. Producer and consumer jointly accept each continuous handoff; no reset between skills in the final integration check.
