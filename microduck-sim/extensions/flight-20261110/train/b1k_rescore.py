"""Stage B1 of ../TRAIN-CONTRACT.json, attempt 2 (prepared 2026-11-20; history note of 14:40): attempt 1 excluded every
round 3 teacher because it reads seven or eight simulator values. Four of them are not hidden on the robot: payload
mass and the loaded trunk centre of mass x y z are constants of the pack state, known from the mass manifest; the gain
is the walk mode's KP_RL 200. Only the three trunk velocity values are unavailable. Question: fed only what the robot
can know, does any teacher save pass B1's line? Beside it, the with-pack specialist fq2_1999 (a plain 61-input
one-frame policy, coordinator's addition) is scored in the same cells. Nothing is trained. Cells, seeds, window,
metrics and pass line are attempt 1's (b1_rescore.py, imported here: its constants and pure functions only).

  $PY train/b1k_rescore.py [phase=1|2] [workers=7] [only=<substring>] [check=only] [seeds=60] [seed0=2000]   (Mac mini only)
  python3 train/b1k_rescore.py select=1        (MacBook; reads files, no simulation; writes out/rescore_b1k/candidates.json)

Two phases, one per launch (owner decision 2026-11-20 14:55: two policy sets, walk61 and stand61 without the pack and a
pack set of its own; a universal model is a later question).
  phase=1 (default)  the reference and fq2_1999 alone, all 20 cells: 24 cells. Its with-pack cells are the result that
                     matters. Writes summary.json with its own verdict, complete without phase 2.
  phase=2            the reference and the four teachers with the "known" and "as_trained" feeds: 164 cells, started
                     separately later; it now only informs a possible later merge. Writes summary_teachers.json.
The reference's four no-pack cells belong to both phases; a phase started after the other keeps their finished files
(same files, same seeds, same deterministic probe), as any restart does.

Candidates (frozen in CANDIDATES below before any scoring; select=1 recomputes the rule and says whether the frozen
list still equals it). Pool: the round 3 teacher saves (first input 68 or 69 wide, out/rescore_b1/inventory.json) whose
eight 10-episode gate files eval/gate_<save>_{pack,none}{,_g400}_{stand,walk}.json exist (seeds 0 to 9, fed as round 3
fed them). Rank: fewest whole-episode falls summed over the four pack cells (pack_g400_stand, pack_g400_walk at gain
400; pack_stand, pack_walk at gain 200), then over the four no-pack cells. Thirteen saves tie at 0 and 0, so the
tie-break is: lower median action jumps per 10 s in pack_walk (gain 200), then in pack_g400_walk, then name; and at
most one save per training run, so the four are four different teachers and not neighbouring saves of one run. At
most 4. t3h_750 must be in the list (RUNLOG.md: 0 of 10 falls with the pack at gain 400); the rule puts it first.
The specialist fq2_1999 is a group of its own, added by instruction, not ranked.

Feeds. A teacher file takes obs [1, 68] or [1, 69]: columns 0:61 are the robot's own inputs, built by the probe's
Brain exactly as for every 61-input policy (b1_rescore.py: gyro 3, gravity 3, joint positions 14, joint speeds 14,
last action 14, command 3, head command 4, body_command 6 zeros). The rest is appended by flight_eval._PrivSession
from flight_eval.priv_now, which this script replaces per episode:
  known        61 payload_kg, 62:65 trunk_com x y z = the nominal values of the cell's manifest (NOMINAL below:
               computed once per manifest by file arithmetic from the model's XML and the manifest, before any
               episode; never read from the simulator), 65:68 lin_vel x y z = 0.0, 68 kp_scale (69-wide files only)
               = KP_RL 200 / 200 = 1.0 in BOTH conditions (the gain400 condition still simulates gain 400; the robot
               believes 200). flight_eval.priv_now is never called: every episode asserts priv_first is None.
  as_trained   flight_eval.priv_now unchanged, as round 3's gates fed it: payload and trunk COM from the compiled
               model, the true trunk velocity every tick, kp_scale = simulated KP_RL / 200 (2.0 under gain400). The
               upper bound.
  plain        fq2_1999 only: a 61-input file, nothing appended (b1_rescore.one, as attempt 1's candidates).
  runtime      the reference "deployed" (walk61 + stand61 of runtime-overlay/models), no-pack cells only.
Every teacher episode counts what was really appended (calls, per column first / min / max) and is refused if it
differs from the feed's definition. For "known" the compiled model's trunk_base COM is read once per episode as a
CHECK of NOMINAL (within 0.05 mm), never as a feed.

Stand policy. Each save's folder holds walk61.onnx and stand61.onnx; the Brain runs the stand slot at zero command and
the walk slot under a walk command. For the four teachers and fq2_1999 both slots are one file (the round 1 probe ran
fq2 that way: train/policy/, sim/policy_legs.py), so their stand policy is the save itself in every cell; the
reference stands on Pollen's stand61. Cells without a payload start with the probe's 0.3 s open-loop stand, cells
with a payload run the policy from the first tick (--stand-s 0), as attempt 1.

Order inside a phase: feed check first (one episode per save and feed on seed 7000, never a verdict seed, in
pack_gain400_walk, where every appended column differs between the feeds; out/rescore_b1k/feed_check.json in phase 1,
feed_check_teachers.json in phase 2; the job stops there on a fault, or with check=only), then the reference, then
the phase's rows (phase 2: every teacher "known" before any "as_trained", so the answer comes first).

Pass line (the contract's, unchanged; b1_rescore.verdict): per row at most 6 window falls of 60 in every cell,
nominal no-pack walking speed at least 0.6 of walk61's in this run, median jumps at most max(1.5 x walk61,
walk61 + 2) in the nominal-condition cells. Beside it, and NOT a pass line of the stage, every row is read per load
group (no pack; 25 %; 50 % + 75 % + full pack), because the owner's fallback in REQUIREMENTS.json FP-R3 is two policy
sets plus detection: fq2_1999 may fail the no-pack cells, where the robot would run walk61 and stand61.

Writes out/rescore_b1k/<save>__<feed>__<cell>.json and the phase's summary file after every cell; heartbeat
logs/b1k_rescore_heartbeat.txt (both phases, each line of a START names its phase), one line per finished cell, last
line DONE or FAILED. A finished cell file of the same
save, file hash and feed is kept on a restart. Other seeds than 2000 to 2059 go to out/rescore_b1k/seeds_<seed0>x<n>/
and never count as the stage's verdict.
"""
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b1_rescore as b1  # noqa: E402  constants and pure functions; never b1.main / b1.hb / b1.inventory (attempt 1's files)

opts = dict(a.split("=", 1) for a in sys.argv[1:])
assert set(opts) <= {"phase", "workers", "only", "check", "seeds", "seed0", "select"}, f"unknown option in {sorted(opts)}"
PHASE = opts.get("phase", "1")
assert PHASE in ("1", "2"), f"phase={PHASE}: 1 (reference + fq2_1999, the default) or 2 (reference + the teachers)"
SUMMARY, FEED_CHECK = ("summary.json", "feed_check.json") if PHASE == "1" else ("summary_teachers.json", "feed_check_teachers.json")
SELECT = opts.get("select", "0") not in ("", "0")
CHECK_ONLY = opts.get("check", "") == "only"
SEEDS, SEED0 = int(opts.get("seeds", 60)), int(opts.get("seed0", 2000))
WORKERS = min(int(opts.get("workers", 7)), 8)
VERDICT_SEEDS = (SEED0, SEEDS) == (b1.VERDICT_SEED0, b1.VERDICT_SEEDS)
BASE = HERE / "out" / "rescore_b1k"
OUT = BASE if VERDICT_SEEDS else BASE / f"seeds_{SEED0}x{SEEDS}"
HB = HERE / "logs" / "b1k_rescore_heartbeat.txt"
RL = (HERE / "../../../microduck_rl").resolve()
MODEL_DIR = RL / "src/mjlab_microduck/robot/microduck"                      # evaluate_delay.MODEL_DIR
ASBUILT_CFG = RL / "cmu/whole/dynamics/asbuilt-20261015/asbuilt.config.json"  # static_gap.MODELS['asbuilt']
AUDIT = RL / "cmu/whole/electrical/existing-model-mass-audit.json"

REF, REF_FEED = b1.REF, "runtime"
FEEDS = ("known", "as_trained")
CHECK_SEED, CHECK_CELL, CHECK_CELL_REF = 7000, "pack_gain400_walk", "none_nominal_walk"
KP_ROBOT = b1.KP_ROBOT
GAIN_SCALE_ROBOT = KP_ROBOT / 200.0  # teacher.py enable_gain: 1.0 = the robot's KP 200; flight_eval.priv_now: KP_RL / 200
TOL_M, TOL_KG = 5e-5, 1e-5
BATTERY_REMOVED_KG = 0.09            # brain_sim_check.run: cfg(0.09, model="asbuilt", ...) -> remove_old_battery_kg

# ---- candidates, frozen 2026-11-20 by select=1 (out/rescore_b1k/candidates.json): save, sha256[:16] of walk61.onnx
# (= stand61.onnx), first-input width, rank key [pack falls, no-pack falls, pack_walk jumps, pack_g400_walk jumps]
CAP, MUST = 4, "t3h_750"
CANDIDATES = (
    ("t3h_750", "229053c23dab2234", 69, [0, 0, 3.5, 1.5]),
    ("t3g_500", "c0370650afd1321b", 69, [0, 0, 18.0, 1.5]),
    ("m3s_100", "fb448ecdb0dd65b5", 69, [0, 0, 29.0, 2.5]),
    ("m3k_500", "5fc4082fc5c10d8b", 69, [0, 0, 32.0, 1.0]),
)
SPECIALIST = ("fq2_1999", "6aaae79c25c405e5", 61)
P4 = ("pack_g400_stand", "pack_g400_walk", "pack_stand", "pack_walk")
N4 = ("none_g400_stand", "none_g400_walk", "none_stand", "none_walk")
TEACHER_RUNS = sorted(k for k, v in b1.FAMILY.items() if v.startswith(("Kaggle teacher", "Modal teacher")))
RULE = dict(
    pool="round 3 teacher saves (first input 68 or 69 wide; runs " + ", ".join(TEACHER_RUNS) + ") whose eight 10-episode gate "
         "files train/eval/gate_<save>_{pack,none}{,_g400}_{stand,walk}.json exist (seeds 0 to 9, privileged inputs as round 3 fed them)",
    rank=f"fewest whole-episode falls summed over the pack cells {list(P4)} (gain 400 and gain 200), then over the no-pack "
         f"cells {list(N4)}; tie-break: lower median action jumps per 10 s in pack_walk, then in pack_g400_walk, then name",
    spread="at most one save per training run, taken in rank order",
    cap=CAP, must_include=MUST,
    must_include_why="train/RUNLOG.md: t3h_750 falls 0 of 10 with the pack at gain 400",
    specialist=f"{SPECIALIST[0]} is a group of its own by the coordinator's instruction of 2026-11-20: not ranked, one feed (plain)")
# 4-decimal values the compiled model gave in existing records (priv_first of earlier runs): the check on nominal_priv
RECORDED = {"flightpack-none.json": ((0.0, -0.0335, 0.0007, 0.0186), "train/eval/gate_t3h_750_none_walk.json"),
            "flightpack-load025.json": ((0.2388, -0.0271, -0.0009, 0.0252), "train/eval/ua_t2a_999_load025_stand.json"),
            "flightpack-load050.json": ((0.4776, -0.0244, -0.0015, 0.0279), "train/eval/ua_t2a_999_load050_stand.json"),
            "flightpack-load075.json": ((0.7163, -0.0229, -0.0019, 0.0295), "train/eval/ua_t2a_999_load075_stand.json"),
            "flightpack-nominal.json": ((0.9386, -0.0211, -0.0021, 0.0303), "train/eval/gate_t3h_750_pack_walk.json")}
GROUPS = {"no_pack": ("none",), "quarter_load": ("load025",), "with_pack_50_75_full": ("load050", "load075", "pack")}


def hb(msg):
    HB.parent.mkdir(parents=True, exist_ok=True)
    with open(HB, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n")


# ------------------------------------------------------------------------- nominal payload inputs (file arithmetic)
def nominal_priv(manifest):
    """Payload kg and loaded trunk_base centre of mass (body frame, m) of a manifest, as the probe's loader builds them
    (cmu/whole/delay-repair-20260912/evaluate_delay.load + add_signed_inertias): the trunk_base <inertial> of the robot
    XML, plus every manifest part on trunk_base, minus the old NP-F970 battery the as-built loader removes. Payload kg
    is the manifest total minus the no-pack manifest's, the formula flight_eval.episode uses. Files only."""
    scene = (MODEL_DIR / "scene.xml").read_text()
    xml = (MODEL_DIR / re.search(r'<include file="([^"]+)"', scene).group(1)).read_text()
    m = re.search(r'<body name="trunk_base"[^>]*>\s*<freejoint[^>]*/>\s*<inertial pos="([^"]+)" mass="([^"]+)"', xml)
    assert m, "trunk_base <inertial> not found in the robot XML"
    base_c, base_m = [float(v) for v in m.group(1).split()], float(m.group(2))
    conf = json.loads(ASBUILT_CFG.read_text())
    assert not conf.get("mass_parts") and conf.get("remove_old_battery_kg") == BATTERY_REMOVED_KG, "as-built config changed"
    old = next(x for x in json.loads(AUDIT.read_text())["models"]["official_current"]["parts"] if x["id"] == "np_f970")
    parts = json.loads(Path(manifest).read_text())["parts"]
    none_parts = json.loads((HERE / "manifests/flightpack-none.json").read_text())["parts"]
    kg = math.fsum(p["mass_kg"] for p in parts) - math.fsum(p["mass_kg"] for p in none_parts)
    on_trunk = [(p["mass_kg"], p["position_m"]) for p in parts if p["body"] == "trunk_base"]
    kg_trunk = math.fsum(mm for mm, _ in on_trunk) - math.fsum(p["mass_kg"] for p in none_parts if p["body"] == "trunk_base")
    assert abs(kg_trunk - kg) < 1e-9, f"{manifest}: the payload is not all on trunk_base ({kg_trunk} against {kg})"
    lumps = [(base_m, base_c)] + on_trunk + [(-BATTERY_REMOVED_KG, old["uniform_mesh_com_in_body_m"])]
    mass = math.fsum(mm for mm, _ in lumps)
    com = [math.fsum(mm * c[i] for mm, c in lumps) / mass for i in range(3)]
    rec = RECORDED.get(Path(manifest).name)
    dev = None
    if rec:
        dev = max(abs(a - b) for a, b in zip([kg] + com, rec[0]))
        assert dev <= 6e-5, f"{manifest}: computed {[kg] + com} is not the recorded {rec[0]} ({rec[1]})"
    return dict(manifest=Path(manifest).name, payload_kg=kg, trunk_com_m=com, trunk_base_kg=mass,
                recorded_4_decimals=None if not rec else dict(values=list(rec[0]), record=rec[1], max_abs_difference=dev))


NOMINAL_SOURCE = dict(
    payload_kg="sum of mass_kg over the cell's manifest minus the same sum over manifests/flightpack-none.json",
    trunk_com="mass-weighted mean of: the trunk_base <inertial> (pos, mass) of microduck_rl/src/mjlab_microduck/robot/microduck/"
              "<the robot XML scene.xml includes>, every manifest part with body trunk_base (mass_kg at position_m), and "
              f"-{BATTERY_REMOVED_KG} kg at the NP-F970's uniform_mesh_com_in_body_m (cmu/whole/electrical/existing-model-mass-audit.json): "
              "the sum evaluate_delay.add_signed_inertias writes into the model's body_ipos",
    computed="once per manifest in the main process, before any episode; the same vector goes to every episode of the cell",
    checked="against the 4-decimal values of existing records (RECORDED) at start, and in every 'known' episode against the "
            f"compiled model's body_ipos (difference at most {TOL_M} m; a check, never fed)")


# -------------------------------------------------------------------------------------------- selection (MacBook)
def gate_cell(name, cell):
    """one existing 10-episode gate file of round 3: falls, jumps and speed as b1_rescore.summarise counts them"""
    p = HERE / f"eval/gate_{name}_{cell}.json"
    if not p.is_file():
        return None
    eps = json.loads(p.read_text())["episodes"]
    if not eps:
        return dict(file=f"train/eval/{p.name}", episodes=0)
    case = cell.rsplit("_", 1)[1]
    per = sorted(round(e["action_jumps"] / max(e["fell_at"] if e["fell_at"] is not None else 20.0, 0.5) * 10, 1) for e in eps)
    sp = [e["speed"] for e in eps if e["speed"] is not None and e["fell_at"] is None]
    pf = eps[0].get("priv_first")
    return dict(file=f"train/eval/{p.name}", file_sha256_16=b1.sha(p), episodes=len(eps),
                seeds=[min(e["seed"] for e in eps), max(e["seed"] for e in eps)],
                falls_whole_episode=sum(e["fell_at"] is not None for e in eps),
                falls_in_window=sum(e["fell_at"] is not None and e["fell_at"] <= b1.WINDOW[case] for e in eps),
                fall_times=sorted(e["fell_at"] for e in eps if e["fell_at"] is not None),
                jumps_per_10s_median=per[len(per) // 2], speed_mean_upright=round(sum(sp) / len(sp), 4) if sp else None,
                first_privileged_inputs_fed=pf[0] if pf else None)


def lines_with(path, pattern, limit=6, width=420):
    if not Path(path).is_file():
        return None
    return [[i + 1, line.strip()[:width]] for i, line in enumerate(Path(path).read_text().splitlines()) if re.search(pattern, line)][:limit]


def specialist_record():
    name = SPECIALIST[0]
    files = {}
    for tag in ("nominal_stand", "nominal_walk", "nopack_stand", "nopack_walk"):
        files[f"train/eval/{name}_{tag}.json"] = None
    for load in ("load000", "load025", "load050", "load075"):
        for case in ("stand", "walk"):
            files[f"train/eval/pl_{name}_{load}_{case}.json"] = None
    for f in files:
        p = HERE.parent / f
        if p.is_file():
            s = json.loads(p.read_text())["summary"]
            files[f] = {k: s.get(k) for k in ("manifest", "case", "episodes", "falls", "fall_times", "speed_median_upright")}
    pol = HERE / "policy"
    return dict(
        instruction="coordinator's addition of 2026-11-20 to the attempt 2 preparation: score the with-pack specialist as a group of its own",
        existing_records=files,
        pet_robot_log=lines_with(HERE.parents[3] / "docs/PET_ROBOT_LOG.md", r"fq2 iteration 1999|leg policy fq2 1999"),
        round_1_probe_slots=dict(
            folder="train/policy (sim/policy_legs.py POLICY_DIR)",
            files={f: b1.sha(pol / f) if (pol / f).is_file() else None for f in b1.FILES},
            policy_legs=lines_with(HERE.parent / "sim/policy_legs.py", r"POLICY_DIR\s*=")),
        never="never scored on the B0 filter (gain400, window falls) and never run on the robot")


def select():
    inv = json.loads((HERE / "out/rescore_b1/inventory.json").read_text())
    rows = inv["saves"]
    pool, left_out = [], {}
    for n, r in rows.items():
        if r["input_size"] not in (68, 69):
            continue
        if r["family"] not in TEACHER_RUNS:
            left_out[n] = f"run {r['family']} is not a round 3 teacher run"
            continue
        cells = {c: gate_cell(n, c) for c in P4 + N4}
        if any(v is None or v["episodes"] < 10 for v in cells.values()):
            left_out[n] = "a gate file is missing or holds fewer than 10 episodes"
            continue
        key = [sum(cells[c]["falls_whole_episode"] for c in P4), sum(cells[c]["falls_whole_episode"] for c in N4),
               cells["pack_walk"]["jumps_per_10s_median"], cells["pack_g400_walk"]["jumps_per_10s_median"]]
        pool.append((key + [n], n, cells))
    pool.sort(key=lambda x: x[0])
    chosen, runs, passed_over = [], set(), []
    for key, n, cells in pool:
        if len(chosen) == CAP:
            break
        if rows[n]["family"] in runs:
            passed_over.append(dict(save=n, rank_key=key[:4], why=f"run {rows[n]['family']} already has a save in the list"))
            continue
        runs.add(rows[n]["family"])
        chosen.append((key, n, cells))
    assert MUST in [n for _, n, _ in chosen], f"{MUST} is not in the rule's list: add it by hand and say so"
    cand = []
    for i, (key, n, cells) in enumerate(chosen):
        r = rows[n]
        d = HERE / "ckpt" / n
        local = {f: b1.sha(d / f) if (d / f).is_file() else None for f in b1.FILES}
        cand.append(dict(
            rank=i + 1, save=n, run=r["family"], what=b1.FAMILY.get(r["family"]), checkpoint=f"train/ckpt/{n}",
            sha256_16=local["walk61.onnx"], files_sha256_16=local, files_equal_the_inventory=local == r["files_sha256_16"],
            on_mac_mini_with_equal_files=r["mac_mini_files_equal_macbook"], input_width=r["input_size"],
            privileged_inputs=r["privileged_inputs"], rank_key=key[:4],
            selecting_record=dict(
                pack_cells={c: cells[c] for c in P4}, no_pack_cells={c: cells[c] for c in N4},
                runlog=lines_with(HERE / "RUNLOG.md", rf"\b{MUST} falls 0 of 10\b") if n == MUST else None)))
    computed = [[c["save"], c["sha256_16"], c["input_width"], c["rank_key"]] for c in cand]
    best = pool[0][0][:2]
    d = HERE / "ckpt" / SPECIALIST[0]
    spec_files = {f: b1.sha(d / f) if (d / f).is_file() else None for f in b1.FILES}
    C = b1.cell_specs()
    nominal = {load: nominal_priv(HERE / "manifests" / man) for load, man in b1.LOADS.items()}
    out = dict(
        stage="B1", attempt=2, written=time.strftime("%Y-%m-%dT%H:%M:%S"), rule=RULE,
        source="train/out/rescore_b1/inventory.json (which saves are teachers, file hashes) and the gate files named per candidate",
        pool=dict(teacher_saves_ranked=len(pool), left_out=left_out,
                  saves_sharing_the_best_fall_counts=[n for k, n, _ in pool if k[:2] == best], best_fall_counts=best),
        ranked_first_20=[dict(save=n, run=rows[n]["family"], rank_key=k[:4]) for k, n, _ in pool[:20]],
        passed_over_by_the_one_per_run_rule=passed_over,
        candidates=cand, frozen_candidates_in_script=[list(c) for c in CANDIDATES],
        frozen_list_equals_computed=[list(c) for c in CANDIDATES] == computed,
        specialist=dict(save=SPECIALIST[0], checkpoint=f"train/ckpt/{SPECIALIST[0]}", files_sha256_16=spec_files,
                        frozen_in_script=list(SPECIALIST), frozen_equals_files=all(v == SPECIALIST[1] for v in spec_files.values()),
                        walk_and_stand_are_one_file=spec_files["walk61.onnx"] == spec_files["stand61.onnx"],
                        selecting_record=specialist_record()),
        nominal_inputs=dict(source=NOMINAL_SOURCE, per_load=nominal),
        known_feed_per_cell={c: known_columns(nominal[s["load"]], 69) for c, s in C.items()})
    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "candidates.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"{BASE / 'candidates.json'}: {len(pool)} teacher saves ranked, {len(out['pool']['saves_sharing_the_best_fall_counts'])} "
          f"share the best fall counts {best}")
    for c in cand:
        print(f"  {c['rank']}. {c['save']} ({c['run']}), file {c['sha256_16']}, width {c['input_width']}, key {c['rank_key']}, "
              f"files equal the inventory {c['files_equal_the_inventory']}, on the Mac mini {c['on_mac_mini_with_equal_files']}")
    print(f"  specialist {SPECIALIST[0]}: files {spec_files}, frozen equals files {out['specialist']['frozen_equals_files']}")
    print(f"frozen list in this script equals the computed one: {out['frozen_list_equals_computed']}")
    for load, v in nominal.items():
        print(f"  nominal {load:8s} payload {v['payload_kg']:.6f} kg, trunk COM {[round(x, 6) for x in v['trunk_com_m']]} m, "
              f"record {v['recorded_4_decimals']['values']} (max difference {v['recorded_4_decimals']['max_abs_difference']:.1e})")


# ------------------------------------------------------------------------------------------------ feeds and episodes
def known_vector(nom, width):
    """the values appended to the robot's 61 inputs in the 'known' feed, as Python floats"""
    return [nom["payload_kg"]] + list(nom["trunk_com_m"]) + [0.0, 0.0, 0.0] + ([GAIN_SCALE_ROBOT] if width == 69 else [])


def known_columns(nom, width):
    names = b1.PRIV8 if width == 69 else b1.PRIV7
    return {f"{61 + i} {n}": v for i, (n, v) in enumerate(zip(names, known_vector(nom, width)))}


def feed_record(kind, feed, width):
    base = dict(
        columns_0_to_54="built by the probe's Brain (the runtime's walk_brain.py): gyro 3, projected gravity 3, joint positions 14, "
                        "joint speeds 14, last action 14, command 3, head command 4",
        columns_55_to_60="body_command: zeros, as the Brain writes them in walk mode",
        walk_mode_gain=f"walk_brain.KP_RL is put back to {KP_ROBOT} before every episode and asserted after it "
                       f"({b1.KP['nominal']} in nominal, {b1.KP['gain400']} in gain400)")
    if kind != "teacher":
        base["appended"] = "nothing: a 61-input file (b1_rescore.one; priv_first asserted None, no flag column, no loader switch)"
        return base
    names = b1.PRIV8 if width == 69 else b1.PRIV7
    if feed == "known":
        base["appended"] = {
            "61 payload_kg": "nominal payload of the cell's manifest (nominal_inputs)",
            "62:65 trunk_com_x, trunk_com_y, trunk_com_z": "nominal loaded trunk_base centre of mass of the cell's manifest (nominal_inputs)",
            "65:68 lin_vel_x, lin_vel_y, lin_vel_z": "0.0 on every call (the robot does not measure them)"}
        if width == 69:
            base["appended"]["68 kp_scale"] = (f"{GAIN_SCALE_ROBOT} on every call in both conditions (KP_RL {KP_ROBOT} / 200, the robot's "
                                               "walk mode; the gain400 condition still simulates gain 400)")
        base["how"] = ("flight_eval.priv_now is replaced for the episode by a function returning this constant vector; the "
                       "simulator-reading function is never called (priv_first asserted None)")
    else:
        base["appended"] = {
            "61 payload_kg": "flight_eval.priv_now: manifest total minus the no-pack manifest's",
            "62:65 trunk_com_x, trunk_com_y, trunk_com_z": "flight_eval.priv_now: the compiled model's body_ipos of trunk_base",
            "65:68 lin_vel_x, lin_vel_y, lin_vel_z": "flight_eval.priv_now: the true trunk velocity in the body frame, every call"}
        if width == 69:
            base["appended"]["68 kp_scale"] = "flight_eval.priv_now: simulated KP_RL / 200 (1.0 in nominal, 2.0 in gain400)"
        base["how"] = "flight_eval.priv_now unchanged, wrapped only to count what it returned: the feed of round 3's gates"
    base["appended_names"] = [f"{61 + i} {n}" for i, n in enumerate(names)]
    base["asserted_per_episode"] = "calls > 0 and per column min / max of the appended values against the feed's definition (feed_faults)"
    return base


def one_k(job):
    label, kind, models, manifest, case, extra, feed, width, nom4, kp_expect, seed, strict = job
    if kind != "teacher":  # the reference pair and fq2_1999: attempt 1's own episode function and assertions
        lab, out = b1.one((label, models, manifest, case, extra, None, kp_expect, seed))
        out.update(feed=None, feed_faults=[])
        return lab, out
    import numpy as np
    for k in [k for k in os.environ if k.startswith(("FLIGHT_", "SPK3DIAG_"))]:
        os.environ.pop(k)  # no diagnostic switch of flight_eval is on in a verdict episode
    import flight_eval as fe
    wb = sys.modules.get("walk_brain")  # None in a fresh worker; in a reused one it keeps the last episode's --kp-rl
    kp_found = None if wb is None else int(wb.KP_RL)
    if wb is not None:
        wb.KP_RL = KP_ROBOT
    orig = getattr(fe, "_b1k_priv_now", None) or fe.priv_now  # workers are reused: never wrap a wrapper
    fe._b1k_priv_now = orig
    n = width - 61
    gain_known = [GAIN_SCALE_ROBOT] if n == 8 else []
    known = np.array(list(nom4) + [0.0, 0.0, 0.0] + gain_known, dtype=np.float32)
    st = dict(calls=0, first=None, lo=None, hi=None, width_seen=None, model_com=None)

    def count(p):
        if st["calls"] == 0:
            st["first"], st["lo"], st["hi"], st["width_seen"] = p.copy(), p.copy(), p.copy(), fe.PRIV.get("width")
        else:
            np.minimum(st["lo"], p, out=st["lo"])
            np.maximum(st["hi"], p, out=st["hi"])
        st["calls"] += 1
        return p

    if feed == "known":
        def priv():
            if st["model_com"] is None and fe.PRIV.get("m") is not None:  # a check of the model's constant, never fed
                m = fe.PRIV["m"]
                st["model_com"] = [float(x) for x in m.body_ipos[m.body("trunk_base").id]]
            return count(known.copy())
    else:
        def priv():
            return count(np.array(orig(), dtype=np.float32, copy=True))

    fe.priv_now = priv
    t0 = time.time()
    try:
        r = fe.episode((models, manifest, case, seed, 0.0, 8.0, False, extra))
    finally:
        fe.priv_now = orig
    kp = int(sys.modules["walk_brain"].KP_RL)
    ds = r.get("diag_stat") or {}
    lo, hi = ([float(x) for x in st[k]] if st[k] is not None else None for k in ("lo", "hi"))
    faults = []
    if kp != kp_expect:
        faults.append(f"the episode ran at walk gain {kp}, not {kp_expect}")
    if any(k in ds for k in ("gain_flag_calls", "pack_flag_calls", "prewarm_steps", "warm_state_loaded", "obs_set_calls")):
        faults.append(f"a loader switch was on: {ds}")
    if st["calls"] == 0:
        faults.append("the policy never asked for its appended inputs")
    elif st["width_seen"] != width or len(lo) != n:
        faults.append(f"flight_eval loaded a {st['width_seen']}-wide file ({len(lo)} appended), the frozen width is {width}")
    elif feed == "known":
        want = [float(x) for x in known]
        if lo != want or hi != want:
            faults.append(f"appended values min {lo} max {hi} are not the constant {want}")
        if r.get("priv_first") is not None:
            faults.append("flight_eval.priv_now (the simulator reader) was called")
        if st["model_com"] is None:
            faults.append("the compiled model's trunk COM was never available for the check")
        elif max(abs(a - b) for a, b in zip(st["model_com"], nom4[1:])) > TOL_M:
            faults.append(f"nominal trunk COM {list(nom4[1:])} is not the compiled model's {st['model_com']}")
        if abs(float(fe.PRIV["kg"]) - nom4[0]) > TOL_KG:
            faults.append(f"nominal payload {nom4[0]} is not flight_eval's {fe.PRIV['kg']}")
    else:
        if r.get("priv_first") is None:
            faults.append("flight_eval.priv_now left no priv_first")
        for i, (name, tol) in enumerate(zip(b1.PRIV7[:4], (TOL_KG, TOL_M, TOL_M, TOL_M))):
            if lo[i] != hi[i] or abs(lo[i] - nom4[i]) > tol:
                faults.append(f"{name} fed {lo[i]} to {hi[i]}, nominal {nom4[i]}")
        if max(max(abs(v) for v in lo[4:7]), max(abs(v) for v in hi[4:7])) == 0.0:
            faults.append("the three velocity inputs were 0.0 on every call: not the as-trained feed")
        if n == 8 and (lo[7] != hi[7] or abs(lo[7] - kp_expect / 200.0) > 1e-6):
            faults.append(f"kp_scale fed {lo[7]} to {hi[7]}, the simulated condition is {kp_expect / 200.0}")
    assert not (strict and faults), f"{label} seed {seed}: {faults}"
    out = {k: r.get(k) for k in ("seed", "fell_at", "fall_dir", "max_tilt", "speed", "dist_x", "action_jumps")}
    out.update(kp_rl=kp, kp_rl_found_on_entry=kp_found, obs_set_calls=None, secs=round(time.time() - t0, 2), feed_faults=faults,
               feed=dict(feed=feed, calls=st["calls"], first=None if st["first"] is None else [float(x) for x in st["first"]],
                         min=lo, max=hi, simulator_reader_called=r.get("priv_first") is not None, model_trunk_com=st["model_com"],
                         model_trunk_com_minus_nominal=None if st["model_com"] is None else
                         [a - b for a, b in zip(st["model_com"], nom4[1:])]))
    return label, out


def feed_summary(eps):
    """what a cell's episodes were really fed: calls and the appended columns' range over all calls of all episodes"""
    f = [e["feed"] for e in eps if e.get("feed")]
    if not f:
        return None
    w = len(f[0]["min"])
    dev = [max(abs(x) for x in e["model_trunk_com_minus_nominal"]) for e in f if e["model_trunk_com_minus_nominal"] is not None]
    return dict(feed=f[0]["feed"], episodes=len(f), calls_min=min(e["calls"] for e in f),
                appended_min=[min(e["min"][i] for e in f) for i in range(w)], appended_max=[max(e["max"][i] for e in f) for i in range(w)],
                episodes_that_called_the_simulator_reader=sum(e["simulator_reader_called"] for e in f),
                model_trunk_com_minus_nominal_max_abs_m=max(dev) if dev else None)


# --------------------------------------------------------------------------------------------------- models and plan
def check_models():
    """row -> what runs and how it is fed; refuses before any episode a file that is not the frozen one"""
    rows = {}
    rec = b1.describe(b1.OVERLAY / "models")
    assert rec["files"] == b1.REF_SHA, f"the deployed pair is not the files B0 ran: {rec['files']}"
    facts, ok, reason = b1.judge(rec)
    assert ok is True and not facts["recurrent"], reason
    rows[f"{REF}__{REF_FEED}"] = dict(save=REF, feed=REF_FEED, kind="ref", models=str(b1.OVERLAY / "models"), files=rec["files"],
                                      width=61, reads=reason, cells="no-pack cells only",
                                      stand_policy=f"Pollen stand61 (stand61.onnx {rec['files']['stand61.onnx']}), walk slot walk61 "
                                                   f"({rec['files']['walk61.onnx']})")
    if PHASE == "1":  # the reference and the with-pack specialist alone
        name, want, width = SPECIALIST
        d = HERE / "ckpt" / name
        rec = b1.describe(d)
        facts, ok, reason = b1.judge(rec)
        assert ok is True and not facts["recurrent"] and facts["gain_flag_col"] is None and facts["pack_flag_col"] is None, f"{name}: {reason}"
        assert rec["files"] == {f: want for f in b1.FILES} and facts["input_size"] == width, f"{name}: files {rec['files']}, frozen {want}"
        rows[f"{name}__plain"] = dict(save=name, feed="plain", kind="plain", models=str(d), files=rec["files"], width=61, reads=reason,
                                      cells="all", stand_policy=f"{name} itself in both slots (stand61.onnx = walk61.onnx = {want}), "
                                                               "as the round 1 probe ran it (train/policy, sim/policy_legs.py)")
        return rows
    teachers = {}
    for name, want, width, _ in CANDIDATES:
        d = HERE / "ckpt" / name
        rec = b1.describe(d)
        facts, ok, reason = b1.judge(rec)
        assert ok is False and rec["files"] == {f: want for f in b1.FILES}, f"{name}: files {rec['files']} ({reason}), frozen {want}"
        ins = rec["per_file"]["walk61.onnx"]["inputs"]
        assert len(ins) == 1 and ins[0][1] == [1, width] and width in (68, 69), f"{name}: inputs {ins}, frozen width {width}"
        assert facts["privileged_inputs"] == (b1.PRIV8 if width == 69 else b1.PRIV7), f"{name}: {facts['privileged_inputs']}"
        meta = rec["per_file"]["walk61.onnx"]["meta"]
        if "joint_names" not in meta:  # flight_eval._PrivSession then takes joint names and default pose from ts_start
            assert (HERE / "ckpt/ts_start/walk61.onnx").is_file(), "train/ckpt/ts_start/walk61.onnx is missing (teacher metadata)"
        teachers[name] = dict(models=str(d), files=rec["files"], width=width, reads=reason,
                              metadata="its own" if "joint_names" in meta else
                              "none in the file: joint names and default pose from train/ckpt/ts_start/walk61.onnx (flight_eval._PrivSession)")

    def teacher_row(n, feed):
        t = teachers[n]
        return dict(save=n, feed=feed, kind="teacher", models=t["models"], files=t["files"], width=t["width"], reads=t["reads"],
                    metadata=t["metadata"], cells="all",
                    stand_policy=f"{n} itself in both slots (stand61.onnx = walk61.onnx = {t['files']['walk61.onnx']})")

    for feed in FEEDS:  # every "known" row before any "as_trained" row
        for n in teachers:
            rows[f"{n}__{feed}"] = teacher_row(n, feed)
    return rows


def job(label, row, spec, nominal, seed, strict=True):
    nom = nominal[spec["load"]]
    return (label, row["kind"], row["models"], spec["manifest"], spec["case"], spec["extra"], row["feed"], row["width"],
            [nom["payload_kg"]] + list(nom["trunk_com_m"]), b1.KP[spec["cond"]], seed, strict)


def cell_key(row, spec, nominal):
    """what must be equal for a finished cell file to be kept on a restart"""
    k = dict(save=row["save"], feed=row["feed"], sha256_16=row["files"]["walk61.onnx"], manifest=Path(spec["manifest"]).name,
             flags=spec["extra"])
    if row["feed"] == "known":
        k["appended"] = known_vector(nominal[spec["load"]], row["width"])
    return k


# ------------------------------------------------------------------------------------------------------------ verdict
def group_reading(view, row, C):
    """the stage's three lines read per load group; NOT a pass line of the stage (the two-policy-set fallback of FP-R3)"""
    ref = {case: view.get(f"{REF}__none_nominal_{case}") for case in b1.CASES}
    ref_speed = ref["walk"]["speed_mean_upright"] if ref["walk"] else None
    out = {}
    for g, loads in GROUPS.items():
        cells = [c for c, s in C.items() if s["load"] in loads]
        got = {c: view.get(f"{row}__{c}") for c in cells}
        missing = [c for c, v in got.items() if v is None]
        falls = {c: v["falls_in_window"] for c, v in got.items() if v}
        over_fall = {c: k for c, k in falls.items() if k > b1.FALL_MAX}
        need_jumps = [c for c in cells if C[c]["cond"] == "nominal"]
        jumps, over_jump = {}, []
        for c in need_jumps:
            if got[c] is None or ref[C[c]["case"]] is None:
                continue
            lim = b1.jump_limit(ref[C[c]["case"]]["jumps_per_10s_median"])
            jumps[c] = dict(median=got[c]["jumps_per_10s_median"], limit=lim, ok=got[c]["jumps_per_10s_median"] <= lim)
            if not jumps[c]["ok"]:
                over_jump.append(c)
        speed = None
        if "none" in loads:  # the stage's speed line is on the nominal no-pack walk only
            v = got.get("none_nominal_walk")
            need = None if ref_speed is None else round(b1.SPEED_FRACTION * ref_speed, 4)
            val = v["speed_mean_upright"] if v else None
            speed = dict(cell="none_nominal_walk", value=val, walk61=ref_speed, need=need,
                         ok=None if v is None or need is None else (val is not None and val >= need))
        failed = bool(over_fall) or bool(over_jump) or (speed is not None and speed["ok"] is False)
        complete = not missing and all(c in jumps for c in need_jumps) and (speed is None or speed["ok"] is not None)
        out[g] = dict(cells=cells, holds=False if failed else (True if complete else None), complete=complete, cells_missing=missing,
                      falls_in_window=falls, cells_over_the_fall_line=over_fall, fall_line_alone_holds=None if missing else not over_fall,
                      jumps_line=jumps, cells_over_the_jump_line=over_jump, speed_line=speed,
                      nominal_walking_speed_for_information=dict(
                          values={c: got[c]["speed_mean_upright"] for c in cells if got[c] and C[c]["cond"] == "nominal" and C[c]["case"] == "walk"},
                          walk61_no_pack=ref_speed, note="only the no-pack value is a line of the stage"))
    return out


def main():
    assert CHECK_SEED not in range(b1.VERDICT_SEED0, b1.VERDICT_SEED0 + b1.VERDICT_SEEDS), "the feed check must not touch a verdict seed"
    assert len(CANDIDATES) <= CAP and MUST in [c[0] for c in CANDIDATES], "CANDIDATES is not the frozen rule's list"
    OUT.mkdir(parents=True, exist_ok=True)
    rows, C = check_models(), b1.cell_specs()
    for spec in C.values():
        assert Path(spec["manifest"]).is_file(), spec["manifest"]
    nominal = {load: nominal_priv(HERE / "manifests" / man) for load, man in b1.LOADS.items()}
    cand_file = BASE / "candidates.json"
    selection = json.loads(cand_file.read_text()) if cand_file.is_file() else None
    if selection is not None:
        assert selection["frozen_candidates_in_script"] == [list(c) for c in CANDIDATES], "candidates.json was written for another frozen list"

    def label_of(r, c):
        return f"{r}__{c}"

    plan = [(label_of(r, c), r, c) for r, row in rows.items() for c, spec in C.items() if row["kind"] != "ref" or spec["load"] == "none"]
    plan = [p for p in plan if "only" not in opts or opts["only"] in p[0]]
    summ, todo = {}, []
    for label, r, c in plan:  # resume: a complete cell file of the same save, file and feed is kept
        try:
            old = json.loads((OUT / f"{label}.json").read_text())
            if (sorted(e["seed"] for e in old["episodes"]) == list(range(SEED0, SEED0 + SEEDS))
                    and old["key"] == json.loads(json.dumps(cell_key(rows[r], C[c], nominal)))):
                summ[label] = old["summary"]
                continue
        except (OSError, ValueError, KeyError, IndexError, TypeError):
            pass
        todo.append((label, r, c))
    hb(f"START phase {PHASE} pid {os.getpid()}: {len(todo)} cells x {SEEDS} seeds from {SEED0} ({len(summ)} kept from files), {WORKERS} workers"
       + (", check=only" if CHECK_ONLY else "") + (f", only={opts['only']}" if "only" in opts else "")
       + f"; robot walk gain {KP_ROBOT}; rows " + json.dumps({r: v["files"]["walk61.onnx"] for r, v in rows.items()})
       + "; nominal payload kg and trunk COM " + json.dumps({k: [round(v["payload_kg"], 6)] + [round(x, 6) for x in v["trunk_com_m"]]
                                                            for k, v in nominal.items()}))
    t_start = time.time()
    got = {label: [] for label, _, _ in todo}
    state = dict(feed_check=None)

    def view():
        return {k.replace(f"{REF}__{REF_FEED}__", f"{REF}__"): v for k, v in summ.items()}

    def write():
        vw = view()
        names = [r for r in rows if rows[r]["kind"] != "ref"]
        v = b1.verdict(vw, names + [REF], C)
        for r in names:
            v[r]["by_load_group_not_a_pass_line"] = group_reading(vw, r, C)
        full = (not CHECK_ONLY and "only" not in opts and VERDICT_SEEDS and all(x["complete"] for x in v.values())
                and len(v) == (1 if PHASE == "1" else 2 * len(CANDIDATES)))
        if PHASE == "1":
            spec_row = f"{SPECIALIST[0]}__plain"
            groups = v[spec_row]["by_load_group_not_a_pass_line"]
            question = ("where does the with-pack specialist fq2_1999 (a plain 61-input policy, both slots) stand in B1's cells, read "
                        "for two policy sets: its with-pack cells are the result that matters, without the pack the robot runs walk61 and stand61")
            stage_verdict = dict(
                phase=1, complete=full, row=spec_row,
                passes_the_stage_line_all_20_cells=v[spec_row]["passes"] if full else None,
                with_pack_cells_50_75_full=dict(
                    holds=groups["with_pack_50_75_full"]["holds"],
                    fall_line_alone_holds=groups["with_pack_50_75_full"]["fall_line_alone_holds"],
                    cells_over_the_fall_line=groups["with_pack_50_75_full"]["cells_over_the_fall_line"],
                    cells_over_the_jump_line=groups["with_pack_50_75_full"]["cells_over_the_jump_line"],
                    falls_in_window=groups["with_pack_50_75_full"]["falls_in_window"]),
                quarter_load_cells=dict(holds=groups["quarter_load"]["holds"], cells_over_the_fall_line=groups["quarter_load"]["cells_over_the_fall_line"],
                                        cells_over_the_jump_line=groups["quarter_load"]["cells_over_the_jump_line"]),
                no_pack_cells=dict(holds=groups["no_pack"]["holds"], cells_over_the_fall_line=groups["no_pack"]["cells_over_the_fall_line"],
                                   cells_over_the_jump_line=groups["no_pack"]["cells_over_the_jump_line"], speed_line=groups["no_pack"]["speed_line"]),
                note="the stage's pass line is the 20-cell one and is unchanged; the per-group reading applies the same three lines to "
                     "the cells of one load group (owner decision 2026-11-20 14:55 and the fallback of REQUIREMENTS.json FP-R3: two "
                     "policy sets). In the with-pack group the jump line holds a payload cell to walk61's no-pack nominal cell of the "
                     "same case, as b1_rescore.verdict does; 'fall_line_alone_holds' is the fall line without it. Phase 2 (the "
                     "teachers) is a separate launch and a separate file, summary_teachers.json")
        else:
            known = [r for r in names if rows[r]["feed"] == "known"]
            upper = [r for r in names if rows[r]["feed"] == "as_trained"]
            question = ("fed only what the robot can know (nominal payload and trunk COM of the pack state, KP 200, velocity 0), does "
                        "any round 3 teacher save pass B1's line; it now only informs a possible later merge into one model")
            stage_verdict = dict(
                phase=2, complete=full,
                teacher_rows_fed_what_the_robot_can_know_that_pass=[r for r in known if v[r]["passes"]] if full else None,
                any_teacher_passes_fed_what_the_robot_can_know=any(v[r]["passes"] for r in known) if full else None,
                teacher_rows_as_trained_that_pass_upper_bound=[r for r in upper if v[r]["passes"]] if full else None,
                note="whether a teacher fed pack-state constants counts as 'only inputs the robot has' is the contract's reading "
                     "(B1 history, 2026-11-20 14:40), not decided here; the per-group reading changes no line. Phase 1 (fq2_1999) is in summary.json")
        (OUT / SUMMARY).write_text(json.dumps(dict(
            stage="B1", attempt=2, phase=int(PHASE), seeds=dict(seed0=SEED0, count=SEEDS), only=opts.get("only"), check_only=CHECK_ONLY,
            question=question,
            rule=dict(max_falls_in_window=b1.FALL_MAX, windows_s=b1.WINDOW,
                      speed=f"nominal no-pack walking speed (mean over upright episodes) at least {b1.SPEED_FRACTION} x the deployed walk61's in this run",
                      jumps="median jumps per 10 s at most max(1.5 x walk61, walk61 + 2) in the nominal-condition cells; a payload cell "
                            "is held to walk61's no-pack nominal cell of the same case",
                      unchanged="b1_rescore.verdict and b1_rescore.summarise, as attempt 1"),
            candidate_rule=RULE, frozen_candidates=[list(c) for c in CANDIDATES], frozen_specialist=list(SPECIALIST),
            selection=selection if selection is not None else "out/rescore_b1k/candidates.json is not on this machine (select=1 writes it on the MacBook)",
            nominal_inputs=dict(source=NOMINAL_SOURCE, per_load=nominal),
            conditions={k: dict(flags=f, walk_mode_gain=b1.KP[k]) for k, f in b1.COND.items()},
            cells={c: dict(manifest=Path(s["manifest"]).name, case=s["case"], condition=s["cond"], flags=s["extra"],
                           start="policy from the first tick (--stand-s 0)" if "--stand-s" in s["extra"] else "0.3 s open-loop stand, then the policy",
                           known_feed_appended_69_wide=known_columns(nominal[s["load"]], 69)) for c, s in C.items()},
            rows={r: dict(save=x["save"], feed=x["feed"], models=x["models"], files_sha256_16=x["files"], input_width=x["width"],
                          reads=x["reads"], metadata=x.get("metadata"), cells=x["cells"], stand_policy_in_every_cell=x["stand_policy"],
                          fed=feed_record(x["kind"], x["feed"], x["width"])) for r, x in rows.items()},
            feed_check=state["feed_check"], results=summ, verdict=v, stage_verdict=stage_verdict), indent=1, default=str))
        return v

    def feed_check(ex):
        """one episode per row on a seed outside the verdict set; every appended column is listed as fed"""
        jobs, labels = [], []
        for r, row in rows.items():
            c = CHECK_CELL_REF if row["kind"] == "ref" else CHECK_CELL
            labels.append((f"{r}__{c}", r, c))
            jobs.append(job(f"{r}__{c}", row, C[c], nominal, CHECK_SEED, strict=False))
        res, bad = {}, []
        for (label, r, c), (_, e) in zip(labels, ex.map(one_k, jobs)):
            row, f = rows[r], e["feed"]
            names = [] if row["kind"] != "teacher" else [f"{61 + i} {n}" for i, n in enumerate(b1.PRIV8 if row["width"] == 69 else b1.PRIV7)]
            res[label] = dict(
                save=row["save"], feed=row["feed"], file=row["files"]["walk61.onnx"], cell=c, seed=CHECK_SEED,
                expected_appended=None if row["feed"] != "known" else known_columns(nominal[C[c]["load"]], row["width"]),
                policy_calls_counted=None if f is None else f["calls"],
                appended_first=None if f is None else dict(zip(names, f["first"])),
                appended_min=None if f is None else dict(zip(names, f["min"])),
                appended_max=None if f is None else dict(zip(names, f["max"])),
                simulator_reader_called=None if f is None else f["simulator_reader_called"],
                model_trunk_com=None if f is None else f["model_trunk_com"],
                model_trunk_com_minus_nominal=None if f is None else f["model_trunk_com_minus_nominal"],
                walk_gain=e["kp_rl"], fell_at=e["fell_at"], speed=e["speed"], action_jumps=e["action_jumps"], secs=e["secs"],
                faults=e["feed_faults"])
            bad += [f"{label}: {x}" for x in e["feed_faults"]]
        mean = sum(x["secs"] for x in res.values()) / len(res)
        est = len(todo) * SEEDS * mean / WORKERS / 60
        state["feed_check"] = dict(ok=not bad, faults=bad, seed=CHECK_SEED, rows=res, mean_secs_per_episode=round(mean, 2),
                                   estimate_min_for_the_cells_to_run=round(est))
        (BASE / FEED_CHECK).write_text(json.dumps(state["feed_check"], indent=1, default=str))
        for label, x in res.items():
            print(f"{label}: file {x['file']}, calls {x['policy_calls_counted']}, min {x['appended_min']}, max {x['appended_max']}, "
                  f"reader called {x['simulator_reader_called']}, gain {x['walk_gain']}, fell_at {x['fell_at']}, faults {x['faults'] or 'none'}",
                  flush=True)
        fed = [f"{k.split('__' + CHECK_CELL)[0]} calls {x['policy_calls_counted']} min {[round(v, 4) for v in x['appended_min'].values()]} "
               f"max {[round(v, 4) for v in x['appended_max'].values()]}" for k, x in res.items() if x["appended_min"]]
        plain = [f"{k} ran at walk gain {x['walk_gain']}, nothing appended" for k, x in res.items() if not x["appended_min"]]
        hb(f"FEED CHECK {'OK' if not bad else 'NOT OK'}: {len(res)} rows x 1 episode on seed {CHECK_SEED}; faults {bad or 'none'}; "
           + "; ".join(fed + plain) + f"; mean {mean:.1f} s per episode, about {est:.0f} min for {len(todo)} cells")
        return not bad

    with ProcessPoolExecutor(WORKERS) as ex:
        ok = feed_check(ex)
        write()
        if not ok:
            hb(f"FAILED feed check: see the line above and out/rescore_b1k/{FEED_CHECK}")
            sys.exit(1)
        if CHECK_ONLY:
            hb(f"DONE phase {PHASE} feed check only (check=only): no cell was scored")
            return
        jobs = [job(label, rows[r], C[c], nominal, seed) for label, r, c in todo for seed in range(SEED0, SEED0 + SEEDS)]
        where = {label: (r, c) for label, r, c in todo}
        for label, e in ex.map(one_k, jobs):
            got[label].append(e)
            if len(got[label]) < SEEDS:
                continue
            r, c = where[label]
            s = b1.summarise(label, got[label])
            s["fed"] = feed_summary(got[label])
            s["stand_policy"] = rows[r]["stand_policy"]
            summ[label] = s
            (OUT / f"{label}.json").write_text(json.dumps(dict(key=cell_key(rows[r], C[c], nominal), summary=s, episodes=got[label]),
                                                          indent=1, default=str))
            write()
            fed = s["fed"]
            hb(f"{label}: window falls {s['falls_in_window']} of {SEEDS} (blocks of 10: {s['falls_in_window_per_block_of_10']}, "
               f"95 % {s['falls_in_window_wilson95']}); whole episode {s['falls_whole_episode']}; jumps/10 s median "
               f"{s['jumps_per_10s_median']} quartiles {s['jumps_per_10s_quartiles']}; speed {s['speed_mean_upright']}; walk gain "
               f"{s['kp_rl']}; " + ("no appended inputs" if fed is None else
                                   f"appended min {[round(x, 4) for x in fed['appended_min']]} max {[round(x, 4) for x in fed['appended_max']]} "
                                   f"calls {fed['calls_min']}") + f"; {time.time() - t_start:.0f} s since start")
    v = write()
    for r, x in v.items():
        g = {k: y["holds"] for k, y in x["by_load_group_not_a_pass_line"].items()}
        hb(f"VERDICT {r}: passes {x['passes']}; cells over {b1.FALL_MAX} window falls {x['cells_over_the_fall_line']}; speed "
           f"{x['speed_line']['value']} against {x['speed_line']['need']} ok {x['speed_line']['ok']}; cells over the jump line "
           f"{x['cells_over_the_jump_line']}; missing {len(x['cells_missing'])}; by load group (not a pass line) {g}")
        if PHASE == "1":
            wp = x["by_load_group_not_a_pass_line"]["with_pack_50_75_full"]
            hb(f"WITH-PACK CELLS {r} (50 %, 75 %, full pack; not the stage's pass line): holds {wp['holds']}; window falls of {SEEDS} "
               f"{wp['falls_in_window']}; over the fall line {wp['cells_over_the_fall_line']}; over the jump line {wp['cells_over_the_jump_line']}")
    hb(f"DONE phase {PHASE}: out/rescore_b1k/{SUMMARY}")


if __name__ == "__main__":
    if SELECT:
        select()
    else:
        try:
            main()
        except Exception as e:
            hb(f"FAILED {type(e).__name__}: {e}")
            raise
