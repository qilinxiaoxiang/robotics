# pet/voice: a spoken sentence becomes a task or a rule

Problem: `docs/PET_ROBOT_FEATURES.md` section 6 (understanding the owner's words). Shawn, 2026-10-29: "语音转文字接一接, 看看能不能用语音控制它". The pet never speaks (2026-10-26); it answers with motion and quacks, so the chain ends in something the body can do, never in a reply.

The chain is four stages, each usable alone:

- `listen.py`: audio blocks in, one `Utterance` per spoken sentence out. Takes the robot's 4-channel 48 kHz stream (ears ch0+ch1 downmixed; `microduck-sim/CURRENT-STATE.json` `a7z_audio_capture`), a WAV, or a Mac microphone. Onset from `namecall.OnsetDetector` (the same detector that turns the duck's head to a call; imported, with a small fallback when `namecall.py` cannot be imported), end after 0.7 s under the room floor, 1-8 s, 0.3 s pre-roll, 16 kHz mono out.
- `stt.py`: `transcribe(wav) -> {"text", "lang", "words", "backend", "latency_s"}` over two backends. Local (default): sherpa-onnx on the CPU with SenseVoice small int8 (zh/en/ja/ko/yue; `--model whisper-base` is the Whisper alternative). ElevenLabs Scribe v2 (`POST /v1/speech-to-text`, `model_id=scribe_v2`), key read from the macOS Keychain into process memory, never printed; an HTTP error comes back as `{"error": "401 invalid_api_key"}` with empty text, and `--stt auto` then uses the local model.
- `intent.py`: the sentence to one JSON through Claude Haiku 5.5 (`pet/mind/backends.ClaudeCliBackend`, `claude -p` on the subscription; `--sonnet` for Sonnet 5.5): `task` (steps over the body card's primitives and `pet/mind` skills, validated by `pet/mind/validator.validate`, one re-ask on a rejection), `rule` (an owner instruction, parsed and validated by `pet/learn/instruct.parse_answer`, weight 0.6), or `ignore`; plus `reaction` praised / said_no / none for the learn layer. `say_back` is always null.
- `voice.py`: the loop. Each sentence appends an `owner_said` line to `pet/state/inbox/owner_said.jsonl` and writes `inbox/tasks/<stamp>.json` or `inbox/rules/<stamp>.json` (contract: `pet/state/README.md`, "Inbox from the voice layer"). `--dry` keeps everything under `out/dry/<start>/`.

## Run

```sh
cd ~/code/robotics
# models (git-ignored, about 240 MB + 150 MB)
curl -L https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2 | tar xj -C pet/voice/models
curl -L https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.tar.bz2 | tar xj -C pet/voice/models

pet/.venv/bin/python -m pet.voice.voice --dry --say "把橙色方块叼来"            # typed sentence -> intent -> out/dry/
pet/.venv/bin/python -m pet.voice.voice --dry --wav pet/voice/out/clips/zh01.robot.wav   # WAV -> listen -> stt -> intent
pet/.venv/bin/python -m pet.voice.voice --mic                                   # this Mac's microphone -> pet/state/inbox/
pet/.venv/bin/python -m pet.voice.listen --wav FILE | --mic | --cmd "..."       # segmentation alone
pet/.venv/bin/python -m pet.voice.stt FILE.wav [--backend local|elevenlabs|auto] [--model sense-voice|whisper-base]
pet/.venv/bin/python -m pet.voice.intent "Sit down"                             # one sentence
pet/.venv/bin/python -m pet.voice.synth && nice pet/.venv/bin/python -m pet.voice.bench_stt   # clips + STT benchmark
pet/.venv/bin/python -m pet.voice.intent --eval                                 # the 20 test sentences, live model
pet/.venv/bin/python -m pytest pet/voice/tests -q                               # 22 tests, no model calls
```

`pet/.venv` already holds numpy, scipy, sherpa-onnx and sounddevice. Set `PET_STT_MODEL`, `PET_STT_THREADS` (default 4) to change the local default.

## Measured (2026-10-29, MacBook Pro M-series CPU, 4 threads, `nice`)

Twenty synthetic clips from macOS `say` (ten English, Samantha; ten Chinese, Tingting; written to files, never played; `synth.py`, `out/clips/`). Error rate is word error rate for English and character error rate for Chinese; latency is decode time of a clip already in memory, after a warm-up. Full numbers in `out/stt_bench.md` and `.json`.

- **SenseVoice small (chosen default)**: 8.3 % error over all clips (en WER 10.7 %, zh CER 6.2 %), 15/20 exact; median 0.15 s, max 0.42 s per clip; model load 2.0 s. Misreads: `Fetch` as `Fedch`, `duck` as `dog`, `beak` as `be`, `叼` as `雕`, `别` as `边`. Short words from a synthetic voice; the intent model recovered the two that mattered (see below).
- **Whisper base int8**: en WER 3.6 % (9/10 exact), zh CER 75 % (writes traditional characters, hallucinates on short Mandarin: `过来` became `Cô lại`, `停` became `Thank you`); median 0.31 s, max 2.3 s. Good English, unusable Chinese at this size.
- **ElevenLabs Scribe v2**: `401 invalid_api_key` on the first clip (the key in the Keychain had a 2026-09-25 expiry); not scored.
- **The whole chain on the robot-format clips** (4-channel 48 kHz with room noise, through `listen.py`, then SenseVoice): 20/20 segmented into one utterance each, 13.3 % error (en 10.7 %, zh 15.6 %: the padded `停` came back as `Ting.`), median 0.14 s.
- **Intent, Haiku 5.5 through `claude -p`**: 20/20 on the test set (`out/intent_eval.md`): fetch the orange block (en, zh) became look_around -> walk -> groundpick; come here became turn_head -> walk; sit, stop, open your beak, turn around (three 0.3 rad/s walk turns) became tasks; "stop going in the bedroom", "别进卧室", "don't quack at night", "以后别在厨房里乱跑" became operant rules `self:entered(bedroom|kitchen) -> owner:said_no` and `self:vocalised(quack) -> owner:said_no`; "good duck" and "好鸭子" were ignore with reaction praised; four lines of chatter were ignored. Median 4.9 s, max 7.5 s per sentence (CLI start-up included), $0.0073 for the run at list price, billed to the subscription.
- **End to end** (`out/e2e-zh01-robot-wav/voice.log`): the `把橙色方块叼来` robot-format clip -> utterance 2.7 s -> SenseVoice 0.18 s read `把橙色方块雕来` -> Haiku 8.8 s composed "I'll find the orange block and carry it back to you": look_around(4 s) -> walk(0.15 m/s, 3 s) -> groundpick(phase 1, 5 s) -> turn_head -> walk, abort_if not standing / touched -> `tasks/20261029-040816-001.json`, validated. A typed "Stop going in the bedroom" (`out/e2e-typed-rule/`) became the bedroom rule file in 5.8 s.

The Mac mini (the deployment host for these models) had 558 MiB free on its data volume at the time, so the models and benchmarks ran on the MacBook; the Mac mini needs space freed before the loop can run there.

## The robot test (what Shawn does)

Nothing in this directory has run on the robot or heard its microphones. The first robot test keeps every model on a Mac and only reads the A7Z stream over ssh:

1. Robot on, brain running or not (capture needs neither the servo bus nor the IMU, so no robot I/O lock is taken); `namecall.py` not running (it holds the same capture device). From a Mac terminal, the first command:

   ```sh
   cd ~/code/robotics && pet/.venv/bin/python -m pet.voice.voice --robot --host a7z --dry
   ```

   `--dry` keeps the first session under `pet/voice/out/dry/<start>/`; drop it once the log looks right, and the runner will find the files in `pet/state/inbox/`. The ssh alias is `a7z` (CURRENT-STATE `a7z_network`); the capture line it runs is `arecord -q -D hw:CARD=sndi2s0,DEV=0 -c 4 -r 48000 -f S32_LE -t raw -`.
2. Wait for the `listening on robot:a7z at 48000 Hz` line, then from about a metre in front of the duck say, one at a time with a pause between: "过来", "坐下", "把橙色方块叼来", "别进卧室", "好鸭子", and one sentence to someone else in the room.
3. What the log should show per sentence: an `[utterance]` line (1-8 s, peak well above -40 dBFS, onset over floor 10 dB or more), an `[stt]` line with the sentence in the right language within about 0.5 s, and an `[intent]` line within about 10 s: `task` with steps for the first three, `rule self:entered(bedroom) -> owner:said_no` for the fourth, `ignore, reaction praised` for the fifth, plain `ignore` for the last. No utterance lines while the room is quiet; if servo noise or the fan triggers utterances, restart with `--threshold-db 18` (the onset threshold over the room floor; default 12, namecall's) and report the `onset over floor` numbers it printed.
4. Nothing moves in this test. Moving on a task file is the runner's job (`pet/mind/runner.py`), which does not read the inbox yet.

## Renewing the ElevenLabs key

One line, after a new Speech-to-Text-scoped key exists: `security add-generic-password -U -s elevenlabs-codex-scribe-20260826 -a xiangzheng -w` (it prompts for the key; nothing is passed on the command line). Then `pet/.venv/bin/python -m pet.voice.stt pet/voice/out/clips/en04.wav --backend elevenlabs` should print `Stop.`.

## Limits

- Synthetic voices only: the error rates are for `say`, not for Shawn's voice in a room with a walking duck. The chain's robot numbers come from the test above.
- The onset detector is namecall's: a loud non-voice sound (a clap, a dropped object) also becomes an utterance; SenseVoice then returns little or nothing and the loop logs it and moves on.
- `--robot` streams raw audio at 768 kB/s over Wi-Fi and Tailscale; fine for a test, not for all day. The A7Z-side alternative (segment on the robot, send 16 kHz clips) is not written.
- One capture reader per device: `namecall.py` and `voice.py --robot` cannot listen at the same time until a shared capture (one arecord, two consumers) exists.
- Intent latency is 4-9 s through the CLI, so a spoken "stop" is a slow stop; the reflex path for a few fixed words (stop, 停) is not built.
- The runner's pickup of `inbox/tasks` and `pet/learn`'s merge of `inbox/rules` are specified in `pet/state/README.md` and not implemented.
