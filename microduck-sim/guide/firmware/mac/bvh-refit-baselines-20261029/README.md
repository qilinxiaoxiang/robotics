# BVH refit across the as-built sim baselines (2026-10-29)

Simulation only: nothing here ran on the robot or the A7Z, nothing was trained, and no default was changed. The loader
diff at the end is a proposal.

## Answer

**Get-up 50/50 holds with the refit, and approach 21/21 is not affected.** The approach runs and every walking,
standing, kick, groundpick, namecall and joint-failure baseline give the same result rows bit for bit. Their only
floor contacts are the feet, and the refit leaves both feet's collision boxes covering their geometry. The refit
changes results only where the head or trunk lies on the floor: the get-up runs, one sit-to-stand run and the
seeing pick. It changes two of the get-up study's claims. The "2 side starts went down again after first standing"
disappear: both re-falls came from the head sinking through the floor during the rise. The longest joint saturation
falls from 0.50 s (left hip pitch, one of those two re-falls) to 0.38 s (right knee). The stand61-recover success
count, the 5.09 rad largest action and the 2.2-2.5 s median rise times stay as recorded.

Without the refit the beak falls through the floor in 37 of the 50 get-up runs, up to 40.8 mm deep with no contact.
The trunk falls through in 16 runs, up to 7.9 mm. The refit removes every such sample. The study's variant cases move
by more:

- **IMU 4 deg**: 50/50 without the refit, 46/50 with it.
- **walk_wired 3.0 rad guard kept**: 33/50 without, 26/50 with.
- **velstand v8**: 44/50 both ways, with different runs failing.

The robot does not run with the 3.0 rad guard during a rise, so the guard case strengthens the 2026-10-26 decision
to step the guard aside rather than questioning it.

**Recommendation:** refit inside `evaluate_delay.load`. The change is decision-neutral for everything that walks or
stands. It is required for anything that touches the floor with the head or trunk: get-up, falls, groundpick contact
and seeing pick. Today those baselines rest on a floor the head can sink 40 mm into.

On the approach record: "21/21" is the 2026-10-24 first version (`bf8f73f`). The current suite is the 11-case
`approach_sim.py` suite, which gave 11/11 without drift and 7/11 with the robot drift both ways. Every drift miss is a
safe "not arrived" stop.

## Which collision boxes the refit moves (`bvh_probe.py`, `results/probe.json`)

`evaluate_delay.load` always rewrites body inertias after compile, because `remove_old_battery_kg` 0.09 is applied
on every as-built config. So every as-built model carries stale boxes. The only colliding bodies are `trunk_base`,
`hip_l`/`hip_l_2`, `leg`/`leg_2`, `jaw_soft` (the whole head and beak) and the two `ankle_*` feet.

`outside_mm` is how far each body's colliding geometry reaches outside its stale box: the depth at which a contact
can go missing. On every manifest:

- `jaw_soft`: 32-37 mm, with the long axis swapped (half sizes 37/49/67 mm become 67-69/48-50/37 mm).
- `leg`/`leg_2`: 32 mm.
- `hip_l`/`hip_l_2`: 10 mm.
- `trunk_base`: 18.5 mm (asbuilt), 36.4 (saddle), 38.6 (plugged), 35.1 (plugged with COM -2.25 mm).
- `ankle_right`: box grows 0.1 mm, already covered (0 mm). `ankle_left`: unchanged.

## Method

- **Harnesses run unchanged.** Each one runs through `bvh_run.py`, which imports `bvh_hook.py` before the harness.
- **The refit follows the proposed diff.** The hook wraps `evaluate_delay.load` and applies
  `brain_sim_check.refit_body_bvh` (copied verbatim) right after the original load when `BVH_REFIT=1`.
- **Floor contacts are counted per body every step** from `d.contact`. Contacts between two bodies are counted too.
- **Missed contacts are sampled.** Every 20 ms the hook records any body whose colliding geometry is more than 1 mm
  below the floor with no floor contact.
- **The hook refit matches the built-in flag.** `brain_sim_check.py --bvh-refit` on teleop groundpick_from_stand61
  seed 0 gives the same row as the hook (`logs/xcheck_gp_flag.out` on the Mac mini).
- **Seeds and conditions match.** Both runs of a pair use the same seeds. Real-condition flags come from
  `robot_state_check.py --print-sim-args` (`--volt 7.0 --drop 0.04`, `CURRENT-STATE.json`).
- **Batches ran on the Mac mini.** The code is a snapshot at `~/sims/bvh-refit-20261029/rt` (`snapshot.sh`; md5 of
  the harnesses equal to this checkout), run with `~/.venvs/microduck-dyn`. The MacBook ran only the probe.

```
cd ~/sims/bvh-refit-20261029/rt/microduck-sim/guide/firmware/mac/bvh-refit-baselines-20261029   # Mac mini
BVH_WORKERS=5 nice -n 10 ~/.venvs/microduck-dyn/bin/python run_baselines.py suite teleop getup approach namecall failure
BVH_WORKERS=5 nice -n 10 ~/.venvs/microduck-dyn/bin/python run_baselines.py getup_imu4 getup_guard3 getup_velstand
nice -n 10 ~/.venvs/microduck-dyn/bin/python trace_pair.py side 7          # also side 1, push 0; guard/imu traces below
python3 compare.py > results/compare.txt                                    # results/summary.json
```

Every row in `results/<group>.jsonl` carries its exact harness command, the result row and the hook's contact
counts. `compare.txt` lists every pair that differs.

## Per case (without refit -> with refit)

### sim_suite: identical (10/10 pairs)

- **Source:** `results/suite.jsonl`.
- **Command:** `brain_sim_check.py --model asbuilt --walk-s 10 --models runtime-overlay/models --volt 7.0 --drop 0.04
  [case flags]`.
- **Cases:** real nominal, vx0.25, vx0.2, com+5 and imu_pitch4; stress volt6.3, drop8_imu35 at seeds 0 and 1,
  floor_mu 0.3 and 0.7.
- **Result:** no moved body ever touches the floor. Falls 1 = 1, the median peak tilt is 9.4 deg both ways, and
  dist_x and yaw are equal.

### Teleop (kick, sit-stand, groundpick; plugged manifest, seeds 0-2): 23 of 24 pairs identical

- **Source:** `results/teleop.jsonl`, `teleop_sim_batch.py`'s eight cases.
- **The one change, sit_stand_from_stand61 seed 2:** peak tilt goes from 41.6 to 39.5 deg and stable-after from 2.84
  to 2.46 s.
- **Mechanism:** on the stand-up the robot pitches forward and the beak meets the floor at 11.65 s. Without the refit,
  the head is 5.1 mm under the floor with no contact for 9 samples and then gets a late contact 15 mm deep. With the
  refit it has 172 steps of beak contact, at most 8.3 mm deep, instead of 76.
- **Unchanged:** no falls either way. Groundpick (closed-beak bow, mouth minimum z 22.4 mm) and all kicks are
  identical.

### Get-up stand61-recover (CURRENT-STATE `getup`): 50/50 -> 50/50

- **Source:** `results/getup.jsonl`; saddle manifest, five starts x seeds 0-9.
- **Command:** `getup_sim.py --start S --getup recover --seed N --hard-max-action 99`.

Per start (median / maximum up time, largest action):

- face_down: 10/10 -> 10/10, 2.46 / 2.82 -> 2.48 / 2.88 s, 3.70 -> 3.78 rad
- face_up: 10/10 -> 10/10, 2.18 / 2.50 -> 2.20 / 2.60 s, 3.35 -> 3.55 rad
- side: 10/10 -> 10/10, 2.30 / 5.54 -> 2.30 / 2.56 s, 3.99 -> 3.38 rad; went down again after first standing 2 -> 0
- sitting: 10/10 -> 10/10, 0.28 / 2.94 -> 0.28 / 3.26 s
- push: 10/10 -> 10/10, 2.38 / 4.08 -> 2.26 / 3.80 s, 5.09 both

Longest single-joint saturation over the 50 runs: 0.50 s, left hip pitch (side 7) -> 0.38 s, right knee (sitting 1).

Contacts: without the refit the beak is more than 1 mm under the floor with no contact in 37 runs (1286 samples,
deepest 40.8 mm) and the trunk in 16 runs (61 samples, 7.9 mm). With the refit there are none. Beak floor-contact
steps rise from 43871 to 51557. New head-to-leg self contacts appear (`jaw_soft|leg_2` 227 steps), which the stale
head box had hidden.

Why the changed runs changed (traces in `results/traces/`):

- **side 7 (up 5.54 -> 2.38 s):** the runs are identical until the rise starts at 3.30 s. Without the refit the head
  then drops 7.7 mm and 18.1 mm under the floor with no contact (3.5-3.6 s), so the head is no lever in the push-up.
  The robot stands at 4.80 s, tips at once (gravity z -0.89 -> -0.51) and needs a second LIMP-POSE-RISE. With the
  refit the head stays on the floor (0 to -0.6 mm, touching) through 3.4-3.7 s and the robot stays up from 4.80 s.
  The study's worst saturation (0.50 s) was this run's second rise.
- **side 1 (went down again -> stays up):** at the rise start (3.1 s) the head contact is already missing without the
  refit, and the head is 4.8 mm under the floor at 3.3 s. The robot stands at 4.50 s and falls over at 4.8-4.9 s.
  With the refit it stands at 4.52 s and stays.
- **push 0 (up 3.64 -> 2.20 s):** after the push the head lands. Without the refit it sinks 31-34 mm into the floor
  and the robot keeps rolling over it (gravity z goes positive). The gyro never quiets, so LIMP runs to its 1.5 s cap
  (2.24 -> 3.74 s). With the refit the head stops on the floor and LIMP ends after 0.66 s.
- **The other 38 changed runs** are face_down, face_up, side and push runs whose head sinks at the first touchdown.
  They differ by tens of milliseconds in up time.

### Get-up variants of the study (`results/getup_imu4|guard3|velstand.jsonl`)

**IMU 4 deg (`--imu-pitch 4`): 50/50 -> 46/50** (face_up 10 -> 8, side 10 -> 9, push 10 -> 9). The study recorded
48/50 for this case. In all four flips the robot stands up, then falls again while standing on its feet, after the
head has left the floor. A re-fall that lands near the end of the 12 s window fails the "standing for the last 2 s"
test. Re-falls after standing happen without the refit as well: 9 runs without, 12 with. The divergence starts at the
first touchdown (face_up 0: head 15.3 mm under the floor at 0.1 s without the refit, 0.7 mm with). This case is
marginal both ways, and its success count is noise from the window edge.

**walk_wired 3.0 rad guard kept: 33/50 -> 26/50** (face_down 0 -> 0, face_up 8 -> 7, side 9 -> 5, sitting 9 -> 9,
push 7 -> 5). The without-refit counts equal the study's. Mechanism (`traces/guard3_side_2.json`): with the head
holding the floor the rise pivots on it, gravity z reaches -0.69 by 3.7 s against -0.48, and the action climbs to
2.89 rad. The guard trips at 3.76 s. Without the refit the head is 22 mm under the floor and the rise asks for at most
2.83. With real head contact, more rises exceed 3.0 rad, so the guard must keep stepping aside during `brain.getup`.

**velstand v8 recover: 44/50 -> 44/50.** Different runs fail: side 6 -> 7 and push 10 -> 9. All failures are GAVE_UP
with the robot on its back, as the study describes. The "not a walk61 replacement" conclusion stands.

### Approach (`results/approach.jsonl`): identical (22/22 pairs)

- **Without drift** (`--drift 0 --trim 0`): 11/11 both ways.
- **Robot drift** (0.015 N m forward, trim -1.1079): 7/11 both ways. The misses stop safely with "not arrived after 4
  approaches".
- **Contacts:** no moved body touches the floor.

### Namecall (`results/namecall.jsonl`, `namecall_<refit>_<seed>.json`): identical (12/12 seeds)

- 72 calls, 71 detected, 0 false alarms, 0 falls and maximum tilt 0.99 deg both ways. This equals `sim_real.json`.

### Joint-failure study (`results/failure.jsonl`): identical (130/130 pairs)

- Command: `walk_fault.py`, no fault plus six joints frozen or weak, seeds 0-9, saddle manifest, guards on.
- 0 falls both ways and the median peak tilt is 6.7 deg both ways.

### Seeing pick (not rerun)

`seepick-gap-20261029/` already measured this case: stale 0/54, refit 12/54.

### Open-loop stand COM study (`stand-saddle-20261026/olsearch.py`, not rerun)

- Its pool workers start through `multiprocessing` spawn, and those workers would not carry the hook.
- In standing only the feet touch the floor, and their boxes do not change.
- The teleop `*_from_STAND` cases, which start in that open-loop stand, are identical.

## Proposed loader change (text only, NOT applied)

```
--- microduck-sim/hardware-design-20260912/whole-robot-20260912/delay-repair-20260912/evaluate_delay.py
@@ def load(config):
     if mass_parts:add_signed_inertias(m,mass_parts)
+    refit_body_bvh(m)   # add_signed_inertias turns bodies' inertial frames after compile; MuJoCo keeps each body's
+                        # bvh_aabb in the compile-time frame, so the head/trunk/leg boxes miss up to 40 mm of geometry
+                        # and the midphase drops their contacts (guide/firmware/mac/bvh-refit-baselines-20261029)
     d=mujoco.MjData(m)
```

Move `refit_body_bvh` from `brain_sim_check.py` into `evaluate_delay.py` (it needs only `mujoco` and `numpy`). Keep
`brain_sim_check.py --bvh-refit` as an accepted no-op flag so the seepick-gap and rehearsal command lines still run;
a second refit changes nothing. Placing it inside `load` covers every caller at once: `brain_sim_check.py`,
`getup_sim.py`, `pickup_sim.py` and `approach_sim.py`, `pet/express/duck_sim.py` and `namecall_sim.py`,
`walk_fault.py`, `target_ground.py`, `stance_switch.py`, `duck_kin_export.py` and `run_experiments.py`. A refit right
after `load` at each call site would leave any missed caller stale.

Re-verify these facts and claims if it is applied:

- **CURRENT-STATE `getup`:** 50/50 and "median time up 2.2-2.5 s" hold (2.20-2.48 s). Replace "longest joint
  saturation 0.50 s (left hip pitch)" with 0.38 s (right knee). Rerun `getup-20261026/run_batch.py` and update
  `summary.json`.
- **`getup-20261026/README.md`:** the "2 seeds went down again" line becomes 0. Update the IMU 4 deg case (48/50
  there, 46/50 with refit), the guard 3.0 table (side 5/10, push 5/10, face_up 7/10) and velstand recover (same 44,
  side 7/push 9).
- **`teleop-sim-check.json`:** regenerate it; sit_stand_from_stand61 seed 2 changes.
- **Seeing-pick rehearsal grid:** the next grid would get the refit by default, as `seepick-gap-20261029` already
  assumes.
- **Unchanged and need no re-verification:** walking (sim_suite, `walk_heading_hold` and `walk_speed_vx025` sim
  sources), approach, namecall, the joint-failure study, kicks, groundpick and the open-loop stand pose.

## Seen along the way, not caused by the refit (identical with and without)

These baselines from current code differ from their older records:

- **sim_suite com+5** falls forward at 0.84 s in the open-loop STAND phase, before stand61 starts.
  `microduck_rl/cmu/simcheck/reference-walk61.jsonl` records no fall.
- **Approach with robot drift** passes 7/11. `approach-sim-20261024-v4` recorded 9/11.
- **teleop sit_stand_from_stand61 seed 2** reaches a 41.6 deg peak tilt, against 10.4 in `teleop-sim-check.json`.

These were not investigated here.
