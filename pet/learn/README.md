# pet/learn: learning from a handful of exposures

Problem: register `docs/PET_ROBOT_FEATURES.md` section 3 (memory and learning from experience). The pet should learn like a dog from a few exposures (keys jingle, then the owner leaves), keep what the owner tells it as rules ("stay out of the bedroom": it goes less, still sometimes), and be visibly different the next day because of what happened. No RL or imitation learning here: a frontier model reflects at night, arithmetic and a small model act on the result during the day.

## Pipeline

1. **Event log** (`events.py`). Perception and the pet's own actions write JSON lines `{t, type, args}` from a fixed vocabulary of 41 types (`VOCAB`). Rule patterns name a type, with its argument when it has one: `sound:keys`, `owner:said_no`, `self:entered(bedroom)`. `synth_day(day, seed)` generates a day with planted regularities for testing without a robot.
2. **Night: reflection** (`reflect.py`). `compress_day` builds a digest of the day: counts, co-occurrence windows with lift, the owner's sentences, absences and other episodes, and the timeline. One structured call to `claude-opus-5-5` (`PET_REFLECT_MODEL`, effort high) returns rule candidates, diary entries, personality nudges, tomorrow's plan and optional skills built from the body card's primitives. `validate_reflection` drops anything malformed, out of bounds or outside the vocabulary, then `apply_reflection` merges the rest into `pet/state/`. New rules start at weight 0.3. A rule that already exists keeps its weight; the model does not set weights. `fallback_rules` proposes rules from co-occurrence lift alone, with no model, so the pipeline runs offline. Every night logs both proposal sets and their overlap (`comparison`).
3. **Day: Rescorla-Wagner** (`rw.py`, `match.py`). The matcher opens a trial when a rule's trigger fires and its context holds (for example `owner_home`). An outcome inside `window_s` is a confirmation: V <- V + alpha(1 - V). An expired window is an omission: V <- V + alpha(0 - V). If the owner leaves during the window, the trial is voided. Learning rates: alpha 0.3 for pavlovian rules (three straight confirmations take 0.3 to 0.76) and 0.15 for operant rules. Rules with no trial that day decay with tau 10 days and are forgotten below 0.05. Rules from owner instructions never decay. A rule expecting `owner:said_no` or `owner:praised` also accepts a plain `owner:said(text)` that counts as one. `FuzzyJudge` decides with `claude-haiku-5-5` when `use_model=True`, with a Chinese/English keyword list otherwise, and caches each decision per sentence.
4. **Owner instructions** (`instruct.py`). A transcribed sentence becomes an operant rule (`self:entered(bedroom) -> owner:said_no`, context `owner_home`, weight 0.6, `source: instruct`) or a rejection with a reason. The default model is `claude-haiku-5-5` (`PET_SMALL_MODEL`). The prompt never lets the model refuse an instruction for being unkind or odd; it rejects only chatter and things the body cannot do.
5. **Retrieval** (`retrieve.py`). Diary lines are embedded with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` through fastembed (ONNX, CPU, 384-d, no key). This model was chosen because Chinese and English land in one space: "主人拿起钥匙要出门" retrieves "The keys jingled and then the door closed" (cosine 0.79 for a direct translation). If the model is missing, a hashed character n-gram vector is used and tagged `hash`. `retrieve(query, k)` reads `pet/state/diary.jsonl` and writes back the missing embeddings.

Model transport (`llm.py`): `api` (the `anthropic` SDK, structured output via `output_config.format`, server-side refusal fallback on Opus) when `ANTHROPIC_API_KEY` or an `ant` profile exists; otherwise `cli` (`claude -p --json-schema`, billed to the Claude subscription, with tools, settings, hooks and MCP all disabled so the pet's prompt is the whole context); `ollama` with `PET_OLLAMA_URL`. On 2026-10-26 there was no API key on this MacBook and no Ollama on either the MacBook or the Mac mini, so the measured runs below used `cli`. Every call appends tokens and cost to `out/llm_costs.jsonl`.

State files (`state.py`) follow the schemas in `pet/state/README.md`: `rules.json`, `plan.json`, `diary.jsonl`, `personality.json`, `skills.json`. Rules may carry optional keys that pet/learn needs and other readers can ignore: `window_s`, `context` (`owner_home` | `owner_away` | null), `source`, `created`, and for instructions `said` and `direction`. Personality nudges move a value by at most 10 % a night and stay inside `drive_rates` 0.5-2.0 and `thresholds` 0.3-0.9. Skills are validated against `pet/state/body_card.json`, else a card in `pet/state/examples/`, else the built-in duck list (`DUCK_PRIMITIVES`).

## Run

```bash
pet/.venv/bin/pip install -r pet/learn/requirements.txt
```

```bash
pet/.venv/bin/python -m pytest pet/learn/tests -q
```

```bash
pet/.venv/bin/python -m pet.learn.demo
```

`--no-llm` skips the model call. `--backend api|cli|ollama` picks the transport. `--fuzzy-model` sends fuzzy sentences to Haiku. The demo keeps its state in `pet/learn/out/state/` and never touches `pet/state/`. Single steps:

```bash
pet/.venv/bin/python -m pet.learn.reflect pet/learn/out/days/day1.jsonl --date 2026-11-02
```

```bash
pet/.venv/bin/python -m pet.learn.instruct "别进卧室，听话"
```

## Measured (2026-10-26, synthetic days, seed 0)

- Keys -> owner leaves: born on night 1 at 0.30, then 0.66, 0.88 and 0.94 at the end of days 2-4, and 1.00 on day 7 (14 confirmations, 0 omissions).
- Bedroom -> owner says no (planted at 80 %): 0.81 on day 3, then 0.69, 0.64, 0.69 and 0.79 on days 4-7 (mean 0.70); evidence 25 confirmations, 9 omissions, so 0.74 observed.
- TV -> doorbell (planted twice on day 1 only): 0.30, 0.21, 0.15, 0.13, 0.09, then forgotten on day 6.
- Plots: `out/weights_by_day.png` and `out/day1.png` to `out/day7.png`; numbers in `out/weights_by_day.json`.
- 20 seeds, fallback nights: all three checks pass on 16. Two failures are keys: on that day 1 the owner left once, so no rule was born until night 2. Two are bedroom: the sampled no rate was 0.66-0.70, and the weight tracked it. The weights follow the evidence; the misses are the data.
- Frontier reflection on day 1 (`out/reflection_day1.json`): Opus 5.5 through the CLI, 36 s, 6,876 input tokens (cache write) and 3,896 output tokens including thinking. It cost $0.133 at list price, billed to the subscription. It proposed 6 rules, all of which the fallback also found, including the keys, bedroom and spurious TV rules. The fallback had 4 more rules that the model left out as mechanics or duplicates (`sound:keys -> sound:footsteps`, `owner:sat -> sound:doorbell`, ...). The model also wrote 8 diary entries, 2 bounded nudges, 6 plan intentions (go to the door at 18:05 before the usual 18:18 return) and 2 valid skills (`greet_at_door`, `leave_bedroom_quietly`). No validation problems, and no diary line evaluated the owner.
- Instruct, Haiku 5.5 through the CLI: "别进卧室，听话" became `self:entered(bedroom) -> owner:said_no`, owner_home, 10 s. "今天好累啊" was rejected as a remark about the owner, not a request. "Don't quack at night, I'm sleeping" became `self:vocalised(quack) -> owner:said_no`, and "at night" was lost (see limits). Each call was $0.0004-0.0007.

## Cost

- **Per night**: about $0.13 at list price for a synthetic day of 91 events (input $4 and output $20 per million tokens, Opus 5.5). The digest carries the full timeline at about 25 tokens per event, so a real day of 1,000 events adds about 25k input tokens, roughly $0.10. Budget $0.15-0.30 a night, which is $5-9 a month. Through the CLI the night bills the subscription instead of money.
- **Per day**: Haiku 5.5 only for instructions (about $0.0005 each) and, with `--fuzzy-model`, ambiguous sentences (about $0.0005 each, cached per sentence). With 3 instructions and 20 fuzzy sentences that is about $0.01 a day. The matcher and Rescorla-Wagner are arithmetic and free. Embeddings run locally.

## Limits of the vocabulary

- A regularity is learnable only if both ends are event types. Smells, the owner's mood, which shoes they put on, and a sound the classifier has no class for all stay invisible. The way to grow this is a general sound classifier (YAMNet's 521 classes mapped to `sound:*`) and object labels (`see:object(label)`).
- Context is only owner home / away. Time of day, the day of the week and "the owner is asleep" are not rule contexts yet, so "don't quack at night" becomes "quack less". `plan.json` is where time-of-day patterns live today.
- Rules are pairs (A then B within a window). Chains (keys, then shoes, then leaving) and absences ("no walk today") are not rules; the nightly model may describe them in the diary and plan.
- The fallback needs at least two co-occurrences in one day. A one-off event teaches nothing until it repeats, which is also what keeps coincidences from becoming rules on day 1 without a second sighting.
- `owner:said_no` counts only when the owner reacts. While the owner is away, trials of an `owner_home` rule are skipped, so the pet learns nothing about rooms while it is alone.

## Character constraint

The pet is unconditionally supportive and never moralises (register section 10). The reflection system prompt (`reflect.CHARACTER`) says so explicitly and tells the model to record the day, never to evaluate the owner. `validate_reflection` also drops any diary line containing evaluative words aimed at the owner ("should", "too late", "lazy", "应该", ...) and logs it under `problems`. The instruction prompt never lets the model refuse an owner instruction. The owner's data is the owner's: the state lives in local plain files, and the only data that leaves the device is the day digest sent to the model provider.
