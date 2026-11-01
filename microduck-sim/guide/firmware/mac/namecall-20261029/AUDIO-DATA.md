# Audio data for the Mochi name spotter

Every sound source the spotter can learn from, where it lives and what is in it. Check this list before deciding
what data exists; update it in the same turn as a new recording, download or label.

All duck recordings are A7Z head-microphone captures (ch0 left ear, ch1 right ear, ch2 back mic, ch3 empty;
S32_LE 48 kHz) unless noted. Recordings are git-ignored. On the MacBook they sit in `recordings/raw/` (.raw and
calls_221510.wav) and `recordings/` (10/29 .wav). The Mac mini copy is `~/mochi-train/data/`.
`to_mono16.py` turns each recording into NAME.npy (the ear mix the spotter hears) and NAME@ch0/1/2.npy (each
microphone alone, all three live in every recording). Labels are in `mochi_labels.json`.

## Duck recordings with Shawn calling "Mochi"

- **calls_201411.wav** (10/29 20:14, RoboClub lab, 180 s, before the ear repair): eight calls at 2 m, duck turned
  45 deg by hand between calls, head touches. Calls at 21.75, 34.08, 42.43, 51.07, 59.79, 68.55, 80.31, 88.15 s
  (template match, confirmed by Shawn's ear; `calls_found`). Until 2026-10-30 evening the whole file was wrongly
  used as a negative. `listen_raw.wav` and `listen_voiceband_plus30dB.wav` are 24 kHz copies of it (correlation
  0.965); they are not separate data.
- **calls_221619.wav** (10/29 22:16, RoboClub, 150 s, after the ear repair): eight calls at 2 m with Shawn walking
  round the duck and a corridor loudspeaker playing Chinese courtroom dialogue throughout (`word_starts`).
  `listen2_voiceband_plus30dB.wav` is a processed copy.
- **live_141734.raw** (10/30 14:17, home, 228 s): Shawn's open-ended call session, 56 calls in 110-226 s
  (`call_spans`); 0-110 s unlabelled.
- **live_073135.raw** (10/30 07:31, home table test, 103 s): six calls (`calls_heldout`).
- **live_nc_143806.raw** (10/30 14:38, home, 227 s, namecall running with quacks): about ten calls from behind-left
  in 176-212 s; the rest has no call. `mine_life.py` finds eight sure calls at 183.8-204.1 s.
- **live_nc_145512.raw** (10/30 14:55, home, 185 s, namecall running): calls in 20-60 and 95-125 s; 125-185 s
  Shawn only stood up and walked (the duck answered five times, all false). `mine_life.py` finds ten sure calls at
  97.9-120.7 s.
- **calls_200910.wav** (10/30 20:09-20:21, home, 714 s, 48 kHz 4 ch S32, `record_calls.sh`): the eight-direction
  protocol recording, `eightdir_20261030.json`. Shawn stood 2 m away on the floor; the duck was turned 45 deg clockwise
  between calls: one call each at 529.4, 552.9, 562.6, 573.9, 582.6, 593.1, 602.5, 611.6 s = bearings 0, +45, +90, +135,
  180, -135, -90, -45 (positive = left). 0-520 s is Shawn talking and moving with no call (confirmed): a certified
  negative stretch. Held out from training (the spotter's only certain home test set). Mac mini `data/calls_200910.wav`
  and `mono16v2/calls_200910*.npy`.
- **Life log 10/30 21:00-21:10** (`recordings/life/20261030/2100*-2110*.wav`, 13 segments, namecall running with v2):
  the first live run of the word spotter. `results/events_2100_20261030.json`: 20 voice events, 17 calls and 3 talk by
  Whisper transcript; 9 calls scored >= 0.5, 8 quiet calls 0.00-0.20 (the training material round 3 adds). Mac mini
  `mono16v2/life_20261030_21*.npy`.
- **Clip gate** (`oww/clip_gate.py`, `results/clip_gate_20261030.json`): from round 3 on every positive clip passes
  it (Whisper reads the name in the window, or the recording is a protocol one; the clip is the 0.3-1.0 s envelope burst,
  else the labelled word length). Round 2's live_141734 spans were E3 energy events, 31 of 56 fragments.

## Duck recordings without the name

- **calls_221510.wav** (10/29 22:15, RoboClub, 66 s): no known call (`mine_life.py`: none); unused so far.
- **live_204536.raw, live_204926.raw** (10/29 20:45, 20:49, lab, 180 s each): finger snaps by each ear, ears
  covered and open.
- **live_205910.raw** (10/29 20:59, lab, 87 s): snaps behind the head. **live_221322.raw** (10/29 22:13, 107 s):
  snap test after the ear repair.
- **live_073014.raw** (10/30 07:30, home, 78 s): unlabelled sounds the any-voice mode answered.
- **live_150103.raw** (10/30 15:01, home, 144 s): Shawn's ordinary speech, no name.
- **own_quacks_144713.raw** (10/30 14:47, home, 73 s): all 48 QuackBank calls through the head speaker.
  **own_quacks_144438.raw** (10/30 14:44, 73 s, pulled 10/30 20:00): the first take of the same playback, not yet in
  mono16v2.
- The A7Z holds no other recording (checked 10/30 16:00, 12 .raw files, all here); the morning live_level runs wrote no
  files. The life log stops writing below 2 GB free. Since 10/30 18:45 `a7z_offload.py` (launchd
  `com.xiangzheng.a7z-offload`, hourly on the MacBook) moves every duck-logs file older than 6 h to the Mac: life
  segments to `recordings/life/<day>/`, everything else (brain logs, blackbox, calls_*.wav) to `~/Backups/a7z-duck-logs/`;
  run records and health in `~/Backups/a7z-duck-logs/offload-runs.jsonl` and `offload-status.json`. First run freed the
  card from 1.7 GB to 10 GB free.
- **Life log** `recordings/life/<day>/HHMMSS_mmm.wav` (3-ch int16 16 kHz, `life_log.py`, index `life_index.jsonl` with
  the epoch start of each segment): the duck records round every voice, name and answer from boot. Pull with
  `rsync -a a7z:duck-logs/life/ recordings/life/`, convert with `to_mono16.py --prefix life_<day>_`, label with
  `mine_life.py` (no one marks anything). Times: the A7Z ran on UTC until 10/30 16:08 EDT, so file names before that are
  UTC (195614 = 15:56 EDT); it is on America/New_York since. 10/30 15:56-16:07 EDT (listen-only v2 ensemble, Shawn at
  home): 15 segments, 10 min, `life_labels_1030_evening.json`: no call, 501 s of quiet negatives; the one live hit at
  16:01:47 (segment 200104_327, 43.1 s) has no voiced event and the room's own level (-33 dB), the model's P reaches
  0.75 only at one window phase: a quiet-room false hit, kept as a negative.

## Downloaded and generated sources

- **Google Speech Commands v0.02** (35 words, thousands of speakers): MacBook path given to `--speech-commands`,
  Mac mini `~/mochi-train/data/speech_commands`.
- **ESC-50** (2000 environmental clips, 50 classes): `~/data/esc50`, Mac mini `~/mochi-train/data/esc50`.
- **mochi_set** (`mochi_set.py`, macOS `say`): 262 synthetic "Mochi" in 28 voices, 415 near-miss words, 11 long
  speech clips (28 min, the held-out false-wake test). Synthetic Mochi positives are not used: even with
  same-voice synthetic speech as negatives they woke on 235 of 561 held-out synthetic sentences (2026-10-30).
- **tts_speech** (`tts_speech.py`): 38 clips, 15 min of everyday sentences in the same 28 voices (negatives).
- **mochi_web** (`~/data/mochi_web/`, final 2026-10-30 16:30; Mac mini `~/mochi-train/data/mochi_web2` is this final
  set, `mochi_web` there is the earlier unverified cut with 1925 positives that the W runs trained on): real people
  saying "mochi" in 80 YouTube videos from 65 channels (54 English, 26 Japanese; recipes, tasting), 16 kHz mono,
  `manifest.json` with video, channel, language, time, transcripts and, inside each clip's `check` record, a `confidence` tier (785 high, 653 medium,
  248 low: how many of three recognizer readings agree). `pos/` 1686 tight word cuts (0.45-1.0 s, verified by
  SenseVoice; Whisper reads mochi or a close mishearing in 60 % of them and in 0 of 663 checked negatives),
  `pos_ctx/` 1686 1.5 s cuts with the word in its own background (`word_offset_in_clip`), `neg_adjacent/` 3158 1 s
  windows from the same sentence, `neg/` 1198 1 s speech windows at least 2 s from any mochi or sound-alike, `audio/`
  the 80 source files (2.6 GB); file prefix before `_NNN` is the video id. Limits: cuts keep slivers of neighbouring
  words, もちもち counts as mochi, 329 positives have background music. Scripts in `scripts/`, `run_final.sh` reruns the
  cut and check. This is the 18-763 lecture 21 recipe (many speakers, the word as the only shared cue);
  `train_mochi.py --web` holds out the videos whose id hashes to 0 mod 10.

## Not duck data

`~/Downloads/audio-17923*.wav` (10/18) are 17-720 breathing recordings from a phone; not usable.

## The duck's own motion noise (body turns, head sweeps, walks)

- **Source**: the life log while the duck moved, cut by `oww/life_motion_bg.py` (speech masked: voiced 60 ms frames and
  +-2 s around logged calls). Motion times come from the namecall logs (`recordings/motion_sources/`: turn ->
  turn_done, scan steps) and from brain logs with the walking command per row: the 10/30 t2b walks 16:01-16:05
  (`robot-runs-20261030-t1/t2b/`) and Shawn's in-place turns at vtheta +-0.5, 16:09-16:13
  (`turn-inplace-20261030/robot_walk611030-160205_tail20000.jsonl.gz`). Life segment starts come from
  `life_index.jsonl` (names before 10/30 16:08 EDT are UTC).
- **Amount** (`recordings/bg_motion_life2/`): 360 training windows of 2 s x 3 streams (left, right, mix); held out:
  the 10/31 body turns at 20:21:33 and 20:21:49 (`hold/*.npy`, 16 kHz, 3 mics), used only by `oww/eval_motion.py`.
  Round 4 used the first 167 windows (`recordings/bg_motion_life/`), round 5 all 360.
- **Not yet pulled**: the 10/31 daytime life log and the 17:11 run stay on the A7Z (offline since 10/31 20:45);
  `a7z_offload.py` brings them on its next successful run.
- **Measured** (2026-10-31/11-01): during a body turn the 300-3000 Hz band at the ears is 6-13 dB over standing and
  4-11 dB over a 2 m call; spectral flatness 0.8 (the loudest 10 % of 4 Hz bins carry 31 % of the added power, no
  fixed tones); 10 % of the 20 ms frames carry 70 % of the energy (footstep impacts); coherence between the three
  microphones 0.3-0.5 below 1.5 kHz, under 0.2 above; the same level before and after the glue.
