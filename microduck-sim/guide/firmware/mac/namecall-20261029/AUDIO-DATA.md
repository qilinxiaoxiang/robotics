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

## Duck recordings without the name

- **calls_221510.wav** (10/29 22:15, RoboClub, 66 s): no known call (`mine_life.py`: none); unused so far.
- **live_204536.raw, live_204926.raw** (10/29 20:45, 20:49, lab, 180 s each): finger snaps by each ear, ears
  covered and open.
- **live_205910.raw** (10/29 20:59, lab, 87 s): snaps behind the head. **live_221322.raw** (10/29 22:13, 107 s):
  snap test after the ear repair.
- **live_073014.raw** (10/30 07:30, home, 78 s): unlabelled sounds the any-voice mode answered.
- **live_150103.raw** (10/30 15:01, home, 144 s): Shawn's ordinary speech, no name.
- **own_quacks_144713.raw** (10/30 14:47, home, 73 s): all 48 QuackBank calls through the head speaker.
- Still on the A7Z only (list them when it is back online): the 10/30 morning live_level and namecall runs
  (06:10-07:22), any later live_*.raw, and from now on the life log `~/duck-logs/life/` (`life_log.py`).

## Downloaded and generated sources

- **Google Speech Commands v0.02** (35 words, thousands of speakers): MacBook path given to `--speech-commands`,
  Mac mini `~/mochi-train/data/speech_commands`.
- **ESC-50** (2000 environmental clips, 50 classes): `~/data/esc50`, Mac mini `~/mochi-train/data/esc50`.
- **mochi_set** (`mochi_set.py`, macOS `say`): 262 synthetic "Mochi" in 28 voices, 415 near-miss words, 11 long
  speech clips (28 min, the held-out false-wake test). Synthetic Mochi positives are not used: even with
  same-voice synthetic speech as negatives they woke on 235 of 561 held-out synthetic sentences (2026-10-30).
- **tts_speech** (`tts_speech.py`): 38 clips, 15 min of everyday sentences in the same 28 voices (negatives).
- **mochi_web** (`~/data/mochi_web/`, being built 2026-10-30): real people saying "mochi" in YouTube videos (recipes,
  tasting, Japanese food), word cuts as positives, the rest of the same sentence and video as negatives, manifest
  with video id and time.

## Not duck data

`~/Downloads/audio-17923*.wav` (10/18) are 17-720 breathing recordings from a phone; not usable.
