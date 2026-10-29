# Pet robot: problems, scenarios, solutions, status

Register for the companion-pet direction on the MicroDuck body and for the Introduction to Robot Learning course project that is its first milestone. One entry per capability; status words are fixed so the list can be checked off:

- `can`: feasible with what exists or with a part we have / can buy cheaply. `cannot`: not reachable in this project; recorded so nobody promises it.
- `done`: on the robot or verified in sim with a readback. `build`: software or integration, no new model. `train`: needs a learned model trained or fine-tuned by us. `frontier`: open research; only as a stretch.

Principle (Shawn 2026-10-26): a dumb pet is fine, a rigid pet is not. It must visibly remember things and visibly try to understand, even when it gets it wrong. No speech. Current robot facts come only from `microduck-sim/CURRENT-STATE.json`.

## 0. Goal and the overall solution

Goal: a pet that knows its owner, remembers what it was told and what happened, acts on its own, finds its way at home, and can fetch a named object. The course project is the fetch story (section 7); the pet is where it goes afterwards.

One architecture serves every scenario below. Three layers, split by time scale and by where they run:

- **Reflex layer, milliseconds, on the A7Z.** Balance and walking policies, fall recovery, obstacle and stair-edge stops, immediate reactions to a sound, a face or a touch (turn, stop). Learned policies and arithmetic only; never a language model.
- **Intention layer, 10-30 s, small model on the Mac mini.** Reads time, owner location, recent events, drive and mood values, today's plan, the owner's rules with their weights (as text), the last minutes of behaviour; composes the next intention from motor primitives with a duration and abort conditions. A validator admits only known primitives, in-range parameters and a timeout. Drives and mood stay arithmetic so behaviour has continuity; the model gives it variety. Offline fallback: drives pick directly.
- **Reflection layer, nightly, frontier model (Claude via the subscription or API).** Reads the day's event log; writes the diary, association rules with evidence counts, personality nudges, new skill scripts (compositions of primitives) and tomorrow's plan. Rule strength is then maintained by a Rescorla-Wagner update during the day, not by the model.

How the architecture shows up: in every scenario the pet reacts at once (reflex), does something that fits its state and history rather than a fixed script (intention), and behaves differently the next day because of what happened (reflection). That is the expectation the principle sets; a scenario that cannot show all three is marked.

Persisted state, all plain files, survive reboot: `rules.json` (associations with weights), diary (text + embeddings), personality parameters, skill library, people memory (embeddings and familiarity), home map.

## 1. Body competence (reflex layer)

Scenario: it walks around the home, falls on a rug, gets up; bends to the floor without toppling; closes its beak on an object.

- **Walk and turn.** `can` / `done`. Pollen `walk61` at 0.25 m/s, arcs both ways, stable (CURRENT-STATE `walking_stability`, `walking_policy`). Turning in place never tried on the robot.
- **Get up after a fall.** `can` / `build`. Pollen's `alpha_stand` is our `stand61.onnx` (same SHA256); `velstand` v8 (walk + protected fall + get-up) is on HF `pollen-robotics/microduck-policies`. Blocker is our tilt gate in `walk_brain.py` `Brain.tick()`. Fix: robotd's sequence (predicted fall -> limp -> quiet -> 1 s ramp home -> stand policy at zero command -> give up after 5 s at low gain). In progress 2026-10-26 (`guide/firmware/mac/getup-20261026/`).
- **Bend and keep balance, beak open.** `can` / `train`. Pollen's `groundpick61` bows with the beak closed (shown on the robot, 37 deg tilt). A beak-open bend is a new learned motion (D-027, PROJECT-CONTEXT step 3).
- **Grasp with the beak.** `can` / `train`. Beak-lab jaw policy passes 12/12 table-edge and 4/4 ground-ball cases in sim; the jaw gripped a finger on the robot; no object picked up yet (PROJECT-CONTEXT step 4). Jaw limit stays in software.
- **Obstacle and stair-edge stop.** `can` / `build` once a VL53L5CX ToF (0.5 g, $20, I2C) is fitted 45 deg down from the chest; monocular depth on the NPU is unmeasured and never a safety loop.

## 2. Knowing people

Scenario: owner on the sofa, a stranger walks in; the pet tells them apart, goes to the owner, and after a week treats a frequent visitor as familiar.

- **Face.** `can` / `build`. InsightFace `buffalo_sc` (SCRFD-500MF + MobileFaceNet, 16 MB ONNX). Needs >= 10 px inter-pupil distance (about 1.5-2 m on our 720p / 120 deg camera, inferred) and degrades past 15-30 deg upward pitch, so: recognise when the person is near or the head has tracked up; enrol the owner from five angles including from below (Astro's practice). Licence: non-commercial. In progress 2026-10-26 (`pet/identity/`).
- **Voice.** `can` / `build`. CAM++ or ECAPA-TDNN ONNX via sherpa-onnx; 2-3 s of speech; enrol one phrase; verify only while standing still (servo noise). Waits on the ear mics being soldered for the robot; Mac first.
- **Familiarity memory.** `can` / `build`. Store embeddings by day; nightly HDBSCAN; a new person only after >= 3 similar samples (Immich's rule); familiarity = encounters x recency; owner pinned. In progress (`pet/identity/memory.py`).
- **Silhouette and clothing when the face is out of frame.** `can` / `train`. OSNet embeddings with a gallery reset daily and relabelled by confident face/voice matches. Gait at knee height: `frontier`, no evidence.
- **Fusion face + voice (+ body).** `can` / `build`. Log-odds accumulation with time decay; no product does more than face.
- **Where did the sound come from.** `can` / `build`. GCC-PHAT with interpolation on the two ear mics (about 10-15 deg at 6 cm), rear mic resolves front/back. Waits on the mics.
- **Look up at a person.** `can` / `build`. YOLOv8n person detection on the A7Z NPU (Radxa: 12.6 ms inference + 25.9 ms post, ACUITY toolchain) -> head pitch/yaw target through `approach.py`'s head control. RL gaze control: `frontier`, marginal gain.
- **Recognise the owner by smell.** `cannot`. Dropped (Shawn 2026-10-26).

## 3. Memory and learning from experience

Scenario: keys jingle, the owner leaves; by day four the pet is at the door when the keys jingle. The owner says "stay out of the bedroom"; it goes less, not never. A rainy afternoon spent alone shows up in how it greets the owner.

- **Event log.** `can` / `build`. A few dozen event types from perception and from its own actions; JSON lines; the vocabulary bounds what can be learned, grow it with a general sound classifier (YAMNet class) later.
- **Associations after a few exposures.** `can` / `build`. Nightly the frontier model proposes "A then B" rules from the compressed log; Rescorla-Wagner weights (start 0.3, rise on confirmation, fall on omission, decay when unused) do the learning. Pavlovian rules bump drives in anticipation; operant rules enter the intention prompt as text with their weight.
- **Owner instructions as rules.** `can` / `build`. Transcribed sentence -> operant rule via the model; speech-to-text itself is a cloud service (ElevenLabs / OpenAI / Volcengine), accepted.
- **Diary and retrieval.** `can` / `build`. Nightly summary sentences with embeddings; the intention layer retrieves similar past situations.
- **Personality and growth.** `can` / `build`. Drive rates and thresholds per robot; nudged nightly within bounds.
- **Anticipation beyond rules (time-of-day patterns).** `can` / `build`. Nightly plan from the diary ("17:30 wait at the door"), executed by the intention layer.
- **Learning a new motor skill from a few demonstrations.** `train`, course-relevant; see section 7.

## 4. Initiative and liveliness

Scenario: nothing happens for ten minutes; the pet wanders, calls once, naps by the owner's feet, startles at a door slam, goes to look.

- **Drives and mood.** `can` / `build`. Bored, miss-owner, tired, curious; valence/arousal set by events, decaying.
- **Intention every 10-30 s by a small model.** `can` / `build`. Composes primitives; validator; recent-behaviour list and temperature against repetition; per-robot personality text. Cost: ~3000 calls/day at the cheap tier, or free with a local 7B on the Mac mini (1-2 s latency, acceptable).
- **Interrupts.** `can` / `build`. Reflex reaction first, then the event goes into the next intention round.
- **Skill library.** `can` / `build`. Primitives are enumerated and safety-checked; new skills are scripts over primitives written by the reflection layer and validated (Code-as-Policies / Voyager pattern); the robot never takes raw motor commands from a model.

## 5. Finding its way at home (monocular, no lidar)

Scenario: "find the owner": it knows it is in the kitchen, the owner was last seen in the living room, it walks there without hitting the chair legs or falling down the step.

- **Map.** `can` / `build`. Photograph the home with a phone, including a pass at 15-30 cm height; COLMAP / hloc reconstruction on the Mac mini. Mature.
- **Localise.** `can` / `build`, success rate to be measured. Relocalisation, not SLAM: one frame per second to the Mac mini, hloc retrieval + SuperPoint/LightGlue + PnP; dead-reckoning from leg kinematics + IMU between fixes. Known failure cases: blank walls, lights off, moved furniture; fallback to room classification.
- **Room classification.** `can` / `train`. Places365 / ResNet18 fine-tuned on photos of the home, few-frame vote; fits the NPU (inferred).
- **"Where was the owner".** `can` / `build`. Table of person seen + room + time.
- **Path planning.** `can` / `build`. Free-floor grid + A* once the pose is known.
- **Local obstacles.** `can` / `train` or measure: monocular depth (Depth Anything V2 small) on the NPU, unbenchmarked; ToF for the step.
- **Continuous monocular SLAM while walking.** `frontier`, do not build on it (ANYmal study: mono-inertial tracking failure, rolling shutter 30x worse). **3D Gaussian Splatting localisation.** `frontier`; the splat itself is optional eye candy on the same reconstruction.

## 6. Understanding the owner's words (cloud)

Scenario: "go fetch the orange block"; "don't go in there"; "good duck".

- **Speech to text.** `built` off the robot (`pet/voice/`, 2026-10-29). Default is local, not cloud: SenseVoice small (int8, sherpa-onnx, CPU) reads the two ear channels of the A7Z 4-channel stream after `listen.py` cuts one utterance per sentence (namecall's onset detector, trailing silence, 1-8 s). On 20 synthetic `say` clips (10 en, 10 zh): 8.3 % error (WER en 10.7 %, CER zh 6.2 %), 0.15 s median per clip on the MacBook's CPU; Whisper base (same runtime) was 41.7 % because it writes traditional characters and hallucinates on short Mandarin. ElevenLabs Scribe v2 is the second backend behind the same call; its key is expired (401), so it is off until renewed. Nothing has heard the robot's microphones yet; `--robot` streams them over ssh to the Mac mini.
- **Sentence to rule or to task graph.** `built` off the robot: `intent.py` asks Claude Haiku 5.5 (through `claude -p`, Sonnet by flag) for one JSON of kind `task` (steps over the body card's primitives and `pet/mind` skills, validated by `pet/mind`'s validator), `rule` (an owner instruction parsed by `pet/learn`'s instruct parser, weight 0.6) or `ignore`, with a `reaction` (praised / said_no) for the learn layer. 20/20 on the test sentences in both languages (fetch, come, sit, stop, bedroom rule, night-quack rule, praise, chatter); median 4.9 s per sentence, $0.0004 each at list price. The result lands in `pet/state/inbox/` (contract in `pet/state/README.md`); the runner's pickup of task files is not written yet. Not a frontier model and not a task graph over learned skills: a step list over today's primitives.
- **Open-ended dialogue, theory of mind.** `cannot` by design (no speech).

## 7. Course project: fetch a named object (Introduction to Robot Learning)

Story: the owner says "bring me the orange block". The cloud model decomposes it into the four learned-skill steps; the duck finds the object in view, walks to it, bends with the beak open while balancing, grasps, stands, walks back.

What Pollen ships and where it stops (checked 2026-10-26, details in `PET_ROBOT_LOG.md`): `alpha_ground_pick` is a blind episodic bow, beak 86 deg down, mouth tip 2.7 cm up, horizontal final approach; Rémi's own note calls it "beautiful but rarely grasps". It is aim-and-hope: the operator lines the duck up by hand and the move either lands on the object or not. Rémi's `ground-grasp` branch (2026-10-10, unmerged, no exported policy) adds an opening jaw, a scripted mouth schedule and a randomised object, but the policy is still blind and relies on the object sitting within +-1 cm of a fixed spot. Our target is a robust grasp: the beak is aimed at a perceived grasp point (`cmu_aim_pick_env_cfg.py`, error-gated aiming) fed by the detector and the approach, so the object can be anywhere in view. Robust grasp, get-up integrated with walking, language-to-skill chaining and the overnight learning are ours.

Status today (PROJECT-CONTEXT `final_goal`): step 1 find: orange HSV detector locks 57/57 frames; camera changed since, calibration to redo (`train` if we move to a learned detector). Step 2 walk to it: autonomous approach runs exist (`approach.py`, 2026-10-24), not teleoperation. Step 3 bend: Pollen's closed-beak bow shown; open-beak bend `train`. Step 4 grasp: sim only, `train` + sim2real. Get-up: `build`, in progress.

Learning content to present: RL policies for bend-and-grasp (sim, domain randomisation, sim2real on 15 XL330s), a learned detector or VLM grounding for the object, the get-up policy integration, the language planner over a skill library, and the nightly association learning as the "learning that continues after deployment". Baselines, perturbations, failure artifacts and quantitative readback are required by AGENTS.md; a polished demo is not acceptance. If the full story slips, fetch alone is the deliverable.

## 10. Long-term: one end-to-end model, and what the pet is allowed to be

- **End-to-end pet model.** `frontier`, long-term. One network with sound, vision, joint angles, IMU and touch in and motor/vocal commands out, trained continually from its own life. The modular stack above is the way to get there, not a detour: it produces the labelled event stream, the skill library and the behaviour logs that such a model would be distilled from, and it keeps a safe fallback while the model is immature. Known obstacles to record honestly: catastrophic forgetting under continual training (the nightly-consolidation design exists because of it), no reward signal richer than owner reactions, and sim2real for the body parts. First concrete step when the time comes: distil the intention layer into a small policy on the logged (state, intention) pairs and compare behaviour diversity against the model-driven version.
- **Private data, the owner's responsibility.** The pet is a single-owner device; its learning data is private. If the owner trains it badly, the owner lives with the result. Hard limits stay only where the body can be damaged (servo ranges, overload, stair edge, hold-until-told) and where the law reaches (biometric data of visitors). Nothing else is filtered.
- **Unconditionally supportive, never judgmental.** Design principle (Shawn 2026-10-26): the pet does not lecture, disapprove or moralise; whatever the owner does, it stays on their side, like a pet. Where it lives: the personality text given to the intention and reflection models says so explicitly; the behaviour primitives contain no scolding or refusal behaviours; the reflection prompt is told to record the day, not to evaluate the owner. A cloud model that editorialises in its outputs is a reason to switch that layer to a local model, not to tolerate it. Since the pet does not speak, the surface where moralising could leak is small: behaviour choice and vocal tone.

## 11. One mind, several bodies (Shawn 2026-10-26: "灵魂可以穿越到不同的身体")

- **Mind/body seam.** `can` / `build`. The intention, reflection, identity, memory and rule layers never touch the body; they read a **body card**: sensors, actuators (model, torque, range), available primitives and each primitive's preconditions. One card for the duck, one for the OMX-F arm. A frontier model given "camera, no ears, 6 joints, cannot move" chooses waving and turning towards the owner, not walking. This is the cheap and real part of the transfer.
- **Self-inspection on boot (body schema).** `can` / `build`. Scan the Dynamixel bus (ids, models, limits), enumerate camera/mics, then small safe motor babbling per joint while logging IMU and image change, and write the body card from it. Lipson et al. 2006 (Science, "Resilient machines through continuous self-modeling") is the reference; same program on the duck and on the OMX is the demo.
- **Walking with a failed non-critical joint (neck servo gone or frozen).** `can` / `train`. Add joint failure (frozen / weak / missing, head and neck first) to the training randomisation so the policy sees the stuck joint in its observation; alternatives: RMA-style online adaptation (Kumar et al. 2021) and the repertoire + Bayesian-optimisation recovery of Cully et al. 2015 (Nature, "Robots that can adapt like animals", minutes to a working gait after damage). Leg joints are a different robot, not a damaged one.
- **One learned motor policy across morphologies (duck policy driving an arm).** `frontier`. Shared Modular Policies (Huang 2020), MetaMorph (Gupta 2022) work across hundreds of simulated bodies; no plug-and-play real-robot result. Do not build on it.

## 12. Aliveness and personality on any body (Shawn 2026-10-26, after a talk with a character-robot startup)

Aliveness comes mostly from how the body moves, not from what it chooses. Sources: the twelve principles of animation (Thomas and Johnston, *The Illusion of Life*, 1981); Heider and Simmel 1944 (moving triangles read as agents when they self-start, react contingently and change course toward goals); Pixar's *Luxo Jr.* (a faceless lamp reads as alive through gaze and timing); Sung et al., "My Roomba is Rambo" (UbiComp 2007: owners name and gender their vacuum robots); Disney Research's bipedal character (Grandia et al., RSS 2024) and BDX droids: RL policies that track animator-authored motion with style.

- **Expressive motion layer.** `can` / `build`. Every primitive takes style parameters (speed profile, amplitude, reaction latency, head lead, settle) driven by mood and traits: anticipation (a small counter-move before acting), gaze leads the body by 150-300 ms, follow-through and settle after a stop, slow-in/slow-out, reaction latency of a few hundred ms rather than instant. Same primitive, different mood, visibly different motion.
- **Attention system.** `can` / `build`. There is always something it is looking at (owner, sound source, moving thing, idle scan); looking before doing makes the thought visible.
- **Living stillness.** `can` / `build`. Idle breathing and micro-motions (head drift, weight shift) so it is never frozen; drowsy when tired.
- **Fallibility.** `can` / `build`. Hesitation, double-takes, a startle and recovery; matches "dumb but not rigid".
- **Personality = stable mapping from state to style and choice.** Drive rates and thresholds (section 4) plus style gains per robot; consistent across days, nudged slowly by the reflection layer.
- **Body-agnostic form.** A vacuum robot's "head" is its heading: gaze = turning toward, anticipation = a short back-up before going, mood = speed profile, sound and light. The body card (section 11) lists which expressive channels exist.
- **Responding to its name, technique.** Today the duck's head follows its target through a first-order low-pass (`walk_brain.py` `HEAD_ALPHA = 0.2`): it eases in, never anticipates or overshoots, and is identical every time; each quack picks one of a few real recordings at random (`duck_sound.py`). Plan: second-order (spring-damper) gaze dynamics with mood-set stiffness and damping, a library of takes (quick snap, slow curious turn, double take, groggy) chosen by context with per-sample parameter jitter (latency, overshoot, head tilt, settle, quack timing and pitch), no immediate repeats, habituation when called repeatedly, Perlin-noise idle. Gestures run under the stand/walk policy, which already takes head commands; an open-loop stand tipped on a quack head move on 2026-10-20. Status 2026-10-29: built for the robot as `microduck-sim/guide/firmware/mac/namecall.py` (three-mic onset + GCC-PHAT direction + `pet/express` take + quack, 0 falls in 72 simulated calls, plan in `namecall-20261029/NAMECALL.md`); awaiting Shawn's first robot test, head only and muted first.
- **Cross-body abstraction.** The mind emits expressive intents with affect, e.g. `acknowledge(target=owner, warmth, energy)`, never joint motions. Each body card declares semantic channels and how they map: ATTEND (duck head / arm wrist camera / vacuum heading), ORIENT (body yaw / base joint / chassis), POSTURE (head height, shoulder lift), GESTURE (nod, bounce, tilt, gripper clack), VOCALISE (speaker, else none). Affect maps to motion qualities in the Laban Effort terms used in expressive-robot research (time sudden-sustained, weight light-strong, space direct-indirect, flow free-bound); "cute" = light, sudden-but-small, indirect, bouncy springs, head tilt. Generative Expressive Motion (Mahadevan et al., HRI 2024) composes such behaviours with an LLM over a robot's primitives.
- **Learned style.** `train`, course-relevant: style-conditioned imitation of a few animator keyframe clips on the duck (Disney's approach), so a mood changes the gait itself.

## 13. One principle under the drives (Shawn 2026-10-26: "为什么生物表现得像一个生物")

The candidate single principle is homeostasis under uncertainty: an organism keeps its essential variables inside a viable range (Cannon 1932; Ashby 1952), and Friston's free-energy / active-inference account (2010) shows that minimising expected surprise about those variables splits into exactly two terms, pragmatic value (survival drives) and epistemic value (curiosity). Curiosity and survival are one quantity, not two indicators. Either alone degenerates: curiosity alone sits in front of the noisy TV (Burda et al. 2018), survival alone does nothing (our ft1 run, 2026-10-16). Derivable from the principle: foraging, play as cheap model learning, attachment (owner proximity as an essential variable), approach-or-avoid of strangers depending on current stability, habituation, and emotion as the rate of change of the deviation. Not derivable: cuteness (an evolved signal for the observer; section 12 stays separate), personality (the parameters, not the form), morality and language (not ours).

- **Homeostatic drive layer.** `can` / `build`. Replace the hand-written drives with a table of essential variables and comfort ranges (battery, temperature, owner distance, time since touch, unexplained surprise) and one objective: pick the intention that minimises expected deviation plus expected information gain. The intention prompt states ranges and deviations instead of drive scores. References: Keramati and Gutkin 2014 (homeostatic RL), Yoshida et al. 2021 (homeostatic agents that develop foraging/rest/explore rhythms). Experiment: run both drive layers through the same simulated day in `pet/mind` and compare behaviour against animal-likeness criteria (self-started action, contingent reaction, goal-directed course change, habituation).

## 8. Purchases and open decisions

- VL53L5CX ToF for stair edges: wanted, not bought.
- No lidar, no smell sensor (Shawn 2026-10-26).
- Ear mics: in hand, not soldered (CURRENT-STATE `parts_a7z_extensions`).
- Privacy: faces and voices are biometric data (Illinois BIPA and similar); embeddings only, on device, non-owner samples deleted after N days.

## 9. Sources

Four surveys on 2026-10-26 (get-up policy; home navigation; person recognition; olfaction) with quoted URLs are in the session transcript; the Radxa NPU numbers are from docs.radxa.com/en/cubie/a7z/app-dev/npu-dev; Pollen's design notes from pollen-robotics/microduck `docs/design/robotd-design.md`. Anything marked inferred is ours.
