# Incident: V1.9 release stalled about 6 hours (2026-10-13)

Owner's finding: the work was not complex, yet the session ran from 02:25 to 09:50 before the first print file existed,
and at 09:37 the remaining estimate was still "2 to 3 hours". Previous releases took minutes: the V1.7 and V1.8 slicing
runs each span 2 minutes of file timestamps, and the print gate is about 3 minutes. V1.9 slicing, once started, also
took 2 minutes (09:48 to 09:50).

Times below are local (America/New_York). Evidence: the session transcript
`~/.claude/projects/-Users-xiangzheng-code-robotics/cb2a1eef-7aa0-4728-afad-9518fb22c188.jsonl`, file mtimes under
`guide/extension-20261012-neck-audio/jaw-neck-check/` and `guide/print/ext-v19/`, and the bounded-runner report files.

## Where the time went

- 02:25 to 03:04: inventory of open problems and three decisions for Shawn. Five short agents, all back by 03:35. Fine.
- 03:04: Shawn fixed the V1.9 scope (open fixes, speaker and amplifier, 12 V power) and went to sleep: "其他做好了再和我说吧".
- 03:06 to 03:08: four work agents started. Rear pack done 04:21. Jaw 25° software cap done 03:56. Amp soldering page
  done 04:10. Extension geometry (cap, retainer, four clips, resistor placement) never finished; it was stopped at 09:42.
- **03:57: the coordinating session, on its own, replaced the finished 25° jaw cap with a pose-dependent cap** and told
  the jaw agent to sweep neck pitch, head pitch, yaw and roll on a 156,695-node grid under the shared CAD lock. Nobody
  asked for it. The handoff had already concluded that a 25° cap clears every yaw and the policy opens at most 18.33°.
  The trigger was the agent's own hand-back section "Gaps the limits do not cover", listing poses the policy never uses
  (roll ±25° at pitch 50 to 65°, pitch −45° with yaw 110 to 160°). The sweep held the exclusive lock from about 04:30 to
  07:58 (bracket 37 s, neck 852 s, torso 438 s rescanned for 11 neck values, check 1,488 s) and reported at 08:01.
- 04:36 to 09:42: the extension agent, queued behind that lock, wrote 33 scripts of its own checks. Its dispatch had
  told it to "run your own equivalent checks" when the gate scripts could not take extra solids, instead of integrating
  the parts into the guide data and running the 3-minute gate. From 08:17 it read the new pose-cap table and started
  checking the clips against the jaw (jaw_contact, jaw_reach 414 s, jaw_cap, jaw_span, clip relocation): 1.5 hours of
  jaw work for parts that do not touch the jaw, then "Decision needed: regenerate the table" in its README.
- 04:22 to 08:01 and 08:22 to 09:37: the coordinating session did nothing. It had no deadline on any agent, never read
  the lock state, and woke only on hand-backs. Shawn's question at 09:37 was the first check on progress.
- 09:39: the session explained the five hours as a consequence of the lock ("同一时间只跑一个任务") and quoted
  "2 to 3 hours" more. That framing treated the unrequested sweep as normal work.

## Causes

1. **Scope grew without the owner.** A gap reported by an agent about its own work was treated as a task. The same
   pattern is in the violation log two days earlier (OMX calibration, 2026-10-11: criteria never derived from the task,
   no time box, promised minutes and took an hour). This is the second occurrence, now at 5 hours.
2. **No time budget anywhere.** The runner accepted `--seconds 1500` for every job; the dispatch text repeated that
   number as the default. Nothing distinguished a 3-minute gate from a 25-minute sweep chained 11 times.
3. **The lock was invisible.** `run_bounded_cad.py` serialised jobs correctly but kept no record of who held the lock,
   so neither the session nor a second agent could see a 4-hour holder; the exit-75 retry loop just waited.
4. **Open-ended gate text.** AGENTS.md said "check new printed parts against recorded walking frames" and
   "check connector insertion" without naming a script. No gate script implements walking frames, so agents invented
   sweeps to satisfy the sentence.
5. **Parallel audit instead of integration.** Telling the geometry agent to build "equivalent checks" produced a second
   audit stack (33 scripts) instead of the existing gate.

## Fixes made the same morning

- `build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py`: every job is clamped to 600 s
  unless `MICRODUCK_CAD_LONG_JOB_OK` carries Shawn's explicit go (recorded in the report and ledger); every start and
  end is appended to `.cad-queue.log`; `--status` prints the current holder; an exit-75 refusal names the holder.
  Tested: clamp without the token, pass-through with it, holder shown to a queued caller, status while held and after.
- `robotics/AGENTS.md`: the four gate scripts are the whole gate; a check none of them implements is a study, not a gate
  item; an agent-reported gap is not a task; the runner's clamp and `--status` are named; the walking-frames sentence
  is gone.
- The pose-cap table (`guide/firmware/pi/jaw_pose_caps.json`) and its tests exist and pass; they are kept as a
  deliverable for Shawn to accept or drop. The V1.9 clips and wires are not in it, by his decision.
- Violation-log entries for the two failures (scope growth without authority; no time box or monitoring).
