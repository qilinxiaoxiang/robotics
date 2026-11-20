# Flight training: handover to an executing session (Opus 5.5)

**Draft, not in force (2026-11-20).** Shawn: "等有了结果再写交接清单". No session takes over from this file yet. It is completed after the thrust validation result is in and he has decided on the whole route; the approved stages and the queue are written in then.

This file tells a session that runs approved training stages what is fixed, what it may decide, how to run one stage, and when to stop and hand the work back to a Fable session. It holds no numbers of its own: goals, stages, pass and kill lines, budgets and results live in `TRAIN-CONTRACT.json` in this folder, and the status Shawn reads is `train/OVERVIEW.html`.

Handover starts only when Shawn has approved the stage to run. His approval is in the stage's `approval` field with his words. A stage that is `proposed` is not yours to start.

## 1. What is fixed (the owner's goal and decisions)

Read line B of the contract (`goal_zh`, `owner_words`) before anything else. In short, with his words:

- **Two policy sets.** "走路的就不带涵道电机输入和输出 沿用walk61 背包形态自成一套 后面再考虑要不要融合". Without the pack the robot runs the deployed walk61 and stand61 unchanged. Every stage you run is about the pack set.
- **Order.** "先不开 我们要先做一个能用背包走路和起飞的模型起来". The world-model line (line A, stage A0) stays on hold until he says otherwise.
- **Load is told to the model.** "背包自重我们知道 四个涵道电机的出力我们也知道 就能算出一些东西 作为输入给到机器人". Fan output is an input of the policy. The policy's outputs stay the 14 joints; the fans belong to the flight controller.
- **Thrust acceptance.** "站着不摔是肯定要的 而且也不能乱动和挣扎 走路可以不考". Standing holds at every thrust level without flailing; walking is tested up to half thrust.

Two facts measured on 2026-11-20 that every stage builds on: a with-pack policy must be trained with the servo gain varied (fq2 1999: 0 falls at the nominal gain, 53 to 58 of 60 at the doubled gain), and the doubled-gain filter only rejects (a pass on it is the ticket to a robot test, never proof).

## 2. What you decide and what you do not

**Yours (reversible means inside an approved stage):** when to start within the approved window; retrying a job that died for an infrastructure reason with the same command; writing a scoring or fetch helper that implements the stage's written `pass.metric` exactly; watcher cadence; wording of reports.

**Frozen (changing any of these is a hand-back, section 4):**
- The goal text, the stage's one question, its `pass`, `kill`, cells, seeds, selection rule and budget.
- The recipe: start weights, inputs, network, reward terms and weights, randomisation ranges, iteration and hour caps, the arms. One stage changes one thing, and that thing is already written in `changes_vs_previous`.
- The number of attempts. A second attempt needs a new hypothesis, which is design work.
- Scope: no new stage, no extra arm, no "while it runs" experiment, no use of idle quota. Idle compute or an expiring quota never justifies a launch.

**Never, whatever the result:** touch the robot, the A7Z, the deployed runtime models or the team repository; push any repository; spend Modal money (free credit only, hard stop at the metered 50.00 USD) or exceed the stage's Kaggle hours; run training or simulation batches on the MacBook; work around a launch-guard denial; call a missed line "close enough"; change a threshold after seeing a result.

## 3. Running one approved stage

1. **Read.** The stage block in the contract, its `attempt_1_draft` (hypothesis and prediction were written before any run and stay as written), `REQUIREMENTS.json`, and the training-effort skill (`~/.claude/skills/training-effort/SKILL.md`). Robot facts come only from `microduck-sim/CURRENT-STATE.json`.
2. **Open the attempt.** Move the draft into `attempts` with the real start time, set the stage `running`, run `python3 ~/code/claude-config/scripts/train_contract_check.py TRAIN-CONTRACT.json` until it prints OK. One stage per line runs at a time.
3. **Launch exactly the recorded command.** Any pre-launch audit the command needs runs first on the Mac mini under `train/mini_lock.sh`. Jobs that outlive the turn are detached on the machine that runs them, write a heartbeat, and get a watcher sized to the job (`~/code/claude-config/rules/common/long-jobs-detached-and-watched.md`). Stop a run on the task metric the stage names, never on total reward.
4. **Score and record.** Fetch, apply the stage's selection rule and `pass.metric` as written, fill `result`, `verdict` (pass or fail) and `evidence`, and write the check against the prediction line by line, including where the prediction was wrong. Update `train/OVERVIEW.html`, append to `train/RUNLOG.md`, commit locally with only the files you changed.

Report to Shawn in Chinese, plain words, no stage codes: what was run, the pass and kill numbers against the lines, whether the prediction held, and the next step. A decision that is his is asked with the `ask-clearly` template inside the message. Helpers you send out run on `opus` with a self-contained brief (`~/code/claude-config/rules/common/delegate-to-cheaper-models.md`).

## 4. When to hand back to Fable

Stop executing, leave running jobs detached and watched, and hand back when any of these is true. The split is by what kind of thing went off the written path.

**The result needs a route decision**
- A stage's verdict is fail, its kill condition is met, or a second attempt would be needed.
- The falls pass and another line misses (speed, action jumps, calm standing), or one arm passes and the stage's main arm does not.
- A result contradicts the written prediction on a point given 70 % or more.

**The measure itself is in doubt**
- The reference policies no longer reproduce in a scoring run: walk61 and stand61 without the pack exceed 6 window falls of 60 at the doubled gain, or walk61's nominal speed is off by more than 30 % from 0.089 m/s.
- The feed check or an assertion in a scoring script fails for a reason that is not a typo or a path.
- The same fault appears twice and its cause is not found by one instrumented rerun.

**The written sheet no longer fits**
- Running the stage as written is impossible (a flag the launcher refuses, an audit that cannot pass for a structural reason, a missing asset) and the fix changes anything in the frozen list.
- The next stage has no approved sheet, or its sheet depends on a result that came out differently from what the sheet assumed.
- You notice a requirement in `REQUIREMENTS.json` that no cell or training term of the running stage covers.

**The owner or the robot is involved**
- Shawn states a new requirement or changes a decision: write his words into the contract in the same turn, then hand back.
- Anything that would put a model on the robot: the first with-pack test, fans on the ground, take-off. The test protocol is written by Fable and approved by Shawn.
- A step needs authority the contract does not give (money, a push, a deletion).

**How to hand back.** Add an entry to the stage's `history` in the contract: what was run, the numbers, which trigger above fired, and the one question that needs deciding. Then tell Shawn in one line: "需要交回 Fable：" plus the reason. He switches the session's model or opens a Fable session; that session starts from the contract and this file. Do not prepare the route decision yourself and do not start "the obvious next thing" while waiting.
