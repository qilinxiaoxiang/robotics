# Name call on the robot: hear a call, turn the head to it with a take, quack on arrival (2026-10-29)

Pet register section 12 (`docs/PET_ROBOT_FEATURES.md`, "Responding to its name, technique"). First pet behaviour meant
to run on the robot. Program: `microduck-sim/guide/firmware/mac/namecall.py`. Nothing here has run on the robot or the
A7Z yet; the robot test plan is section 5 and Shawn runs it.

## 1. Result

- The chain works off the robot: three-mic capture format -> voice-band onset detector -> GCC-PHAT / SRP-PHAT direction
  on the head's real microphone geometry -> a `pet/express` take (`acknowledge`) -> walk_brain's head command path at
  50 Hz -> a pitched duck call on the head's arrival. 29 tests pass (`test_namecall_*.py`); `pet/express` tests still
  pass (28).
- Duck sim under stand61 (the `pet/express` plant, as-built model with the saddle manifest, 7.0 V, 4 % read drops,
  `results/sim_real.json`, Mac mini): 72 calls over 12 seeds, 71 detected (the miss is one clap), 0 false alarms,
  0 falls. Azimuth error mean 1.4 deg, p90 3.1, max 7.0, no front/back mistake (12 of the calls came from behind).
  Head latency from the sound's onset: median 0.40 s (p10 0.16, p90 0.72, max 0.80); direction decided 60 ms after
  the onset. Overshoot past the wanted command median 0.12 rad (p90 0.30, max 0.52, double_take). Trunk tilt median
  0.45 deg, p95 0.81, max 0.99 deg; drift at most 2.3 mm. Takes: curious_turn 22, double_take 22, quick_snap 14,
  glance 13; 49 quacks (glances are mostly silent, habituation mutes some).
- Stress bracket (6.6 V, 8 % drops, `results/sim_stress.json`): identical detections, 0 falls, tilt max 0.89 deg.
- `--smooth` (no EMA pre-inverse, `results/sim_smooth.json`, 36 calls): 0 falls, overshoot max 0.25 rad, tilt max
  0.80 deg; the fallback flag for the robot if the pre-inverted targets look jerky there.
- Name mode for "Mochi" (`--name mochi`, opt-in; `--any-voice` stays the default): built and measured off the robot,
  section 9. The gate works (direction taken at the word, the duck's own calls never wake it), but the public
  keyword model catches only about 30 % of synthetic "Mochi" calls at 20 dB SNR, with about 20 false wakes per hour of
  speech. It is not ready to replace `--any-voice`.

## 2. Sound in and direction

Capture (CURRENT-STATE `a7z_audio_capture`): card `sndi2s0` found by name, `hw:CARD=sndi2s0,DEV=0`, 4 channels
S32_LE 48 kHz through `arecord -t raw`; ch0 left ear, ch1 right ear, ch2 back mic, ch3 nothing; samples are 24-bit
left-justified (`>> 8`, as `duck_selfcheck.py` reads them). The program reads 20 ms blocks and keeps 240 ms.

Microphone positions (head frame, x forward, y left, mm): ears (60.5, +-38.5) from
`guide/print/ears-mouth-20261023/interface.json`, back mic (-19.9, -11.0) from the V1.33 seat (three-mic report
`~/code/reports/src/20261024-microduck-three-mic-localization.md`, section 4; `build_cap_xiao.py`). Ear spacing 77 mm
(the brief's "about 6 cm" was approximate), back mic 95 mm from the left ear.

Detector (`OnsetDetector`): per block the energy in 300-4000 Hz over a room floor that follows the noise with a 3 s
time constant but only while nothing is loud. A call is 12 dB over the floor, at least 6 dB over the quietest of the
previous five blocks (a swell is not a call), at least 35 % of the 100-8000 Hz energy inside the voice band (hum and
servo whine fall outside), confirmed by the next block still 6 dB over the floor (a click is not a call, a clap's tail
is), then 2.5 s refractory. It is deaf while its own quack plays and 0.6 s after, and during its own take (servos
10 cm from the mics); the floor is re-estimated after a playback because a playback stream can reconfigure the shared
I2S0 (`duck_selfcheck.py` plays its sweep in S32_LE for that reason; `aplay` of a 16-bit call may shift the capture;
this is the first thing the robot test watches).

Direction (`Localiser`): GCC-PHAT (band 300-4000 Hz, 64 ms window starting 10 ms before the onset block) for the
three pairs, summed on a 1 deg azimuth grid at each pair's predicted lag (SRP-PHAT), parabolic refinement; the back
mic settles front/back and the margin against the mirrored half-plane is logged. Far field, planar: the caller's
height is not estimated, the look-up pitch is fixed (`--pitch 0.2` rad).

Expected resolution from the geometry (`results/direction_synthetic.json`, free field, no head shadow or echo): on the
ear pair ahead 1.33 deg per 0.25 sample of lag error, 5.3 deg per sample. Synthetic 4-channel scenes all round the
circle (72 directions per SNR): at 30 and 20 dB SNR mean error 0.8-0.9 deg, max 2.6-3.3; at 10 dB mean 1.6, max 5.6;
at 5 dB mean 3.4, max 12.6; no mirror error at any SNR. With ch2 silent (back mic not fitted) the estimate is one of
the two images and the margin reads 0. The 2026-10-24 report's expectation for the real room is about 10 deg (echo,
head shadow): the robot test measures it (section 5.4).

No recorded A7Z 4-channel wav exists in the repository (the 2026-10-29 bench capture stayed on the A7Z in /tmp), so
only synthetic scenes were replayed; `namecall.py --wav FILE --no-head --mute` replays a real one when Shawn records it
(`arecord -D hw:CARD=sndi2s0,DEV=0 -c 4 -r 48000 -f S32_LE -d 20 ~/duck-logs/calls.wav` on the A7Z).

## 3. Keyword spotting: first cost estimate (superseded by section 9)

Section 9 has the built name mode and its measured A7Z cost; the estimate below was made before the duck had a name.

sherpa-onnx 2.0.0 `KeywordSpotter` with the public zipformer `gigaspeech-3.3M-2024-01-01` int8 model, one thread, 20 ms
chunks, 43 s of audio on this MacBook (M1 Pro): real-time factor 0.017 CPU (`results/kws_bench.json`; it spotted
"LIGHT UP", "LOVELY CHILD", "FOR EVER" in the model's own test clips). A7Z estimate (Cortex-A76 at about a quarter of
an M1 Pro core, CURRENT-STATE `a7z_closed_head_thermal_and_resets` for the 416 MHz throttle): 0.07 of one core cool,
0.32 of one core throttled. The detector chain itself costs 0.012 on the Mac (`results/detector_cost.json`), 0.05 /
0.22 on the A7Z by the same scaling. Together with the brain (one core at 50 Hz, p90 24.6 ms when throttled) the
spotter would take the throttled board past a quarter of a core, so this delivery detects any voice-band onset and
leaves a `--kws` hook for later (a model directory plus keywords file; the duck has no name yet in the register).

## 4. Motion and quack

`HeadPath` owns one `pet.express.Expressor` on the duck card (`pet/express/cards/duck.json`). A detection becomes
`acknowledge(Target(yaw, pitch))` with warmth 0.8 and energy 0.7; the take (quick_snap, curious_turn, double_take,
groggy, glance), its jitter, habituation and the call events are `pet/express`'s, unchanged. The azimuth is in the
head frame, so the current commanded head yaw is added to put the caller in the resting frame. The look target is
capped at +-1.2 rad (`YAW_CAP`): a call from behind turns the head as far as it goes on that side and the log says
`behind`. Outputs stay inside the card's limits, which sit inside walk_brain's trained `HEAD_RANGE` (1.10, 1.10, 1.40,
0.31); the last command of every response is the policy default head pose.

The brain smooths head targets with `head_cmd += 0.2 * (target - head_cmd)` (`HEAD_ALPHA`), which cannot overshoot or
anticipate, so the path sends `r = c + (y - c) / 0.2` clipped to HEAD_RANGE (`pet/express/duck.py`'s pre-inverse; the
sim evidence above and `pet/express`'s 360 calls used it). `--smooth` sends the plain targets instead. After the take a
`content_idle` drifts the head home for 2.5 s; then the program stops writing until the next call (`--idle` streams the
Perlin idle all the time instead).

Control file: `{"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0, "head": {neck_pitch, head_pitch, head_yaw, head_roll}}`
(absolute model rad) written atomically at 50 Hz during a response, only while the file still holds the program's own
last command or a plain zero-command walk (keys within mode/vx/vy/vtheta/head/for_s). Anything else (the app's walk,
quack, jaw or sit, Shawn's own command) wins at once: the take stops where it is and the log says `yield`. walk_wired's
own `quack` counter is not used (it would move the head on its own, `QUACK_HEAD`).

Quack: `QuackBank` renders each recording in walk_wired's sounds folder at 4 pitches x 3 lengths once
(`pet/express/voice.py`, into `/tmp/namecall_calls`) and plays the variant nearest the take's call event through
`duck_sound.Voice` (`aplay -q` on the ALSA default device, the -3 dB softvol ceiling of D-012). The event time is the
measured gaze arrival plus the take's offset plus the card's `motion_lag_s` 0.14 s, so it lands with the real head. The
jaw does not open (walk_wired's quack opens it; a later version can send `"jaw"` with the call once the first test is
clean).

Safety on the robot (section 2 of `namecall.py`'s docstring): no servo bus, no IMU, the robot I/O lock is probed and
never taken (refuses when nobody holds it, i.e. no brain); refuses while `duck_selfcheck.py` runs (it owns the sound
card then); refuses unless the brain's newest tick log (`~/duck-logs/duck_wired_log_*.jsonl`, younger than 1.5 s) shows
walk mode at zero command or stand mode; from stand mode it writes the zero-command walk (stand61) and waits for the log
to show walk; it stops itself when the brain leaves walk (guard trip, stop command) or the log goes stale; Ctrl-C
writes one last zero-command walk with the head at the default. Head moves only run under stand61/walk61, never under
the open-loop stand (the 2026-10-20 tip).

## 5. Robot test plan (Shawn runs every command)

### 5.1 Install (Mac)

```
~/code/robotics/microduck-sim/guide/firmware/mac/namecall-20261029/install_namecall.sh
```

Copies `namecall.py`, the tests and `pet/express` to `a7z:~/rt/...` (rsync --checksum, no robot motion) and prints:
`namecall imports ok`, the policy default head pose, `sndi2s0 card: cardN`, the number of calls in `sounds/`, and
`arecord/aplay present`. If it prints `NO sndi2s0 card`, the I2S0 overlay is not loaded (CURRENT-STATE
`a7z_audio_capture`); stop here.

### 5.2 Start order

1. Robot standing on the floor as for a walk, on the bench supply or the pack, with room around the head.
2. Brain from the app (`~/duck-run.sh app<suffix>`, monitor mode), then the usual way up: `{"mode": "stand"}`, then
   `{"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0}` (stand61 balancing). The program also accepts starting from stand
   mode and writes that walk command itself.
3. In a second terminal on the A7Z (`ssh a7z`), the first test:

```
cd ~/rt/microduck-sim/guide/firmware/mac
~/.venvs/duck-policy/bin/python namecall.py --mute --once 3
```

### 5.3 Test A: head only, quack muted (`--mute --once 3`)

Clap or call once from the duck's left front, about 1 m away, between its calls (the program ignores sounds for 2.5 s
after a response). Expected, in order: the terminal prints `call: {... "az_deg": +40 ...}` with `take` named within
0.1 s; the head turns toward the sound in the style of that take (quick_snap: a small counter-move then a snap with
a little overshoot and a tilt; curious_turn: slower, tilt grows after arrival; double_take: a half look, back, then the
full turn; groggy: late and slow; glance: a short partial look), the trunk stays level (the sim says under 1 deg),
the head drifts home over the next 2.5 s. Then from the right front, then from behind on one side (the head goes to
its cap on that side, the log says `"behind": true`). After three responses the program prints `done` and exits with
the head at the default pose; the brain keeps standing.

Stop at any time with Ctrl-C in that terminal (one last zero-command walk, head home). The brain is stopped the usual
way (`{"mode": "monitor"}` or the app); the program notices and exits.

What to check in Test A before Test B:

- The azimuth sign: a sound from the left gives a positive `az_deg` and the head turns left. If it turns the wrong
  way, run with `--swap-ears` (and tell me: the ear wires are crossed against D-025, and CURRENT-STATE
  `a7z_audio_capture` gets the correction).
- Front/back: a call from behind should give |az| > 90 and `behind: true`; if it reads a front direction instead,
  check `front_back_margin` in the log (near 0 means the back mic did not help: is ch2 live? `arecord -c 4` and tap it).
- False triggers: the heartbeat line every 10 s shows `floor_db`; if the program fires on the room or on the servos
  (`call` lines with nobody calling), raise `--threshold-db 16` or `--rise-db 9`.
- Head motion looks jerky or the trunk sways visibly: try `--smooth` (plain targets through the brain's 0.2 EMA,
  less anticipation and overshoot; sim tilt max 0.80 deg).

### 5.4 Test B: with sound (`--once 5`, no `--mute`)

Same calls. Expected: each response ends with one duck call from the mouth speaker as the head arrives (pitch and
length vary per response; a glance is usually silent). Watch the terminal for `quack` lines and, right after each,
whether the next `heartbeat` `floor_db` jumped by more than about 10 dB or `call` lines appear with nobody calling:
that is the shared-I2S0 shift the self-check warned about (the capture format changing under a 16-bit playback). If
so, say so; the fix is on my side (render the bank in S32_LE and play it to the hw device the way the self-check
does), not a knob.

Direction accuracy on the robot: stand at known places (ahead, 45 deg, 90 deg, behind-left) and note `az_deg` per
call; the expectation from the report is about 10 deg. Five calls per place are enough; I read them from the log.

### 5.5 Run on (optional)

`namecall.py` without `--once` runs until Ctrl-C; `--idle` adds the living-stillness drift between calls (50 Hz writes
all the time). Not for the first session.

### 5.6 What the log records

`~/duck-logs/namecall_<start>.jsonl`, one JSON line each: `start` (brain mode, lock state, options, bank size, default
head), `call` (onset time, energy and floor dB, rise, azimuth in the head and resting frames, per-pair lags and peaks,
front/back margin, take, its parameters and call events, target yaw, `behind`), `quack` (file, pitch, stretch, muted),
`skip` (a call while a take ran or the brain was not ready), `yield` (another writer took the control file),
`heartbeat` every 10 s (floor, blocks, capture gaps, CPU share, responses, writes, brain mode), `stop` / `done`. The
brain's own tick log carries the head commands it received (`cmd.head`) and the policy's `head_cmd`.

## 6. Proposed changes outside this delivery (not made; other owners)

- `walk_brain.py` (owner: brain): a `head_raw` want key that sets `head_cmd` directly, as `pet/express/README.md`
  section "Duck integration plan" item 2 proposes; it removes the pre-inverse and its HEAD_RANGE saturation near the
  edge of the yaw range. Diff as in that README.
- `walk_wired.py` (owner: brain): a `"quack_file": path` key next to `"quack"` so the brain's own `Voice` plays a
  chosen variant and opens the jaw with it; then `namecall.py` would not need its own `Voice`. Until then the jaw
  stays shut on these quacks.
- `duck_sound.py`: no change needed; `QuackBank` queues a chosen file on its worker (`voice.q.put`).
- CURRENT-STATE `a7z_audio_capture`: after Test A, add which ear is ch0 as observed (D-025 says left = L/R to GND =
  ch0; the test confirms or corrects it).

## 7. Files

- `microduck-sim/guide/firmware/mac/namecall.py`: the program (A7Z and Mac).
- `microduck-sim/guide/firmware/mac/test_namecall_detector.py`, `test_namecall_direction.py`, `test_namecall_chain.py`:
  29 tests; `pet/.venv/bin/python -m pytest microduck-sim/guide/firmware/mac/test_namecall_*.py -q` (the direction
  test writes `results/direction_synthetic.json` when run with `-s`).
- `namecall-20261029/namecall_sim.py`: the chain against the duck sim; `install_namecall.sh`: deploy; `kws_bench.py`:
  the keyword-spotter cost; `results/`: `sim_real.json`, `sim_stress.json`, `sim_smooth.json`, `direction_synthetic.json`,
  `kws_bench.json`, `detector_cost.json` and the batch logs.
- 2 m components (section 10): `test_namecall_call.py` (12 tests), `namecall-20261029/replay_calls.py` (replay a
  recording through the real chain and score it), `results/replay_221619.json`, `replay_201411.json`, `replay_sweep.json`,
  `call_cost.json`.
- Name mode (section 9): `test_namecall_kws.py` (10 tests), `namecall-20261029/keywords_mochi.txt` (the spotter's
  keywords), `mochi_set.py` (the `say` clip set), `kws_mochi_heard.py` (what the model writes for each clip),
  `kws_mochi_eval.py` (keyword grid and the whole-chain evaluation), `kws_a7z_cost.py` (A7Z replay cost per core);
  `results/kws_mochi_heard.txt`, `kws_mochi_grid.json`, `kws_mochi.json`.
- Reused unchanged: `pet/express` (takes, springs, habituation, voice rendering, duck adapter, `duck_sim.simulate` and
  `call_metrics`), `duck_sound.Voice`, the brain's control file and tick log.

## 8. Not verified

- Nothing on the robot or the A7Z: capture through `arecord -t raw` on the A7Z (the self-check records to a file),
  the ear channel order, the real room's echo and head shadow, servo noise under the mics, the quack's effect on the
  capture stream, the A7Z CPU share (estimated 5-22 % of one core), and the timing of 50 Hz control-file writes
  against the brain's reads (the pre-inverse assumes the brain reads every target once; a missed or doubled read moves
  the head by at most one tick of the wanted motion).
- The look-up pitch is a constant; elevation is not estimated.
- The sim's calls are synthetic voices and claps in a free field at 20 dB SNR with a hum floor.

## 9. Name mode: respond only to "Mochi" (2026-10-29)

The duck is called Mochi (Shawn, 2026-10-29). `namecall.py --name mochi` answers only when a keyword spotter hears the
name; `--any-voice` (the default, sections 1-5) is unchanged. Result: the gate works, the model's hearing does not
yet. On synthetic calls the public model catches "Mochi" about 30 % of the time at 20 dB and 19 % at 10 dB, and wakes
about 20 times per hour of other speech. The next step is to fine-tune the spotter on recordings of Shawn saying the
name (9.6).

### 9.1 How it works

- The two ear channels are averaged and decimated 48 -> 16 kHz (`Decimate3`, 97-tap FIR, over 50 dB rejection of
  what would alias). sherpa-onnx 2.0.0 `KeywordSpotter` with the public zipformer
  `gigaspeech-3.3M-2024-01-01` int8 model, one thread, runs on every 20 ms block.
- The voice-band onset detector keeps running with a 0.25 s refractory; its onsets are only candidates. When the
  spotter fires, the program picks the onset nearest 0.75 s before the spot (from 0.25 to 1.6 s back) and takes the
  direction from the 4-channel ring buffer (3 s) at that onset. With no onset in that window it places the window at
  the spot minus 0.75 s. A clap 0.7 s before the name does not steer the head (tested).
- While its own quack plays and for the deaf time after, the spotter is fed silence; during a take it is not fed
  and starts a fresh stream afterwards. Responses keep the 2.5 s refractory.
- Model: `~/rt/models/kws/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01/` on the Mac and the A7Z (same
  sha256), or `$NAMECALL_KWS_MODEL`; `pip install sherpa-onnx==2.0.0` in `~/.venvs/duck-policy` (done on the A7Z).
  `install_namecall.sh` prints a `name mode:` line with the sherpa-onnx version and the model path.

### 9.2 The keywords and where they came from

The model spells words in English BPE pieces, and it does not know "Mochi". Run as a recogniser on the clips
(`kws_mochi_heard.py`, `results/kws_mochi_heard.txt`), it writes macOS voices' "Mochi" mostly as MARCHY, then MALCHY,
MALCHI, MACHI, MORGY, MARGIE, MONKEY and MULTIPLE; Chinese voices come out as MOTION. The first keywords file, the
plain spelling `▁MO CH I`, caught about 5 %. `keywords_mochi.txt` lists the plain spelling plus the eight spellings
the model actually produces (MONKEY, MULTIPLE and MOTION left out: they are real words). A grid over spelling sets,
boost 1/2/3 and threshold 0.05/0.1/0.2 (`kws_mochi_eval.py grid`, `results/kws_mochi_grid.json`) picked boost 2,
threshold 0.05: among the six best recall settings it had the fewest false wakes (21 per hour on the tuning half).
Adding MOTION raised recall from 21 % to 22 % and doubled false wakes to 55 per hour.

### 9.3 Test set

- `mochi_set.py`: macOS `say` clips. Positives: 18 English and 10 Chinese voices saying "Mochi", "Mochi!",
  "Mochi?", "Hey Mochi", "Come here, Mochi", "Mochi, look at me", "嘿，Mochi" and others (232 clips), split into tuning
  and held-out voices; Chinese spellings 莫奇 / 摩奇 (30 clips). Negatives: 415 clips of near words (年糕, motion,
  Mickey, much, 我去, 没事, moshi moshi, mojito ...), 28.3 minutes of continuous English and Chinese speech, the duck's
  own calls (48 raw plus the QuackBank pitch/stretch variants), and claps.
- Each clip is rendered on the head's microphone geometry from a random direction and mixed into either synthetic
  4-channel noise (pink plus hum, detector floor -35 dB) or the robot's own noise from Shawn's recording
  `calls_201411.wav` (fans, servos; 180 s), at 20 and 10 dB SNR measured in the 300-4000 Hz voice band. The whole
  `NameCall` chain runs on each scene (`kws_mochi_eval.py final`, `results/kws_mochi.json`).
- Shawn's robot recording `calls_201411.wav` contains no speech (its loud events are touches on the head): the
  spotter fired 0 times on it, `--any-voice` fired 10 times.

### 9.4 Numbers (`results/kws_mochi.json`)

- Detection, synthetic noise: 20 dB 70/232 = 30.2 % (tuning voices 28.4 %, held-out 31.9 %; English voices 37.7 %,
  Chinese voices 12.9 %); 10 dB 18.5 % (held-out 21.6 %). Robot noise: 20 dB 30.6 %, 10 dB 19.8 %. Spelled 莫奇 /
  摩奇: 0 of 30 at either level.
- By voice at 20 dB: 0 % for Fred, Kathy and eight of the ten Chinese voices, up to 78 % for Grandma, Reed and
  Shelley (English US). By phrase: bare "Mochi" 20 %, "Hey Mochi" 56 %, "Come here, Mochi" 67 %.
- False wakes on continuous speech: 19.1 per hour at 20 dB, 25.5 per hour at 10 dB, 23.3 per hour on the robot bed
  at 10 dB. Near words that woke it at 20 dB: 16 of 415 (Mickey, Moji, monkey, more cheese, moshi moshi, my cheese,
  模式, 没事).
- The duck's own calls: 0 wakes of 96 at 30, 20 and 10 dB and on the robot bed (and 0 in the unit test at 30 dB).
  Claps: 0 of 24.
- Direction at the word: 20 dB mean error 2.6 deg (p90 5.1, one error over 20 deg); robot bed 20 dB 2.3 deg (p90
  6.2); robot bed 10 dB 8.6 deg (p90 12.8, two over 20 deg). The onset came from the detector in 223 of 230 detected
  calls. A 1.0 s look-back (the median spot delay after the clip's first word) made every condition worse (robot bed
  10 dB mean 15.3 deg, five over 20 deg), so 0.75 s stays.
- Latency, end of "Mochi" to the decision (audio time): p10 0.32 s, median 0.44 s, p90 0.60 s, max 0.74 s. The
  spot comes a median 1.02 s after the clip's first word. Add the take's head motion (section 1) on top.

### 9.5 A7Z cost (`--wav` replay of `calls_201411.wav`, `--no-head --mute`, `kws_a7z_cost.py`)

Each replay was pinned to one core with `taskset` at `nice 19` while the brain (walk_wired) ran: brain ticks stayed at
47-49 per second with p99 27-33 ms before, during and after. Share of one core, cool clock:

- Cortex-A55 (cpu2, 1.78 GHz): `--any-voice` 2.5 %; `--name mochi` 25.2 %, block p99 61 ms, max 69 ms. At the
  416 MHz throttle clock this scales to 1.09 cores: not real time.
- Cortex-A76 (cpu6, 2.0 GHz): `--any-voice` 0.8 %; `--name mochi` 9.2 %, block p99 29 ms, max 69 ms; throttled
  estimate 0.44 of a core.
- SoC temperature peaked at 58 deg C (trip 60). The brain is not pinned (seen on cpu7 and cpu2), so name mode runs
  under `taskset -c 6`. Raw results: `a7z:~/duck-logs/kws_cost_first.json` (A55) and `kws_cost_first_a76.json`;
  the A7Z went offline before the final rerun and its copy to `results/kws_a7z_cost.json`.

### 9.6 Rejected alternatives and next step

- The sherpa-onnx zh-en 3M phone model: 10 of 88 clean clips, 3 of 88 at 20 dB. Worse.
- SenseVoice (offline ASR, already in `pet/voice/models`): writes "Mochi" as Moji, Mochi, Marchi or Margie, at
  about six times the spotter's CPU on the Mac, and it needs a segmenter in front. Not built.
- Next: fine-tune the gigaspeech spotter on the keyword (the icefall `kws` recipe; its RESULTS.md reports recall on
  common commands rising from 86 % to 98.7 % at 0.6 false alarms per hour after fine-tuning). Data: Shawn and others
  saying "Mochi" to the robot through its own microphones (`record_calls.sh`), plus the negatives above.

### 9.7 Robot test (Shawn runs it; brain started as in 5.2)

Listen only first (no head, no sound, no control-file writes), call "Mochi" and other words from about 1 m:

```
cd ~/rt/microduck-sim/guide/firmware/mac
taskset -c 6 ~/.venvs/duck-policy/bin/python namecall.py --name mochi --no-head --mute --no-sound
```

Each spotted name prints `call: {... "keyword": "MOCHI", "az_deg": ...}`; the 10 s heartbeat shows `kw_hits`. Then
the head test, as Test A in 5.3 but with the name:

```
taskset -c 6 ~/.venvs/duck-policy/bin/python namecall.py --name mochi --mute --once 3
```

Expect several tries per response at today's recall; "Hey Mochi" and "Come here, Mochi" were caught most often.
Sensitivity is set per line in `keywords_mochi.txt` (`:2.0` boost, `#0.05` threshold); `--kws-score` and
`--kws-threshold` apply only to lines without their own values.

### 9.8 Not verified

- No human "Mochi" has been recorded yet: every positive is a macOS `say` voice in a free field. Real voices, the
  room's echo and head shadow are untested.
- The two ear microphones did not hear through their wall holes in Shawn's 2026-10-29 cover tests
  (`docs/PET_ROBOT_LOG.md`), which the spotter's ear downmix and the direction both depend on.
- The A7Z numbers come from the first cost runs; the final keywords and the 0.75 s look-back were not rerun there
  (the cost does not depend on either), and nothing ran live on `hw:CARD=sndi2s0`. Throttled shares are clock-scaled
  estimates.

## 10. Calls at 2 m: the bins detector, the call localiser, and what the head really hears (2026-10-29 evening)

Replay of the two robot recordings (`recordings/`, git-ignored) through the real chain with `replay_calls.py`;
records in `results/replay_221619.json`, `replay_201411.json`, `replay_sweep.json`, `call_cost.json`; tests in
`test_namecall_call.py` (12, all 52 namecall tests pass). Nothing ran on the robot.

### 10.1 Result against the acceptance (8 calls at 2 m, `calls_221619.wav`)

Acceptance was 8 of 8 detected, 6 within 30 deg, the side right on all 6 side calls, front/back right on 5 of 6, at
most 2 false triggers per minute. Reached with the defaults: 6 of 8 detected; of the detected real calls (+135, 180,
-135, -90, -45; the trigger in the +90 window is the loudspeaker 1 s before the call) 1 within 30 deg (+135 -> +138),
side right on 2 of 4 side calls (+135, -135; -90 -> +138 and -45 -> +10 wrong), front/back right on 4 of 4; the
missed calls are 0 and +45 (and +90). False triggers 3.1 per minute on the quiet stretches of this recording (7 in
134 s, all of them the loudspeaker speech in the corridor) and 0.8 per minute on the earlier recording without the
loudspeaker (`calls_201411.wav`: 2 in 144 s, 2 of its 9 head touches). The acceptance is not met; the causes are
measured in 10.4, not guessed.

### 10.2 What changed in `namecall.py`

- `--detector bins` (default; `energy` is the earlier OnsetDetector): `CallDetector` counts, per 20 ms block, the
  300-4000 Hz bins of the three-microphone mix that stand `--snr-db` over a noise spectrum tracked per bin (EMA, time
  constant `--floor-tau` 3 s, frozen while a block is loud, followed again after 1.5 s of loudness so a fan or a door
  does not deafen it). An onset is `--min-bins` such bins after a quiet block; it is confirmed when
  `--confirm-blocks` of the next three blocks hold half that many and when the harmonicity of the first 60-80 ms in
  300-1500 Hz (largest normalised autocorrelation peak in the 80-400 Hz pitch range) reaches `--voicing`. Defaults
  `--snr-db 9 --min-bins 8 --confirm-blocks 3 --voicing 0.4`. A call 3 dB over the floor in band power lifts its
  three or four "Mo" harmonics 10-20 dB over their bins, which is how it is seen at all.
- `--localiser call` (default; `short` is the earlier 64 ms GCC-PHAT): `CallLocaliser` waits `--call-window` 0.8 s
  after the onset, takes an STFT (1024/256) of the 2 s before the onset for the noise spectrum per microphone and bin
  and of the call window, keeps the time-frequency bins that stand `--loc-snr-db` 3 dB over the noise on all three
  microphones (`--loc-weight soft` scales each by how far over, 0 at 3 dB to 1 at 18 dB), sums the PHAT cross-spectra
  of the three pairs over them and steers the sum over a 1 deg azimuth grid at the elevations in `--elev` (prior 35
  deg: a standing owner's mouth about 1.4 m above the head at 2 m; several values search). Band `--loc-band`
  1500-8000 Hz (10.4). Reports azimuth, elevation, the front/back margin against the mirrored half-plane, the bin
  count and the per-pair lags. The ring buffer grew to 3.2 s; the decision comes 0.82 s after the onset (the head then
  starts its take), the keyword mode places the same window at the word's onset.
- `render_scene(..., el_rad)` renders synthetic scenes at an elevation; the chain tests now render at 35 deg; the
  name-mode tests keep `--detector energy --localiser short` (their mechanics are unchanged).

### 10.3 Detector trade-off (`results/replay_sweep.json`, false triggers per minute of quiet stretch)

- snr 6 dB, 8 bins, 2 confirming blocks, no voicing: 5 of 8 calls; 18.4 per minute with the loudspeaker, 7.1 without.
- snr 6, 12 bins, 2 blocks, no voicing: 7 of 8; 13.9 and 5.4 (the most calls any setting found; one trigger every
  few seconds between them, and the refractory after a false trigger eats calls).
- snr 6, 12 bins, 2 blocks, voicing 0.4: 5 of 8; 8.5 and 1.7.
- snr 9, 8 bins, 3 blocks, voicing 0.4 (the default): 6 of 8; 3.1 and 0.8; 2 of 9 head touches.
- snr 9, 8 bins, 3 blocks, voicing 0.5: 5 of 8; 2.2 and 0.4.
- snr 9, 12 bins, 3 blocks, voicing 0.5: 1 of 8; 0.9 and 0.0.

The voicing check removes the footsteps and touches (the harmonicity of the real calls at the onset is 0.61-0.86,
of the 41 triggers without it 33 are under 0.6 and 21 under 0.4; on the no-loudspeaker recording it removes 15 of
17). What remains at 3 per minute is the corridor loudspeaker: voiced Chinese speech, as loud at the microphones as
Shawn at 2 m. An any-voice detector cannot separate it; that is the keyword spotter's job (section 9), and the
next 2 m recording should be made with the loudspeaker off.

### 10.4 Why the direction is wrong: the head hears the low band through its cavity

Per-pair masked GCC-PHAT lags on the hand-marked call windows (samples at 48 kHz, positive = first microphone
later; the prediction is the free-field lag at 35 deg elevation):

- 300-1200 Hz (the voiced "Mo", 170-600 bins per call, PHAT peaks 0.65-0.92, the strongest cue in the recording):
  left-right 0.0, -4.0, -3.2, +0.5, -0.5, +0.8, +2.5, +1.0 for the calls at 0, +45, +90, +135, 180, -135, -90, -45
  deg (predicted 0, -6.2, -8.8, -6.2, 0, +6.2, +8.8, +6.2); left-back -3.8, -8.8, -6.8, -4.8, -3.5, -4.2, -3.2, -3.5
  (predicted -9.2, -10.5, -5.7, +2.5, +9.2, +10.5, +5.7, -2.5); right-back -3.8, -5.8, -3.2, -4.5, -4.0, -4.5, -7.2,
  -5.0 (predicted -9.2, -4.3, +3.2, +8.7, +9.2, +4.3, -3.2, -8.7). The ear pair keeps the sign on 5 of 6 side calls
  at a third of the predicted size; the back microphone hears every call 3-9 samples after both ears, including
  the calls from behind, where it should lead by 9. In the same band the back microphone is 1.5-4.2 dB louder than
  the ears in every direction, and in 4-8 kHz the ears are 1-4.5 dB louder than it in every direction, 180 deg
  included. The quiet-stretch noise shows the same pattern (coherent under 700 Hz with the same few-sample delays).
  A sound that enters the head through an opening at the front (the beak and the speaker pocket in the mouth floor
  are the large openings; the ear holes are 1.6 mm) and fills the cap cavity reaches the ears first and the back
  seat about 60 mm later, whoever is calling and from wherever: that is what these lags say. Under about 1.5 kHz
  the cavity path dominates the 1.6 mm hole path, so the low band carries almost no direction.
- 1.5-8 kHz (the "chi" burst, 0.1-0.15 s): the ear pair is spatially aliased above 2.2 kHz (77 mm spacing), the
  back pairs above 1.8 kHz, and the burst at 2 m is mostly reverberant: PHAT peaks 0.1-0.3 with mirror lobes of the
  same height (for example +90: left-right -9.0 and +11.8, both 0.18). Masking the bins by coherence (direct-path
  dominance) leaves 10-90 bins per call and does not settle the peaks. The free-field model is right where it can
  be checked (ear spacing: a snap at the right ear leads the left by 10.2-10.9 samples against 10.8 predicted), but
  the back microphone's timing is off even for a near-field snap (snaps 15 cm off the right ear: right-back -2.4 to
  -3.4 against +6.3 predicted), which is the same cavity path.
- Synthetic calls rendered on the free-field geometry at the real level into the real noise localise with 0 deg
  error because they have neither the cavity path nor the room; they test the arithmetic, not the head.

Consequence: software cannot recover a cue the microphones do not receive. The call localiser's defaults are the
physically defensible ones (high band, elevation prior) and reach 1 of 5 within 30 deg on the real calls; the low
band (`--loc-band 300,2200`) gives the side on 4 of 4 side calls among the five detected at the permissive setting
but folds everything to the front and a third of the angle. The hardware check that settles it: with the beak and
the mouth-floor pocket covered (a hand or tape), snap 15 cm off each ear; if the 300-1200 Hz left-right lag of a
side snap grows from about 3 to about 9-11 samples and the back microphone starts to lead for a snap behind, the
cavity path is confirmed and the fix is sealing the cap cavity from the mouth (foam between the mouth floor and the
head cavity, or the microphones' own sealed chambers behind their holes). The 1 m, loudspeaker-off recording still
helps the detector numbers but not the direction, unless the cavity is sealed first.

### 10.5 Cost (`results/call_cost.json`, MacBook M1 Pro, one core)

Detector 0.064 ms per 20 ms block (0.3 % of a core; estimated 1.3 % of a Cortex-A76 at 2 GHz, 6 % at the 416 MHz
throttle). Localiser 24 ms once per detected call on a 3.1 s buffer (estimated 95 ms on the A76, 460 ms throttled;
it runs after the 0.8 s window and before the take, never during one). Whole chain on the 150 s recording: 0.3 % of
a core (0.0031 cpu share), 1.2 % / 6 % on the A7Z; inside the quarter-core budget beside the brain.

### 10.6 Next robot test (Shawn runs it; nothing here has run on the A7Z)

1. From the Mac: `microduck-sim/guide/firmware/mac/namecall-20261029/install_namecall.sh` (copies namecall.py, the
   tests and pet/express; no robot motion).
2. Listen only, loudspeaker off, 2 m, eight directions as before, with the duck untouched:
   `ssh a7z '~/rt/microduck-sim/guide/firmware/mac/namecall-20261029/listen_only.sh 600'` (that is
   `namecall.py --no-head --mute --no-sound --no-gate --log ~/duck-logs/namecall_listen_<HHMMSS>.jsonl` with the new
   defaults). Each call prints `call: {... "az_deg", "el_deg", "bins", "margin" ...}` 0.8 s after its onset; the
   heartbeat shows `floor_db`. Record the same session with `record_calls.sh 120` in a second terminal only if a
   replay is wanted (two readers cannot share the card: run it instead of, not beside, the listener).
3. Head turn, quack muted, brain in walk at zero command (NAMECALL.md 5.2):
   `cd ~/rt/microduck-sim/guide/firmware/mac && ~/.venvs/duck-policy/bin/python namecall.py --mute --once 3`.
   The head turns 0.8 s after the call; `--localiser short --detector energy` restores the earlier behaviour.
