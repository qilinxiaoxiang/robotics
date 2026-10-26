# pet/express: expressive motion between the mind and the body

Register section 12 (`docs/PET_ROBOT_FEATURES.md`): aliveness comes mostly from how the body moves. This package turns
an expressive intent from the mind ("answer the owner, warmly, with some energy") into timed, varied motion on
whatever body is attached, through five semantic channels that each body card maps to its own joints and devices.
When the duck is called it turns its head and quacks, a little differently each time. The same call on the OMX-F arm
turns the wrist camera and clacks the gripper. On a vacuum robot it turns the chassis and beeps.

Sim and Mac only so far. Nothing here has run on a robot.

## Where it sits

```
mind (pet/mind)  --intent-->  Expressor.submit()          intents.py, takes.py, spring.py, idle.py
                              Expressor.step(now) @ 50 Hz  channels.py (body card "channels" block)
body loop        <--outputs-- {joint/device: value}, events (call / clack / beep)
duck only                     duck.py: walk_brain head-command path; voice.py: pitched, stretched duck calls
```

The mind never emits joint motions. It emits one of five intents with an affect:

```python
from pet.express import Expressor, Affect, Target, acknowledge, attend, greet, startle, content_idle
from pet.express.channels import load_card

ex = Expressor(load_card("pet/express/cards/duck.json"), seed=1)
ex.submit(acknowledge(Target(yaw=0.8, pitch=0.2, label="owner"), warmth=0.8, energy=0.7,
                      affect=Affect(valence=0.6, arousal=0.6)), now)     # mind, whenever it decides
frame = ex.step(now)        # body loop, every 20 ms
frame["outputs"]            # {"head_yaw": ..., "head_pitch": ..., "neck_pitch": ..., "head_roll": ..., "body_heading": ...}
frame["events"]             # [{"kind": "call", "pitch": 1.14, "stretch": 0.93, "gain_db": -1.8, ...}] when due
```

- `acknowledge(target, warmth, energy)`: answer a call (look, a small cute reaction, usually a vocal).
- `attend(target)`: look at a sound or a moving thing; never vocalises.
- `greet(target)`: the owner came back; two calls, a bounce on each.
- `startle(target)`: recoil, snap toward it, settle; sometimes a high squawk.
- `content_idle(seconds)`: drift back to rest; living stillness.

Targets are gaze directions in the body's resting frame (yaw + left, pitch + up, rad). Affect is valence (-1..1) and
arousal (0..1). `intents.effort_for` turns intent and affect into the four Laban Effort factors (time sudden-sustained,
weight light-strong, space direct-indirect, flow free-bound); warm intents come out light and indirect (head tilt),
excited ones sudden and free (stiff, underdamped springs).

The mind owns which intent, the target and the affect (drives and mood already live there). The expressor owns how:
take choice, timing, jitter, habituation. Mapping from the mind's primitives: `turn_head` toward a person becomes
`attend`, a social reply becomes `acknowledge`, `owner_returns` becomes `greet`, a `door_slam` sound becomes `startle`,
`wait` / `stand` becomes `content_idle`.

## Channels and the body-card block (proposal for `pet/state/README.md`)

Five semantic channels, six axes:

- ATTEND: `yaw`, `pitch` (where it looks)
- ORIENT: `yaw` (where the body faces; follows the gaze past `orient_threshold`, starting `head_lead_s` later)
- POSTURE: `height` (-1 slumped .. +1 alert)
- GESTURE: `tilt` (head tilt, rad), `bob` (nod/bounce impulse)
- VOCALISE: events (`call` with pitch, stretch, gain)

Proposed optional key in `body_card.json`, owned by pet/body (it writes the card). Readers ignore it when absent:

```json
"channels": {
  "space": "delta",                 // outputs are deltas from the rest/look pose
  "orient_threshold": 1.2,          // rad of gaze yaw before the body turns too
  "head_lead_s": 0.22,              // gaze leads the body by this
  "motion_lag_s": 0.14,             // the body's lag behind its command; calls are delayed to land with the motion
  "ATTEND":  {"map": [{"axis": "yaw", "to": "head_yaw", "gain": 1.0}, ...]},
  "ORIENT":  {"map": [...]}, "POSTURE": {"map": [...]}, "GESTURE": {"map": [...]},
  "VOCALISE": {"render": "call" | "clack" | "beep" | "none", ...},
  "outputs": {"head_yaw": {"limit": [-1.4, 1.4], "max_rate": 7.0}, ...}
}
```

Each output is the sum of `gain * axis` over the map entries naming it, clipped to `limit` and rate-limited. A `to` must
be an actuator in the card or an entry of a new optional `devices` list (`speaker`, `beeper`, `ring_led`,
`body_heading`). A channel with an empty map is absent on that body. `channels.validate` enforces all of this.

The three cards in `cards/` are copies of `pet/state/examples/duck.json` and `omx_arm.json` with the block added, plus a
hypothetical vacuum robot. `python3 -m pet.express.cards.make_cards` regenerates them from the current examples.

- Duck: ATTEND.yaw -> head_yaw; ATTEND.pitch -> head_pitch 0.75 and neck_pitch -0.25; ORIENT.yaw -> body_heading and
  -1 on head_yaw (the head counter-rotates while the body turns, so the gaze stays on the owner); POSTURE -> neck back
  and head up; GESTURE.tilt -> head_roll, bob -> head_pitch; VOCALISE -> speaker calls. Signs come from the as-built
  sim's head camera: head_yaw + turns left, head_pitch + looks up, neck_pitch + lowers the head. Output limits sit
  inside walk_brain's HEAD_RANGE.
- OMX-F arm: no neck. A gaze turn is split into a fast 35 % glance on the base (ATTEND) and the slower remaining
  65 % (ORIENT, after the head lead). Wrist pitch is the gaze pitch. Wrist roll is the head tilt. A small shoulder
  lift is posture. A gripper close-open is the vocal, with a second clack for a happy (high) call. Wrist pitch only
  moves away from its stop: LOOK is 1.35 deg under the cap in `omx-local/CURRENT-STATE.json` wrist_pitch_max_deg.
  The wrist pitch sign is not verified on the arm.
- Vacuum: the heading is both gaze and body, with the same 35/65 split. There is no pitch. POSTURE is drive speed,
  so the anticipation dip becomes a short back-up. GESTURE tilt is a heading wiggle and bob a forward-back jiggle.
  VOCALISE is a beep at 1400 Hz times the call pitch, plus an LED pulse.

## Motion generation

- **Spring-damper gaze** (`spring.py`): `x'' = wn^2 (r - x) - 2 zeta wn x'`, sub-stepped at 50 Hz, with rate limits.
  Stiffness and damping come from Effort and arousal (`wn_zeta_from_effort`): an eager call gives wn of about 12 and
  zeta of about 0.5 (15 % overshoot); a sleepy one wn of about 4 and zeta of 1 or more (slow, no overshoot). Under
  the old first-order HEAD_ALPHA path the head could never anticipate or overshoot.
- **Takes** (`takes.py`), five ways to answer the same call:
  - `quick_snap`: short latency, a counter-move and a dip (anticipation), a stiff underdamped turn, a little tilt,
    a bounce on the call.
  - `curious_turn`: slower, a head tilt that grows after arrival, the head lifted a bit, a later and higher call.
  - `double_take`: a 45 % glance, back, then a fast full turn.
  - `groggy`: 0.6-0.8 s latency, drooped posture rising, overdamped, falls a little short, a low, long call.
  - `glance` (habituated): a partial look and back, usually silent.

  `startle` is a sixth take, used only for the startle intent.
- **Choice by context**: weights from arousal, warmth, Effort space, novelty and whether attention was elsewhere
  (`selection_weights`). The previous take is excluded, so the same take never runs twice in a row.
- **Per-sample jitter**: every timing and gain is drawn around its nominal value (latency, anticipation size and
  length, spring wn and zeta, tilt size, side and hold, lift, bob, call offset, pitch, length), so two responses
  of the same take are never identical.
- **Habituation**: novelty drops to 0.75 of its value per call and recovers with a 40 s time constant. Energy, bounce
  and call probability scale with it, and the `glance` weight grows as it falls. Called every 2 s, novelty runs
  1.0, 0.76, 0.59, 0.47, 0.39, 0.32, 0.28, 0.25 and the answers shrink toward glances. Five minutes later it answers
  fully again.
- **Head leads body**: ORIENT starts `head_lead_s` (jittered) after ATTEND, softer and overdamped.
- **Idle** (`idle.py`): 1-D Perlin fBm on gaze yaw/pitch, tilt and posture, plus a breathing sine. Arousal scales
  amplitude and speed, and low arousal droops the posture. The idle shrinks to a quarter during a take and ramps
  back afterwards.
- **Call timing and voice**: the call is placed at the measured gaze arrival plus a take-specific offset, then delayed
  by the card's `motion_lag_s` so it lands with the real head, not the command. Pitch is
  `2^((1.5 v + 2.5 (a - 0.5) + take bias + N(0, 0.7)) / 12)`, clipped to 0.80-1.35. Length is set by arousal and
  take. `voice.py` resamples an existing recording for pitch and WSOLA-stretches it for length. The recordings are
  the walk_wired `--sounds` folder or, on the Mac, Pollen's simulator voices, and no file plays twice in a row. No
  new audio assets: rendered calls go to `out/audio/` (git-ignored).

## Duck integration plan (read-only on microduck-sim)

`walk_brain.Brain.tick` takes `want["head"] = {joint: absolute rad}` and turns it into deltas from the policy default,
clipped to HEAD_RANGE (1.10, 1.10, 1.40, 0.31). It smooths them with `head_cmd += 0.2 * (target - head_cmd)` and
feeds `head_cmd` to stand61/walk61 as their head command (obs slots 55..58). The gestures therefore run under the
policy, which keeps the trunk balanced. The 2026-10-20 open-loop tip cannot recur through this path.

1. **No walk_brain change** (what the sim ran): `duck.ema_preinverse` sends `r_k = c_{k-1} + (y_k - c_{k-1}) / 0.2`,
   so the EMA output equals the wanted trajectory `y` exactly while `r` stays inside HEAD_RANGE. The limit is fast
   motion near the edge of the yaw range: a 7 rad/s snap ending near 1.2 rad would need targets past 1.4. There the
   overshoot is shaved for about 3 ticks (largest error 0.23 rad, in `duck_tilt.json` `ema_error_max_rad`).
2. **Small walk_brain change** (proposal for the walk_brain owner): let a want carry the already-smoothed command.

   ```python
   # in Brain.tick, where head_cmd is updated (walk and sitstand branches)
   if want.get("head_raw"):
       self.head_cmd[:] = self.head_target(want)          # pet/express already shaped it
   else:
       self.head_cmd += HEAD_ALPHA * (self.head_target(want) - self.head_cmd)
   ```

   Then send `want_head(y[k])` with `head_raw: True`, and the snaps reach the edge unclipped.
3. Calls: `walk_wired.py` already owns a `duck_sound.Voice`. Render a bank at start (each recording at five pitches
   and three lengths, about 1 MB) and play the nearest variant when an `events` entry with `kind == "call"` is due.
4. ORIENT on the duck is a heading goal for walk_brain's heading controller (walk61, robot-tested turns +-0.3 rad/s)
   and only fires past 1.2 rad of gaze. It was not run here: the name-call sim keeps stand61 and the head range covers
   the callers.

## Evidence (`out/`)

Regenerate everything with `pet/.venv/bin/python -m pet.express.demo --body all --tilt` (about 3 minutes on the
MacBook; the duck sim is one light process, so nothing needed the Mac mini). The stress table needs
`~/.venvs/microduck-dyn/bin/python pet/express/duck_sim.py --tilt --volt 6.6 --drop 0.08 --tag _stress`.

- **Five consecutive name calls on the duck** (`duck_5_calls.mp4`, `duck_5_calls_strip.png`, `duck_calls.json`): as-built
  sim under stand61 with the calls from alternating sides. The takes were curious_turn, double_take, quick_snap,
  double_take, glance, at novelty 1.00, 0.77, 0.61, 0.51, 0.43. Head latency (to 10 % of the move) was 0.64, 0.26,
  0.42, 0.24, 0.10 s, and peak trunk tilt 0.09-0.72 deg. Calls came at pitch x1.20, 1.21, 1.14, 1.21 and length
  x0.95, 0.81, 1.08, 0.93; the fifth call, a glance, stayed silent. `duck_calls_spectrogram.png` shows the rendered
  calls.
- **Tilt table** (`duck_tilt_table.md`, `duck_tilt.png`, `duck_tilt.json`, `duck_tilt_stress.json`): 20 calls per set,
  at 7.0 V / 4 % drops and at 6.6 V / 8 %. There were no falls in 360 calls.
  - Today's path (target step into HEAD_ALPHA 0.2): tilt max 0.63 deg.
  - Takes, highest tilt first: quick_snap 1.29 deg, quick_snap at maximum energy 1.19, greet 1.12, startle 1.10,
    double_take 1.00, curious_turn 0.83, groggy 0.48, glance 0.36.
  - The head joint trails the command by 0.12-0.16 s under the policy; that number is the duck card's
    `motion_lag_s`.
  - So the policy tolerates every take. The expressive moves roughly double today's trunk tilt and stay near 1 deg.
- **Variation** (`{duck,arm,vacuum}_variation.{json,png}`): 300 name calls per body in bursts, mixed affect.
  - Consecutive identical responses: 0/299. Consecutive same take: 0/299.
  - Take counts on the duck: quick_snap 72, curious_turn 85, double_take 66, groggy 67, glance 10.
  - Gaze latency median 0.46 s (p10 0.20, p90 0.86).
  - Median latency by take: double_take 0.20 s, glance 0.30, quick_snap 0.34, curious_turn 0.54, groggy 0.84.
  - Overshoot median 0.024 of the move (p90 0.18). By take: quick_snap 0.08, double_take 0.12, groggy 0.
  - 182 distinct call pitches in 242 calls: pitch p10-p90 0.86-1.25, length 0.82-1.47.
- **Same intent, three bodies** (`same_intent_3_bodies.png`): one intent, one take and one seed give identical
  semantic motion. The outputs differ by body:
  - Duck: the head turns with overshoot and the call lands on arrival.
  - Arm: the base glances 35 % and then turns the rest; the gripper clacks.
  - Vacuum: the heading glances and turns, a back-up comes before the turn, then a beep and an LED pulse.
- **Five calls per body** (`{duck,arm,vacuum}_5_calls_channels.png`) and a top-down vacuum strip (`vacuum_strip.png`).

## Not verified

- No robot motion. The duck numbers are from the as-built MuJoCo model with the saddle manifest. The servo rail
  (7.0 V) and read drops (4 %) come from `microduck-sim/CURRENT-STATE.json`, whose entries were past their
  re-measure age on 2026-10-26 (robot offline). The stress run at 6.6 V and 8 % brackets them.
- Arm: wrist-pitch sign and the executor's lag are unmeasured, and nothing ran on the OMX-F or its twin. The vacuum
  is a card for a robot we do not have.
- The call audio was rendered and its spectrograms checked, but not listened to on the duck's speaker (500 Hz
  high-pass, 560-840 Hz resonance). Pitch factors above about 1.25 may sound thin there.
- Personality: style gains (bounciness, tilt, talkativeness) per pet are a natural next key in
  `pet/state/personality.json`; not added, because pet/learn owns that file.

## Files

- `intents.py`: intents, affect, Laban Effort.
- `spring.py`: spring-damper tracking and step metrics.
- `takes.py`: take library, selection, habituation, call events.
- `idle.py`: Perlin idle.
- `channels.py`: card block validation and mapping.
- `express.py`: Expressor.
- `duck.py`: walk_brain head path and EMA pre-inverse.
- `voice.py`: call rendering.
- `duck_sim.py`: MuJoCo stand61 runs.
- `demo.py`: evidence.
- `cards/`: the three cards and their generator.
- `tests/`: pytest; run `pet/.venv/bin/python -m pytest pet/express/tests -q`.
