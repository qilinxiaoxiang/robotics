# pet/mind: drives, intentions, reflexes

Problem: `docs/PET_ROBOT_FEATURES.md` section 4 (initiative and liveliness) and section 11 (one mind, several bodies). A dumb pet is fine, a rigid pet is not. This package is the daytime mind: arithmetic drives and mood, an intention every 10-30 s chosen by a small language model from the body's primitives, a validator between the model and the body, reflexes for interrupts, and a fallback that works with no model at all. It reads a body card, so the same mind runs the MicroDuck and the OMX-F arm. Nothing here has driven the robot yet; `runner.py` (see `RUNNER.md`) is the live runner, proven against the simulated duck on 2026-10-29.

## Run

```sh
cd ~/code/robotics
pet/.venv/bin/pip install anthropic matplotlib pytest      # anthropic only for the API backend
pet/.venv/bin/python -m pet.mind.run_scenario --body duck   # the scripted day; model if reachable, else fallback
pet/.venv/bin/python -m pet.mind.run_scenario --body arm --backend fallback   # seconds, no model
pet/.venv/bin/python -m pet.mind.compare                     # rigidity and cost across the runs in out/
pet/.venv/bin/python -m pytest pet/mind/tests -q             # 60 tests, no model calls, no sim
pet/.venv/bin/python -m pet.mind.runner --dry --minutes 3     # the live runner against a fake brain (RUNNER.md)
```

`--backend` is `auto` (API key if one is configured, else the `claude` CLI, else fallback), `anthropic`, `claude-cli`, `ollama` or `fallback`. `--body` is `duck`, `arm`, `live` (`pet/state/body_card.json`, written by `pet/body/`) or a path. `--state-dir` points at the rules, plan, diary, personality and skills (default `pet/state/examples/`). Each run writes `out/<body>-<backend>/`: `behaviour.log`, `intentions.jsonl`, `calls.jsonl` (every model call: tokens, latency, cost, the raw answer, validation errors), `drives.png`, `summary.json`.

## The layers

- **Reflex layer** (`reflex.py`, on the A7Z in the real robot). A percept (sound, face, touch, stranger) gets an immediate reaction from a small table: orient toward a sound (`turn_head`, or `turn_camera` on the arm), `stop` and orient at a stranger, `stop` and `nod` when touched. The table lists alternatives per step, so it works on any body. A body only receives percepts it has the sensor for: the arm has no mic and no touch pads, so it never hears the keys or the doorbell.
- **Drives and mood** (`drives.py`). Per-second arithmetic: `bored`, `miss_owner`, `tired`, `curious`, `battery` in 0-1, and valence/arousal relaxing toward a target set by the drives (time constants 300 s and 60 s). Rates come from `personality.json`. Events satisfy or startle: touch lifts valence and halves miss-owner; a stranger raises arousal and curiosity; a pavlovian rule firing (keys jingle, w 0.8) raises miss-owner by 0.3 x w before the owner has even left.
- **Intention layer** (`mind.py`, `prompt.py`, `backends.py`; the Mac mini in the real robot). When the current intention ends (at least 10 s after it began, and intentions last at most 30 s) or a salient event arrives, the mind asks the model for the next intention as JSON: `{intention_text, steps: [{primitive, params}], duration_s, abort_if, mood_note}`. Minor events (footsteps) let the interrupted intention resume after the reflex, with no model call; salient ones (keys, doorbell, a face, touch) re-plan as soon as the reflex is done, and the prompt says what was interrupted.
- **Reflection layer** is `pet/learn/` (nightly). It writes the files this layer reads; see `pet/state/README.md`.

### The prompt

The system part is fixed per body: what the pet is, "vary what you do", the body's senses and whether it can move, every primitive with its parameter ranges, preconditions, posture effects and tags, the skills that validate on this body, the condition grammar, and the JSON format. The user part is the moment, in about 15 lines: time and period, posture and room, the world (owner in view or where last seen, stranger, touch, lights, battery), the five drives and the mood as numbers, the events of the last 5 minutes (including `expect: owner_leaves (w=0.80)` lines from rules), the intentions of the last 5 minutes with repeat counts, the interrupted intention, the active plan items, the rules with their weights, the personality text and 2-3 diary lines retrieved by tag and word overlap. A real example for the duck is printed at the end of this file.

### The validator (`validator.py`)

The only door from the model to the body. A step is a primitive name plus its declared numeric parameters, nothing else (an extra key in a step or an unknown parameter is rejected, so no joint command can pass). It checks: the primitive or skill exists on this body; each parameter is a number inside its range (out of range is rejected, never clamped); preconditions hold at that step, with posture tracked through the steps' effects (`stand` then `walk` from sitting is fine, `walk` alone is not); at most 6 steps; each step within the primitive's `duration_s_max`; the whole intention at most 30 s. Missing parameters take the in-range value closest to 0. Conditions outside the grammar are passed to the model as text and logged as `unchecked`. On failure the model is asked once more with the error text; a second failure, an unparseable answer or an offline backend falls back to drive-picked primitives (and the backend is not tried again for 5 minutes).

### Skills

`skills.json` entries are named step lists the model may call like a primitive. A skill is offered only on a body where every step validates (`greet_owner` with `turn_head` and `nod` exists on the duck; `greet_owner_wave` with `turn_camera` and `wave` only on the arm); its guards are checked like preconditions and its steps are expanded and validated like the model's own.

### Primitive backends (`executors.py`)

- `SimExecutor` lets simulated time pass and applies posture effects and room changes.
- `duck_commands()` documents and produces the mapping onto the control file of `microduck-sim/guide/firmware/mac/walk_brain.py` (`/tmp/duck_cmd.json`, modes `walk`, `sit`, `groundpick`, head targets in walk or sit mode): `stand` is walk at zero command (stand61 balances), `walk` is `{"mode": "walk", "vx", "vy": 0, "vtheta"}` then zero, `turn_head`/`look_around`/`nod` are head targets on a zero-command walk (or sit), `bow` is ground-pick phase 0.4 then 0.9 (the policy's standing rest; 1.0 wraps to a new descent), `rest` is sit with the head down, `wait` writes nothing. `DuckCommandStub` writes those commands atomically only when given a path. The live runner that times the commands on the real brain, reads posture and refusals back and feeds perception into `Mind.perceive()` is `runner.py` (`RUNNER.md`: how it is started against the simulated duck and the robot, what the first robot session looks like, how to stop it). With `--inbox` it also reads the voice layer's inbox (`inbox.py`): an owner task pre-empts the current intention and runs once, a rule goes into `rules.json` and pet/learn's matcher, and praise reaches the drives.

## Measured (2026-10-26)

The scripted day (`run_scenario.py`): five awake segments, 90 minutes in all, simulated second by second; the pet sleeps on its charger in between (drives only, no calls).

- 07:30 morning: the owner gets up, goes to the kitchen, sits in the living room, pets the pet.
- 08:10 leaving: the owner goes to the hallway, keys jingle, the door slams.
- 12:55 alone: the doorbell rings, a stranger (the cleaner) comes into the living room and leaves.
- 18:25 return: keys at the door, the owner comes in, sits down, pets the pet, goes to the kitchen.
- 21:15 evening: sofa, lights dim, the owner goes to bed.

Runs were made with `claude-haiku-5-5` through `claude -p` (effort low) and with the fallback alone, for the duck card and for the arm card, seed 7. Logs, every call and the plots are in `out/`; the numbers below come from `python -m pet.mind.compare` (`out/comparison.json`).

**The duck's day reads as a pet's day.** From `out/microduck-claude-cli/behaviour.log`:

```text
08:18:00  [sound] heard keys_jingle from the left
08:18:00    [rule keys-leave] expect: owner_leaves (w=0.80)
08:18:00    reflex: turn_head(yaw=1.2, pitch=0.1)
08:18:22  INTENT [llm 4.2s] "I'll nod twice to say goodbye while the owner gets their keys."  (wistful, hopeful)
08:18:32  INTENT [llm 5.3s] "I'll follow the owner closer and watch the door, since they're leaving soon."  (wistful, clingy)
08:20:00  [sound] heard door_slam from the left
08:21:49  INTENT [llm 2.8s] "The owner just left and I miss them, so I'll sit by the door and wait for them."
13:00:00  [rule doorbell-stranger] expect: stranger at the door (w=0.60)
13:00:15  INTENT [llm 5.6s] "I'll back away from the doorbell and rest quietly, since strangers make me shy."  (shy, wary)
18:30:59  INTENT [llm 5.8s] "I'll stand up, head toward the hallway, and greet my owner at the door."  (eager, hopeful, clingy)
18:31:14  [face] saw the owner
18:31:17  INTENT [llm 2.1s] "Owner just came back into view; I'll greet them calmly and nod for a head scratch."  (happy, relieved)
```

It uses its rules, diary and personality ("strangers make me shy", "nodding earned a scratch before"), and it gets things wrong in a visible way: at 18:29 the keys rule predicts the owner is leaving while the owner is in fact coming home.

**The arm never tries to walk.** Same mind, same day, the arm card (camera only, fixed in the living room, no walking primitive): 397 intentions, built from `turn_camera` 407 times, `wait` 311, `nod` 132, `look_around` 123, `wave` 51, `rest_pose` 49, `snap_gripper` 45, `beckon` 38. When the owner walks out of view it looks around, beckons and waves toward the hallway ("I'll check the kitchen side, then wave to call my owner back"). It reacts to nothing it cannot sense: no keys, no doorbell, no touch.

**Rigidity check** (one simulated day each; a sequence is the ordered list of primitives in one intention):

- Duck, model: 349 intentions, 162 distinct action sequences, 346 distinct intention texts, 5 % of intentions repeat the previous one, longest identical run 3, sequence entropy 6.8 bits. Most common: `turn_head -> nod -> wait` 24 times.
- Duck, fallback: 346 intentions, 133 distinct sequences, 0 % repeats, longest run 1, entropy 6.4 bits.
- Arm, model: 397 intentions, 89 distinct sequences, 395 distinct texts, 9 % repeats, longest run 5, entropy 5.3 bits. Most common: `turn_camera -> look_around -> wait` 40 times.
- Arm, fallback: 407 intentions, 127 distinct sequences, 0 % repeats, longest run 1, entropy 6.2 bits.

By repeat counts both are far from rigid, and the fallback even looks more varied, because it draws primitives and parameters at random. What separates them is whether behaviour follows the situation. Share of intentions with a social gesture (a social primitive that is not just orienting: `nod`, `approach_owner`, `wave`, `beckon`) when the owner is in view versus out of view:

- Duck, model: 48 % in view, 19 % out of view. Walking: 19 % in view, 44 % out of view (it goes looking).
- Duck, fallback: 31 % and 25 %. Walking: 59 % in view, 37 % out of view (it wanders away from the owner).
- Arm, model: 59 % and 46 % (it beckons and waves toward where the owner went).
- Arm, fallback: 58 % and 55 %.

The model runs predate one validator refinement: a parameterless posture step whose posture already holds (`stand` while standing) now runs instead of being skipped; answers accepted before are still accepted.

**Validity.** 348 of 361 duck calls and 397 of 402 arm calls returned a valid intention. The rejections were mostly posture preconditions (`walk` while sitting, `wave` while folded); the one re-ask fixed all of them except one duck answer that failed twice, the only time the fallback took over in either model run.

**Latency.** Per call through `claude -p`, including about 1 s of CLI start-up: median 4.4 s (duck) and 3.9 s (arm), 90th percentile 5.7 s and 5.5 s, maximum 7.9 s.

**Cost per day.** A call averages 2,427 input and 411 output tokens on the duck (2,352 and 361 on the arm; output includes the model's internal reasoning at effort low). At Claude Haiku 5.5 list price ($0.10 / $0.50 per million tokens, no prompt caching) that is $0.00045 per call. The model was asked 241 (duck) and 268 (arm) times per awake hour, re-asks included (a new intention every 15.5 s and 13.6 s), so a 16-hour awake day is about 3,850-4,300 calls, **$1.73 (duck) to $1.78 (arm) per day**, about $53 a month. The measured runs themselves cost $0.16 and $0.17 at API price for 90 awake minutes each. The obvious savings, not built: ask only when the situation changed or an intention ended early, which would cut the calls several-fold in quiet hours; a local model on the Mac mini costs nothing per call.

## Limits

- `run_scenario.py` is simulation only: the world, perception and room changes are scripted. `runner.py` replaces the scripted world with perception (`perception.py`: pads and gyro from the brain's rows, sound levels and camera frames from the A7Z agent) and checks every primitive against the brain's readback (`brain_link.Readback`); its own limits are in `RUNNER.md`.
- Simulated time stops while the model answers. On the robot the current intention keeps running while the next one is composed; the measured latency (above) is well inside the 10 s minimum interval.
- The API backend (`AnthropicBackend`, official SDK, `claude-haiku-5-5`, effort `low`) is written and exercised only by mocked tests: this machine has no API key and no `ant` profile. The measured runs used the same model through `claude -p` on the Claude subscription (`ClaudeCliBackend`, tools, settings and MCP off, our system prompt), which reports real token counts; the CLI adds about 0.7k tokens of its own framing per call, included in the input counts above.
- Ollama: not installed on the Mac mini, and its data volume had 4.7 GB free of 228 GB on 2026-10-26, about the size of a 4-bit Qwen 7B, so nothing was installed. `OllamaBackend` (`PET_OLLAMA_URL`, default `http://mac-mini:11434`, model `qwen2.5:7b-instruct`) is tested against a closed port (falls back); never run against a real Ollama.
- The fallback is random within the drives, so it looks varied on repeat counts while ignoring the situation; the context measures above show the difference. It is the offline floor, not a target.

## State-file contract

`pet/state/README.md` defines `body_card.json`, `rules.json`, `plan.json`, `diary.jsonl`, `personality.json`, `skills.json` and the event kinds. Examples for both bodies are in `pet/state/examples/`. Every file is optional; the mind runs with defaults when one is missing (tested).

## Example: the user part of the prompt

The duck in the hallway with the owner, a second after the keys jingled (captured from the real code path with a scripted backend). The system part is printed by `prompt.system_prompt()`; for the duck it is 2,293 characters, about 600 tokens.

```text
Time 08:18 (morning). Posture: standing. Location: hallway.
World: owner in view, no stranger, not touched, lights on, battery 100%
Drives 0-1: bored 0.02, miss_owner 0.23, tired 0.16, curious 0.40, battery 0.00. Mood: valence +0.16, arousal 0.46.
Recent events (oldest first): 08:18 heard keys_jingle from the left; 08:18 expect: owner_leaves (w=0.80)
Your last 5 min: 08:17 'I nod goodbye' [nod] (x6)
Today's plan: greet the owner and stay close while they get ready
What you have learned: When the keys jingle, the owner usually leaves soon. (w=0.80); The doorbell usually means someone I don't know is at the door. (w=0.60); Nodding at the owner when they are close often gets a head scratch. (w=0.55); Wandering around the living room late in the evening annoys the owner. (w=0.35)
Personality: Affectionate and clingy with the owner, a little shy with strangers, easily distracted by sounds, likes to show off small tricks.
Memories: 2026-10-25 08:31 Keys jingled and the owner left right after; I watched the door for a long time.; 2026-10-25 18:44 The owner came home and scratched my head when I nodded at them.; 2026-10-25 21:50 Evening on the sofa; I wandered and the owner told me no. Better to sit near them.
What does the pet do next?
```
