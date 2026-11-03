# Independent system acceptance — REJECT pending two repairs

Reviewed root-authored README, CONTRACT, BODY-READINESS, A–E cards, Discord draft, starter README, coordinator and rehearsal. A's audio starter/source package was excluded from independent credit. Exact source hashes and recorded checks are in `system.json`.

The root rehearsal actually ran: **18/18 passed**. This is adequate evidence of the provided software fixtures, not a real robot. Two uncovered counterexamples fail the current proposed behavior, so the package must be repaired and rerun before acceptance.

## Blocking findings

**S1 — Wrong-identity camera traffic suppresses the stale-target stop.** After the normal prefix, the robot is approaching the ball with last valid capture at 1.08 s. Send a fresh `track` for `person-B` at receive 2.0 s/capture 1.99 s. The current selected ball is stale. `handle` leaves state `approaching` and emits only `ignore_other_identity`; the prior `follow_target` remains the last movement intention. The global freshness check deliberately excludes every `track` event. A stream of wrong identities therefore bypasses stop unless an independent tick happens. B explicitly requires stale/wrong target to stop; the coordinator must check freshness even on wrong-target traffic, and E must own a bounded watchdog when no events arrive. Add tests for wrong-target traffic while approaching AND returning, plus no-event timeout. A fresh wrong target must not refresh the selected target's age.

**S2 — Caller look and ball search race.** Feed the actual parser's call/request, then the fixture settled event. The same update emits `gaze_only(person-A)` and `find_target(orange-ball)`, and enters `seeking_ball`. There is no caller-look completion/readback boundary. B can immediately redirect the head to the ball before the name response reaches the caller. CONTRACT says a buffered fetch waits until stop/look happens, but the implementation treats emitting a gaze request as completing it. Require a caller-look acknowledgement (resolved caller, reached/tolerable gaze and supported posture), or a concrete sequential executor contract with a composed proof. Then allow the buffered request to start ball search. Add negative tests for absent, wrong-caller and revoked-epoch look acknowledgements. This checks the proposed sequencing, not actual gaze accuracy.

## Scenario and failure ownership

A emits call/request/cancel and persistent caller reference. E stops through C, waits for supported body readback, then requests the head-only look. B/A resolve the person. E selects the ball; B continuously observes and requests gaze/speed within C's range. B/C present a measured entry to D; D picks/rises while retaining history and supplies a supported loaded exit. C carries; B reacquires the original reference; E stops in the wait zone and holds for verified human take. D supplies payload evidence; E owns take-vs-drop completion. This coverage is now coherent and explicit.

A/B own ambiguous identity and request rejection. B/E own stale/lost/wrong target and reacquisition. B/C/D jointly own incompatible entry. D/C own empty bite, rise failure and unsupported loaded exit. E requests supported cancel/stop/help, revokes old epochs after manual/emergency, and prevents loaded expressions from opening the jaw. Physical estimators remain declared future implementations, which is acceptable at PLAN acceptance.

## Dependency bootstrap and staffing

F0 now assigns physical observations to Shawn and model/package reconciliation to the assistant. Historical CPU replay is available before F0; no new-body training is claimed. After F0, D starts from measured stable baseline entries, not a completed new C policy. B uses a fixture profile, then D publishes a real region; B/C must reach it continuously. C develops unloaded first, then uses D's validated payload/exit. Thus the former circular waiting condition is broken without treating development resets as final acceptance.

Five tasks are claimable increments, not five permanently assigned people. E makes the previously hidden integration work visible. The low-staff path is F0→C/D→B/E with A/B/E independent increments; it is a serial fallback, not a promise of four parallel teammates. One/two-week checkpoints explicitly permit bounded negative findings and conditional physical integration. This is a credible scope declaration.

## Finite repeat acceptance

Keep the current 18 scenarios and add the S1/S2 counterexamples. Rerun the actual parser→detector→coordinator rehearsal, showing stale selected-target stop and ordered stop→look acknowledgement→search. Review changed source hashes. No requirement to complete live speech, train new policies or make the physical robot fetch before accepting this plan.
