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

- **Speech to text.** `can` / `build`, cloud service.
- **Sentence to rule or to task graph.** `can` / `build`. Frontier model turns an instruction into either an operant rule (section 3) or a task graph over learned skills (section 7).
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

## 8. Purchases and open decisions

- VL53L5CX ToF for stair edges: wanted, not bought.
- No lidar, no smell sensor (Shawn 2026-10-26).
- Ear mics: in hand, not soldered (CURRENT-STATE `parts_a7z_extensions`).
- Privacy: faces and voices are biometric data (Illinois BIPA and similar); embeddings only, on device, non-owner samples deleted after N days.

## 9. Sources

Four surveys on 2026-10-26 (get-up policy; home navigation; person recognition; olfaction) with quoted URLs are in the session transcript; the Radxa NPU numbers are from docs.radxa.com/en/cubie/a7z/app-dev/npu-dev; Pollen's design notes from pollen-robotics/microduck `docs/design/robotd-design.md`. Anything marked inferred is ours.
