"""Stage B1 of ../TRAIN-CONTRACT.json (2026-11-20): among the saves round 3 already produced, is there a policy that
(a) reads only inputs the real robot can supply and (b) holds every constant-load cell on the yardstick stage B0
validated (b0_yardstick.py: gain400, falls counted inside the robot-tested window)? Nothing is trained.

  $PY train/b1_rescore.py [workers=7] [seeds=60] [seed0=2000] [only=<substring>] [smoke=1] [out=rescore_b1]   (Mac mini only)
  <python with onnxruntime> train/b1_rescore.py inventory=1 [mini=ssh|skip|<sha256 listing file>]   (MacBook; reads files, no simulation)

Inventory (inventory=1 -> train/out/<out>/inventory.json). The scored saves are the names with a file
eval/gate_<name>_none_g400_walk.json (these files exist on the MacBook only). Deployability is decided from each
save's two ONNX files, by the rules the runtime's own loader applies (guide/firmware/mac/walk_brain.py Brain.__init__):
first input obs [1, 61] whose observation_names metadata is the runtime's list, at most one more input, and that one
named state_in with an output state_out (Brain.run_policy feeds it back). A first input 68 or 69 wide is a privileged
teacher: flight_eval.priv_now appends payload mass, trunk centre of mass, trunk velocity (and the true gain scale)
from the simulator, none of which the robot measures. A folder with a file "prewarm" is the same network as its base
save, read through a loader step (flight_eval FLIGHT_PREWARM) that walk_brain.py does not have: not a separate
deployable save. Candidates for the 60-episode run: deployable saves whose existing 10-episode files (seeds 0 to 9)
show at most 2 falls inside the window in each of the four gain400 cells, best first, at most 12. Rank: fewest window
falls summed over the four gain400 cells, then over the four nominal-gain cells, then fewest whole-episode falls over
all eight, then name. The result is frozen in CANDIDATES below with each file's sha256, so the run cannot drift from
the list that was reviewed; inventory=1 says whether the frozen list still equals the computed one.

Scoring. Saves: CANDIDATES plus the reference "deployed" (runtime-overlay/models: walk61 in the walk slot, stand61 at
zero command), the reference in the no-pack cells only.
Cells: manifests none / load025 / load050 / load075 / pack (flightpack-nominal.json) x stand / walk x conditions
  nominal   no extra flag: the simulation as it is, walk-mode gain KP_RL 200 (CURRENT-STATE.json walking_policy)
  gain400   --kp-rl 400, the stand-in B0 validated
Cells with a payload add --stand-s 0 (ts3_gates.py S0, as its pack cells and accept_universal.py's load cells: the
policy runs from the first tick). Episode as the gates: the case's command (0 or 0.25 m/s) from 2.0 s to 17.0 s, zero
command to 20.0 s. Falls are counted inside the robot-tested window as in B0: fell_at <= 6.0 s walking, <= 12.0 s
standing. Jumps = tick-to-tick action jumps over 0.5 rad per 10 s of upright time. Seeds 2000 to 2059.

Feed: every save gets what the robot's runtime would give it, in BOTH conditions.
  - Inputs 0:55 come from the probe's Brain (the runtime's code): gyro 3, gravity 3, joint positions 14, joint speeds
    14, last action 14, command 3, head command 4. Inputs 55:61 (body_command) are zeros, as the Brain writes them in
    walk mode.
  - Gain flag. A student distilled with --gain-flag-col carries gain_flag_col in its file (column 59, inside
    body_command) and was trained on "gain scale - 1" there. The robot's walk mode runs KP_RL 200 = scale 1.0 = flag
    0.0, which is also what the unchanged runtime already writes in that column. flight_eval on its own would write
    KP_RL / 200 - 1 of the SIMULATED condition (1.0 under --kp-rl 400), a value the robot cannot know. So such a save
    runs with FLIGHT_OBS_SET="<col>:0.0" in both conditions: that switch turns flight_eval's own flag feed off and
    writes the column on every call. Each episode asserts the counters: obs_set_calls > 0, no gain_flag_calls.
  - Recurrent state: flight_eval._StatefulSession, the rule of the runtime's Brain.run_policy: zeros on entry (first
    call, or more than 5 control ticks without a call), then state_out fed back; stand and walk slots loaded from one
    file share the state. No prewarm, no warm start, no privileged value (priv_first must be None).
  - Gain per episode. brain_sim_check sets --kp-rl on the walk_brain module and never restores it, and pool workers
    are reused, so without care a nominal episode that follows a gain400 one in the same worker would run at 400.
    Every episode therefore starts by putting walk_brain.KP_RL back to the robot's 200 and ends by asserting the gain
    the episode ran at (200 nominal, 400 gain400); the value found on entry is kept in the episode record.

Pass line of the stage (fixed in the contract, not here). Per save: at most 6 window falls of 60 in every cell;
nominal no-pack walking speed at least 0.6 of the deployed walk61's in the same run (B0's figure: mean over the
episodes that stayed up of distance along x in the 15 s of the walk command / 15 s); median jumps at most
max(1.5 x walk61, walk61 + 2) in the nominal-condition cells. walk61 runs only without the pack, so a payload cell is
held to walk61's no-pack nominal cell of the same case (the level ts3_gates.py uses for its pack cells); the narrower
reading (no-pack nominal cells only) is written beside it.

Writes train/out/<out>/<save>__<cell>.json and summary.json after every cell; heartbeat
train/logs/b1_<out>_heartbeat.txt, one line per cell, last line DONE or FAILED. A finished cell file is kept on a
restart. smoke=1: the feed check, 2 episodes on seeds from 7000 (never the verdict seeds): every candidate in
none_nominal_walk, the reference in none_gain400_stand (first, so later nominal episodes meet a worker that ran at 400),
none_nominal_stand and none_nominal_walk; files under train/out/<out>/smoke/, heartbeat b1_<out>_smoke_heartbeat.txt.
"""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
opts = dict(a.split("=", 1) for a in sys.argv[1:])
SMOKE = opts.get("smoke", "0") not in ("", "0")
INVENTORY = opts.get("inventory", "0") not in ("", "0")
NAME = opts.get("out", "rescore_b1")
SEEDS = int(opts.get("seeds", 2 if SMOKE else 60))
SEED0 = int(opts.get("seed0", 7000 if SMOKE else 2000))
WORKERS = min(int(opts.get("workers", 7)), 8)
OUT = HERE / "out" / NAME / "smoke" if SMOKE else HERE / "out" / NAME
HB = HERE / "logs" / f"b1_{NAME}{'_smoke' if SMOKE else ''}_heartbeat.txt"
FL = HERE.parent
OVERLAY = (HERE / "../../../microduck_rl/cmu/whole/runtime-overlay").resolve()
STATE = (HERE / "../../../CURRENT-STATE.json").resolve()
MIRROR = "code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110"  # under $HOME on the Mac mini

FILES = ("walk61.onnx", "stand61.onnx")
OBS_NAMES = "base_ang_vel,projected_gravity,joint_pos,joint_vel,actions,command,head_command,body_command"  # walk_brain.OBS_NAMES
OBS_WIDTHS = (3, 3, 14, 14, 14, 3, 4, 6)
PRIV7 = ["payload_kg", "trunk_com_x", "trunk_com_y", "trunk_com_z", "lin_vel_x", "lin_vel_y", "lin_vel_z"]  # teacher.py PRIV_NAMES
PRIV8 = PRIV7 + ["kp_scale"]                                                                # after teacher.enable_gain
REF = "deployed"
REF_SHA = {"walk61.onnx": "e36332d383997d51", "stand61.onnx": "1569268713e40dee"}  # as out/yardstick_b0/summary.json
# Frozen by inventory=1 on 2026-11-20 (out/rescore_b1/inventory.json "candidates"), rank order; sha256[:16] of walk61.onnx
# (= stand61.onnx: every candidate folder holds one file twice).
CANDIDATES = (
    ("s3AB_100", "d4d3ffb74fee8d46"), ("s3RLa_160", "b3f4105228388931"), ("s3h_40", "c73bf25db5c88705"),
    ("s3h_120", "19216cd45c66baf9"), ("s3h_160", "aadb7bf100a1a951"), ("s3h_140", "655f2ba655b9b60c"),
    ("s3h_80", "2069df4f6e76652f"), ("s3h_100", "00246431feab5138"), ("s3AB_60", "3e814fba69cae68b"),
    ("s3h_60", "2190bea03aecfeda"), ("s3l_t3g_625_140", "ba1ae3efb2f40da6"), ("s3a_60", "652b4a9d36d91eee"),
)

LOADS = {"none": "flightpack-none.json", "load025": "flightpack-load025.json", "load050": "flightpack-load050.json",
         "load075": "flightpack-load075.json", "pack": "flightpack-nominal.json"}
S0 = ["--stand-s", "0"]
COND = {"nominal": [], "gain400": ["--kp-rl", "400"]}
CASES = ("stand", "walk")
WINDOW = {"walk": 2.0 + 4.0, "stand": 2.0 + 10.0}
FALL_MAX, SPEED_FRACTION, BLOCK = 6, 0.6, 10
VERDICT_SEED0, VERDICT_SEEDS = 2000, 60
# inventory: the eight cells of ts3_gates.py whose 10-episode files exist, and the screen on them
OLD_G400 = ("none_g400_stand", "none_g400_walk", "pack_g400_stand", "pack_g400_walk")
OLD_NOMINAL = ("none_stand", "none_walk", "pack_stand", "pack_walk")
SCREEN_MAX, CAP = 2, 12
FAMILY = {
    "walk61": "the deployed pair itself (Pollen walk61 and stand61, runtime-overlay/models): the reference row, not a round 3 save",
    "ts_start": "run A, the one-frame start policy of round 3",
    "s2r6": "round 2 recurrent student (the save that fell on the robot on 2026-11-19)",
    "t2a": "round 2 privileged teacher",
    "t3a": "Kaggle teacher ts3-teach-a (universal5t, from ts_start, seed 1)",
    "t3b": "Kaggle teacher ts3-teach-b (universal5t, from walk61, seed 1)",
    "t3c": "Kaggle teacher ts3-teach-c (universal5t, from ts_start, seed 2)",
    "t3d": "Kaggle teacher ts3-teach-d (universal5t, from walk61, seed 2)",
    "t3g": "Kaggle teacher ts3-teach-g (universal5tg: the gain scale is an eighth privileged input; from ts_start)",
    "t3h": "Kaggle teacher ts3-teach-h (universal5tg, from walk61)",
    "t3k": "Kaggle teacher ts3-teach-k (continues t3h_750 under universal5tgs)",
    "m3w": "Modal teacher ts3m-w61long (from walk61; stopped itself at iteration 250)",
    "m3p": "Modal teacher ts3m-b05 (from ts_start, walk61 anchor weight 0.5)",
    "m3q": "Modal teacher ts3m-b6 (from ts_start, walk61 anchor weight 6.0)",
    "m3g": "Modal teacher ts3m-w61g (from walk61, 2500 iterations)",
    "m3k": "Modal teacher ts3m-k625 (from t3g_625 under universal5tgs)",
    "m3s": "Modal teacher ts3m-b625 (from t3g_625 under universal5tgb)",
    "s3h": "Mamba student ts3s-t3h-750-m of teacher t3h_750",
    "s3m_t3g_625": "Mamba student ts3s-t3g-625-m of teacher t3g_625",
    "s3l_t3g_625": "LSTM student ts3s-t3g-625-l of teacher t3g_625",
    "s3a": "Mamba student ts3s-m3s-450-a of teacher m3s_450 (walk61 anchor)",
    "s3AB": "Mamba student run AB of teacher t3h_750 (pack stop case and a gain flag in input column 59)",
    "s3RLa": "run AB save 140 continued with a PPO term (ts3rl-a1), gain flag in input column 59",
    "s3ABw": "the s3AB files read through the self-prewarm loader (10 calls on the entry observation)",
    "s3aw": "the s3a_60 file read through the self-prewarm loader (10 calls on the entry observation)",
}


def robot_walk_gain():
    """KP_RL of the robot's walk mode, from CURRENT-STATE.json walking_policy"""
    value = json.loads(STATE.read_text())["facts"]["walking_policy"]["value"]
    m = re.search(r"KP_RL (\d+)", value)
    assert m, f"{STATE}: walking_policy names no KP_RL"
    return int(m.group(1))


KP_ROBOT = robot_walk_gain()
KP = {"nominal": KP_ROBOT, "gain400": 400}
GAIN_FLAG_ROBOT = KP_ROBOT / 200.0 - 1.0  # the flag's training definition, gain scale - 1 with scale 1.0 = KP 200


def hb(msg):
    HB.parent.mkdir(parents=True, exist_ok=True)
    with open(HB, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def describe(d):
    """What the policy in models dir d reads, from its two ONNX files (inputs, outputs, metadata) and a 'prewarm' file."""
    import onnxruntime as ort
    d = Path(d)
    rec = dict(folder_exists=d.is_dir(), files={}, per_file={}, prewarm=None)
    if (d / "prewarm").is_file():
        rec["prewarm"] = (d / "prewarm").read_text().strip()
    for f in FILES:
        p = d / f
        if not p.is_file():
            rec["files"][f] = None
            continue
        s = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
        rec["files"][f] = sha(p)
        rec["per_file"][f] = dict(inputs=[[i.name, list(i.shape)] for i in s.get_inputs()],
                                  outputs=[[o.name, list(o.shape)] for o in s.get_outputs()],
                                  meta=dict(s.get_modelmeta().custom_metadata_map))
    return rec


def judge(rec):
    """(facts, deployable, reason) from describe(): deployable is True only when the unchanged runtime can load the
    folder and every input is one the robot supplies; None when a file is missing (never guessed)."""
    facts = dict(input_size=None, input_names=None, inputs=None, recurrent=None, state=None, privileged_inputs=[],
                 gain_flag_col=None, pack_flag_col=None, prewarm=rec["prewarm"], walk_and_stand_are_one_file=None)
    missing = [f for f in FILES if rec["files"].get(f) is None]
    if missing:
        return facts, None, f"checkpoint file missing on this machine: {', '.join(missing)}"
    facts["walk_and_stand_are_one_file"] = rec["files"]["walk61.onnx"] == rec["files"]["stand61.onnx"]
    why, priv = [], []
    for f in (FILES[:1] if facts["walk_and_stand_are_one_file"] else FILES):  # one file in both slots is judged once
        pf = rec["per_file"][f]
        ins, outs, meta = pf["inputs"], pf["outputs"], pf["meta"]
        width = ins[0][1][1] if len(ins[0][1]) == 2 else None
        if f == "walk61.onnx":
            names = meta.get("observation_names")
            facts.update(input_size=width, inputs=ins, input_names=names.split(",") if names else None,
                         recurrent=len(ins) > 1,
                         state=None if len(ins) < 2 else dict(input=ins[1][0], shape=ins[1][1], core=meta.get("recurrent_core"),
                                                              output=outs[1][0] if len(outs) > 1 else None),
                         gain_flag_col=int(meta["gain_flag_col"]) if meta.get("gain_flag_col") not in (None, "") else None,
                         pack_flag_col=int(meta["pack_flag_col"]) if meta.get("pack_flag_col") not in (None, "") else None)
        if width in (68, 69):
            priv = PRIV8 if width == 69 or len(priv) == 8 else PRIV7
            why.append(f"{f} input {ins[0][0]} [1, {width}]: 61 robot readings + {width - 61} simulator values "
                       f"({', '.join(PRIV8 if width == 69 else PRIV7)}; flight_eval.priv_now)")
            continue
        if ins[0][1] != [1, 61]:
            why.append(f"{f} first input is {ins[0][1]}, the runtime builds [1, 61]")
            continue
        if meta.get("observation_names") != OBS_NAMES:
            why.append(f"{f} observation_names metadata is not the runtime's list")
        if float(meta.get("action_scale", "1")) != 1.0:
            why.append(f"{f} action_scale is not 1")
        if len(ins) > 2 or (len(ins) == 2 and (ins[1][0] != "state_in" or len(outs) < 2 or outs[1][0] != "state_out")):
            why.append(f"{f} has inputs {[i[0] for i in ins]}: the runtime feeds obs and at most state_in / state_out")
        if meta.get("pack_flag_col") not in (None, ""):
            priv = priv or ["pack_fitted_flag"]
            why.append(f"{f} reads a pack-fitted flag in column {meta['pack_flag_col']}: the robot does not measure its payload")
    facts["privileged_inputs"] = priv
    if why:
        return facts, False, "; ".join(why)
    if rec["prewarm"]:
        return facts, False, (f"folder holds 'prewarm' = {rec['prewarm']}: the same 61-input network as its base save, read through a "
                              "self-prewarm loader the robot's walk_brain.py does not have; the base save has its own row")
    kind = "one-frame" if not facts["recurrent"] else f"recurrent ({facts['state']['core'] or 'core not named'}, state {facts['state']['shape']})"
    how = "obs [1, 61] with the runtime's observation list" + ("" if not facts["recurrent"] else ", state_in / state_out fed back by Brain.run_policy")
    if facts["gain_flag_col"] is not None:
        how += (f"; gain flag in column {facts['gain_flag_col']} (body_command): the robot's walk mode gives {GAIN_FLAG_ROBOT} "
                f"(KP_RL {KP_ROBOT}), the value the unchanged runtime already writes there")
    return facts, True, f"{kind}: {how}"


def obs_term(col):
    """name of the runtime observation term that holds input column col"""
    at = 0
    for n, w in zip(OBS_NAMES.split(","), OBS_WIDTHS):
        if at <= col < at + w:
            return f"{n}[{col - at}]"
        at += w
    return None


# ---------------------------------------------------------------------------------------------- inventory (MacBook)
def family(name):
    return name if name in ("walk61", "ts_start") else re.sub(r"_\d+$", "", name)


def existing(name):
    """the save's 10-episode files of 2026-11-19/20: falls inside the B0 window and over the whole episode"""
    out = {}
    for cell in OLD_NOMINAL + OLD_G400:
        p = HERE / f"eval/gate_{name}_{cell}.json"
        if not p.is_file():
            out[cell] = None
            continue
        eps = json.loads(p.read_text())["episodes"]
        case = cell.rsplit("_", 1)[1]
        ds = (eps[0].get("diag_stat") or {}) if eps else {}
        out[cell] = dict(episodes=len(eps), seeds=[min(e["seed"] for e in eps), max(e["seed"] for e in eps)] if eps else None,
                         window_falls=sum(e["fell_at"] is not None and e["fell_at"] <= WINDOW[case] for e in eps),
                         falls_whole_episode=sum(e["fell_at"] is not None for e in eps),
                         gain_flag_fed=ds.get("gain_flag_value"), prewarm_steps=ds.get("prewarm_steps"))
    return out


def mini_listing():
    """{path under the mirror's flight folder: sha256[:16]} of the model files on the Mac mini, or (None, why)"""
    how = opts.get("mini", "ssh")
    if how == "skip":
        return None, "not checked (mini=skip)"
    if how == "ssh":
        cmd = (f"cd {MIRROR} && find train/ckpt ../../microduck_rl/cmu/whole/runtime-overlay/models -maxdepth 2 -type f "
               "\\( -name walk61.onnx -o -name stand61.onnx -o -name prewarm \\) -exec shasum -a 256 {} +")
        try:
            text = subprocess.run(["ssh", "-o", "ConnectTimeout=10", "mac-mini", cmd], capture_output=True, text=True, timeout=120).stdout
        except Exception as e:
            return None, f"not checked (ssh mac-mini failed: {type(e).__name__})"
        src = f"ssh mac-mini, shasum over ~/{MIRROR}/train/ckpt at {time.strftime('%Y-%m-%dT%H:%M:%S')}"
    else:
        text, src = Path(how).read_text(), f"listing file {how}"
    got = {}
    for line in text.splitlines():
        m = re.match(r"^([0-9a-f]{64})\s+(\S+)$", line.strip())
        if m:
            got[m.group(2).removeprefix("./")] = m.group(1)[:16]
    return (got, src) if got else (None, f"not checked ({src} returned no file)")


def inventory():
    names = sorted(p.name[len("gate_"):-len("_none_g400_walk.json")] for p in (HERE / "eval").glob("gate_*_none_g400_walk.json"))
    assert names, "no eval/gate_<name>_none_g400_walk.json here: the inventory runs on the MacBook, where the scored files are"
    mini, mini_src = mini_listing()
    rows = {}
    for n in names:
        is_ref = n == "walk61"
        d = OVERLAY / "models" if is_ref else HERE / "ckpt" / n
        rel = "../../microduck_rl/cmu/whole/runtime-overlay/models" if is_ref else f"train/ckpt/{n}"
        rec = describe(d)
        facts, ok, reason = judge(rec)
        on_mini = same = None
        if mini is not None:
            there = {f: mini.get(f"{rel}/{f}") for f in FILES}
            on_mini = all(v is not None for v in there.values())
            same = on_mini and all(there[f] == rec["files"][f] for f in FILES) if all(rec["files"].get(f) for f in FILES) else None
        ex = existing(n)
        gf = None
        if facts["gain_flag_col"] is not None:
            gf = dict(column=facts["gain_flag_col"], runtime_term=obs_term(facts["gain_flag_col"]),
                      trained_on="gain scale - 1 (distill_worker.py --gain-flag-col: o[:, col] = env._kp_scale - 1; scale 1.0 = KP 200)",
                      robot_walk_mode_value=GAIN_FLAG_ROBOT,
                      why=f"CURRENT-STATE.json walking_policy: walk mode runs KP_RL {KP_ROBOT}; walk_brain.py writes zeros into body_command in walk mode",
                      fed_in_the_existing_10_episode_files={c: v["gain_flag_fed"] for c, v in ex.items() if v})
        rows[n] = dict(family=family(n), checkpoint=rel, exists_on_macbook=all(rec["files"].get(f) for f in FILES),
                       exists_on_mac_mini=on_mini, mac_mini_files_equal_macbook=same, files_sha256_16=rec["files"],
                       input_size=facts["input_size"], inputs=facts["inputs"], input_names=facts["input_names"],
                       recurrent=facts["recurrent"], state=facts["state"],
                       hidden_state_carried=None if not facts["recurrent"] else
                       "zeros on entry (first call or more than 5 control ticks without one), then state_out fed back as state_in; "
                       "one state for the stand and walk slots when both are one file (walk_brain.Brain.run_policy; flight_eval._StatefulSession)",
                       privileged_inputs=facts["privileged_inputs"], gain_flag=gf, pack_flag_col=facts["pack_flag_col"],
                       prewarm=facts["prewarm"], walk_and_stand_are_one_file=facts["walk_and_stand_are_one_file"],
                       deployable=ok, reason=reason, is_reference=is_ref,
                       existing_10_episode_window_falls_gain400={c: (ex[c] or {}).get("window_falls") for c in OLD_G400},
                       existing_10_episode_cells=ex)
    by_sha = {}
    for n, r in rows.items():  # a prewarm folder points at the save with the same file and no prewarm
        if r["deployable"] and not r["is_reference"]:
            by_sha[r["files_sha256_16"]["walk61.onnx"]] = n
    for n, r in rows.items():
        r["same_file_as"] = by_sha.get(r["files_sha256_16"].get("walk61.onnx")) if r["prewarm"] else None
    # the screen and the rank
    ranked = []
    for n, r in rows.items():
        ex = r["existing_10_episode_cells"]
        if r["is_reference"] or r["deployable"] is not True:
            r["screen"] = None
            continue
        if any(ex[c] is None or ex[c]["episodes"] < 10 for c in OLD_G400):
            r["screen"] = dict(eligible=False, why="a gain400 file is missing or holds fewer than 10 episodes")
            continue
        w = [ex[c]["window_falls"] for c in OLD_G400]
        key = [sum(w), sum(10 if ex[c] is None else ex[c]["window_falls"] for c in OLD_NOMINAL),
               sum(10 if ex[c] is None else ex[c]["falls_whole_episode"] for c in OLD_NOMINAL + OLD_G400)]
        r["screen"] = dict(eligible=max(w) <= SCREEN_MAX, gain400_window_falls=dict(zip(OLD_G400, w)), rank_key=key)
        if r["gain_flag"]:
            r["screen"]["note"] = ("its gain400 files were scored with the gain flag fed 1.0 (the simulated condition); "
                                   f"the robot would feed {GAIN_FLAG_ROBOT}, so this screen is not like for like for this save")
        if max(w) <= SCREEN_MAX:
            ranked.append((key, n))
    ranked.sort()
    chosen = [n for _, n in ranked[:CAP]]
    for i, (key, n) in enumerate(ranked):
        rows[n]["screen"].update(rank=i + 1, selected=i < CAP)
    fams = {}
    for n, r in rows.items():
        f = fams.setdefault(r["family"], dict(what=FAMILY.get(r["family"], "not described"), saves=0, deployable=0, not_deployable=0,
                                              file_missing=0, input_sizes=set(), recurrent=set(), privileged_inputs=set(),
                                              screen_eligible=0, selected=0, reasons=set()))
        f["saves"] += 1
        f["deployable" if r["deployable"] else ("file_missing" if r["deployable"] is None else "not_deployable")] += 1
        f["input_sizes"].add(r["input_size"])
        f["recurrent"].add(r["recurrent"])
        f["privileged_inputs"].update(r["privileged_inputs"])
        f["reasons"].add(r["reason"])
        f["screen_eligible"] += int(bool(r["screen"] and r["screen"]["eligible"]))
        f["selected"] += int(n in chosen)
    for f in fams.values():
        for k in ("input_sizes", "recurrent", "privileged_inputs", "reasons"):
            f[k] = sorted(f[k], key=str)
    frozen = [n for n, _ in CANDIDATES]
    cand = [dict(rank=i + 1, save=n, sha256_16=rows[n]["files_sha256_16"]["walk61.onnx"], rank_key=rows[n]["screen"]["rank_key"],
                 family=rows[n]["family"], gain_flag_col=(rows[n]["gain_flag"] or {}).get("column"),
                 on_mac_mini_with_equal_files=rows[n]["mac_mini_files_equal_macbook"]) for i, n in enumerate(chosen)]
    dep = [n for n, r in rows.items() if r["deployable"] and not r["is_reference"]]
    out = dict(
        stage="B1", written=time.strftime("%Y-%m-%dT%H:%M:%S"), flight_folder=str(FL), mac_mini_listing=mini_src,
        scored_saves=len(names), source="names with a file train/eval/gate_<name>_none_g400_walk.json",
        robot=dict(walk_mode_gain_kp_rl=KP_ROBOT, source=f"{STATE} facts.walking_policy",
                   policy_inputs=dict(zip(OBS_NAMES.split(","), OBS_WIDTHS)), gain_flag_value_in_walk_mode=GAIN_FLAG_ROBOT),
        counts=dict(scored=len(names), reference_row=sum(r["is_reference"] for r in rows.values()), deployable=len(dep),
                    not_deployable=sum(r["deployable"] is False for r in rows.values()),
                    checkpoint_file_missing=sum(r["deployable"] is None for r in rows.values()),
                    privileged_teachers=sum(bool(r["privileged_inputs"]) for r in rows.values()),
                    prewarm_copies=sum(bool(r["prewarm"]) for r in rows.values()),
                    deployable_with_gain_flag=sum(bool(rows[n]["gain_flag"]) for n in dep),
                    deployable_recurrent=sum(bool(rows[n]["recurrent"]) for n in dep),
                    screen_eligible=len(ranked), selected=len(chosen)),
        screen=dict(rule=f"deployable, and at most {SCREEN_MAX} falls inside the window (walk fell_at <= {WINDOW['walk']} s, stand <= "
                         f"{WINDOW['stand']} s) of 10 in each of {list(OLD_G400)}; at most {CAP} saves",
                    rank="fewest window falls summed over the four gain400 cells, then over the four nominal-gain cells "
                         f"{list(OLD_NOMINAL)}, then fewest whole-episode falls over all eight, then name",
                    eligible_in_rank_order=[n for _, n in ranked]),
        candidates=cand, frozen_candidates_in_script=frozen,
        frozen_list_equals_computed=[list(c) for c in CANDIDATES] == [[c["save"], c["sha256_16"]] for c in cand],
        reference=dict(save=REF, models="../../microduck_rl/cmu/whole/runtime-overlay/models", cells="no-pack cells only",
                       files_sha256_16=rows["walk61"]["files_sha256_16"] if "walk61" in rows else None),
        families=dict(sorted(fams.items())), saves=rows)
    (HERE / "out" / NAME).mkdir(parents=True, exist_ok=True)
    (HERE / "out" / NAME / "inventory.json").write_text(json.dumps(out, indent=1, default=str))
    print(f"{HERE / 'out' / NAME / 'inventory.json'}: {json.dumps(out['counts'])}")
    for k, f in out["families"].items():
        print(f"  {k:12s} {f['saves']:3d} saves, deployable {f['deployable']:2d}, inputs {f['input_sizes']}, recurrent {f['recurrent']}, "
              f"screen {f['screen_eligible']}, selected {f['selected']}")
    print("candidates: " + ", ".join(f"({c['save']!r}, {c['sha256_16']!r})" for c in cand))
    print(f"frozen list in this script equals the computed one: {out['frozen_list_equals_computed']}; Mac mini: {mini_src}")


# ------------------------------------------------------------------------------------------------ scoring (Mac mini)
def cell_specs():
    """cell -> load, manifest, case, condition, probe flags"""
    c = {}
    for load, man in LOADS.items():
        for cond, flags in COND.items():
            for case in CASES:
                c[f"{load}_{cond}_{case}"] = dict(load=load, manifest=str(HERE / "manifests" / man), case=case, cond=cond,
                                                  extra=([] if load == "none" else S0) + flags)
    return c


def check_models():
    """(save -> models dir, file hashes, what it reads and how it is fed, candidates whose files are not on this
    machine); refuses a candidate that is not the reviewed, deployable file before any episode runs. A candidate
    without files stops the scoring run (a verdict must not drop a candidate silently); the smoke names it and goes on."""
    saves, absent = {}, []
    rec = describe(OVERLAY / "models")
    assert rec["files"] == REF_SHA, f"the deployed pair is not the files B0 ran: {rec['files']}"
    facts, ok, reason = judge(rec)
    assert ok is True and not facts["recurrent"], reason
    saves[REF] = dict(models=str(OVERLAY / "models"), files=rec["files"], obs_set=None, reads=reason, facts=facts,
                      cells="no-pack cells only")
    for name, want in CANDIDATES:
        d = HERE / "ckpt" / name
        rec = describe(d)
        facts, ok, reason = judge(rec)
        if ok is None:
            assert SMOKE, (f"{name}: {reason} ({d}); copy the folder from the MacBook's train/ckpt/{name} to this machine "
                           "before the scoring run")
            absent.append(name)
            continue
        assert ok is True, f"{name}: not deployable: {reason}"
        assert rec["files"]["walk61.onnx"] == want and rec["files"]["stand61.onnx"] == want, \
            f"{name}: files {rec['files']} are not the reviewed {want}"
        col = facts["gain_flag_col"]
        assert col is None or 55 <= col < 61, f"{name}: gain flag column {col} is outside body_command"
        saves[name] = dict(models=str(d), files=rec["files"], obs_set=None if col is None else f"{col}:{GAIN_FLAG_ROBOT}",
                           reads=reason, facts=facts, cells="all")
    return saves, absent


def feed_record(s):
    f = s["facts"]
    return dict(
        inputs_0_to_54="built by the probe's Brain (microduck_rl/cmu/mac/walk_brain.py, the runtime's code): gyro 3, projected gravity 3, "
                       "joint positions 14, joint speeds 14, last action 14, command 3 (vx, vy, turn from the Brain's heading hold), head command 4",
        inputs_55_to_60="body_command: zeros, as the Brain writes them in walk mode",
        gain_flag=None if f["gain_flag_col"] is None else dict(
            column=f["gain_flag_col"], runtime_term=obs_term(f["gain_flag_col"]), value=GAIN_FLAG_ROBOT, in_conditions=list(COND),
            how=f"FLIGHT_OBS_SET={s['obs_set']} (turns flight_eval's own feed of KP_RL / 200 - 1 off and writes the column on every call)",
            why=f"the robot's walk mode runs KP_RL {KP_ROBOT} whatever the simulated condition is; gain scale 1.0 - 1 = {GAIN_FLAG_ROBOT}",
            asserted_per_episode="obs_set_calls > 0 and no gain_flag_calls in the episode's counters"),
        recurrent_state=None if not f["recurrent"] else dict(
            input=f["state"]["input"], shape=f["state"]["shape"], core=f["state"]["core"],
            how="zeros on entry (first call, or more than 5 control ticks without a call), then state_out fed back; one state for "
                "the stand and walk slots (one file); flight_eval._StatefulSession = the runtime's Brain.run_policy rule"),
        privileged_values="none (priv_first is asserted None in every episode)",
        loader_switches="none: every FLIGHT_* variable is removed in the worker before the episode; no prewarm file in the folder",
        walk_mode_gain="walk_brain.KP_RL is put back to the robot's value before every episode and asserted after it "
                       f"({KP['nominal']} in nominal, {KP['gain400']} in gain400)")


def one(job):
    label, models, manifest, case, extra, obs_set, kp_expect, seed = job
    for k in [k for k in os.environ if k.startswith(("FLIGHT_", "SPK3DIAG_"))]:
        os.environ.pop(k)  # no diagnostic switch of flight_eval is on in a verdict episode
    if obs_set:
        os.environ["FLIGHT_OBS_SET"] = obs_set
    import flight_eval as fe
    wb = sys.modules.get("walk_brain")  # None in a fresh worker; in a reused one it keeps the last episode's --kp-rl
    kp_found = None if wb is None else int(wb.KP_RL)
    if wb is not None:
        wb.KP_RL = KP_ROBOT
    t0 = time.time()
    r = fe.episode((models, manifest, case, seed, 0.0, 8.0, False, extra))
    kp = int(sys.modules["walk_brain"].KP_RL)
    ds = r.get("diag_stat") or {}
    assert kp == kp_expect, f"{label} seed {seed}: the episode ran at walk gain {kp}, not {kp_expect}"
    assert r.get("priv_first") is None, f"{label}: a privileged input was read"
    assert not any(k in ds for k in ("gain_flag_calls", "pack_flag_calls", "prewarm_steps", "warm_state_loaded")), f"{label}: {ds}"
    assert (ds.get("obs_set_calls", 0) > 0) == bool(obs_set), f"{label}: FLIGHT_OBS_SET {obs_set!r} against counters {ds}"
    out = {k: r.get(k) for k in ("seed", "fell_at", "fall_dir", "max_tilt", "speed", "dist_x", "action_jumps")}
    out.update(kp_rl=kp, kp_rl_found_on_entry=kp_found, obs_set_calls=ds.get("obs_set_calls"), secs=round(time.time() - t0, 2))
    return label, out


def wilson(k, n):
    z = 1.96
    p = k / n
    mid, half = (p + z * z / (2 * n)) / (1 + z * z / n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, mid - half), 3), round(min(1.0, mid + half), 3)]


def summarise(label, eps):
    """as b0_yardstick.summarise, plus the mean speed over all episodes and the gain the episodes ran at"""
    case = label.rsplit("_", 1)[1]
    eps = sorted(eps, key=lambda e: e["seed"])
    falls = sorted(e["fell_at"] for e in eps if e["fell_at"] is not None)
    inwin = [e["fell_at"] is not None and e["fell_at"] <= WINDOW[case] for e in eps]
    per = sorted(round(e["action_jumps"] / max(e["fell_at"] if e["fell_at"] is not None else 20.0, 0.5) * 10, 1) for e in eps)
    sp = [e["speed"] for e in eps if e["speed"] is not None and e["fell_at"] is None]
    sp_all = [e["speed"] for e in eps if e["speed"] is not None]
    blocks = [sum(inwin[i:i + BLOCK]) for i in range(0, len(inwin), BLOCK)]
    return dict(cell=label, seeds=len(eps), seed0=eps[0]["seed"], window_s=WINDOW[case], falls_in_window=sum(inwin),
                falls_whole_episode=len(falls), fall_times=falls, falls_in_window_per_block_of_10=blocks,
                falls_in_window_wilson95=wilson(sum(inwin), len(eps)), jumps_per_10s_median=per[len(per) // 2],
                jumps_per_10s_quartiles=[per[len(per) // 4], per[(3 * len(per)) // 4]],
                speed_mean_upright=round(sum(sp) / len(sp), 4) if sp else None,
                speed_mean_all_episodes=round(sum(sp_all) / len(sp_all), 4) if sp_all else None,
                max_tilt=max((e["max_tilt"] for e in eps if e["max_tilt"] is not None), default=None),
                kp_rl=sorted({e["kp_rl"] for e in eps}), episodes_entered_with_another_gain=sum(
                    e["kp_rl_found_on_entry"] not in (None, KP_ROBOT) for e in eps),
                obs_set_calls_min=min((e["obs_set_calls"] for e in eps if e["obs_set_calls"] is not None), default=None),
                episode_secs_mean=round(sum(e["secs"] for e in eps) / len(eps), 2))


def jump_limit(ref_median):
    return round(max(1.5 * ref_median, ref_median + 2.0), 2)


def verdict(summ, saves, C):
    """per save: the stage's three lines; True / False only when the cells that decide it are there"""
    ref = {case: summ.get(f"{REF}__none_nominal_{case}") for case in CASES}
    out = {}
    for save in saves:
        if save == REF:
            continue
        got = {c: summ.get(f"{save}__{c}") for c in C}
        missing = [c for c, v in got.items() if v is None]
        fall_fail = {c: v["falls_in_window"] for c, v in got.items() if v and v["falls_in_window"] > FALL_MAX}
        speed = dict(cell="none_nominal_walk", value=None, walk61=None, need=None, ok=None)
        if got["none_nominal_walk"] and ref["walk"]:
            v, r = got["none_nominal_walk"]["speed_mean_upright"], ref["walk"]["speed_mean_upright"]
            need = None if r is None else round(SPEED_FRACTION * r, 4)
            speed.update(value=v, walk61=r, need=need, ok=None if need is None else (v is not None and v >= need))
        jumps, jump_fail = {}, []
        for c, spec in C.items():
            if spec["cond"] != "nominal" or got[c] is None or ref[spec["case"]] is None:
                continue
            lim = jump_limit(ref[spec["case"]]["jumps_per_10s_median"])
            jumps[c] = dict(median=got[c]["jumps_per_10s_median"], limit=lim, walk61_cell=f"none_nominal_{spec['case']}",
                            ok=got[c]["jumps_per_10s_median"] <= lim)
            if not jumps[c]["ok"]:
                jump_fail.append(c)
        need_jumps = [c for c, spec in C.items() if spec["cond"] == "nominal"]
        failed = bool(fall_fail) or speed["ok"] is False or bool(jump_fail)
        complete = not missing and speed["ok"] is not None and all(c in jumps for c in need_jumps)
        out[save] = dict(passes=False if failed else (True if complete else None), complete=complete, cells_missing=missing,
                         cells_over_the_fall_line=fall_fail, speed_line=speed, jumps_line=jumps, cells_over_the_jump_line=jump_fail,
                         jumps_ok_in_the_no_pack_nominal_cells_only=None if not all(f"none_nominal_{k}" in jumps for k in CASES)
                         else all(jumps[f"none_nominal_{k}"]["ok"] for k in CASES),
                         worst_cell=max(((v["falls_in_window"], c) for c, v in got.items() if v), default=None))
    return out


def main():
    assert not (SMOKE and set(range(SEED0, SEED0 + SEEDS)) & set(range(VERDICT_SEED0, VERDICT_SEED0 + VERDICT_SEEDS))), \
        "the smoke must not touch the verdict seeds 2000 to 2059"
    assert CANDIDATES, "CANDIDATES is empty: run inventory=1 and freeze the list first"
    OUT.mkdir(parents=True, exist_ok=True)
    (saves, absent), C = check_models(), cell_specs()
    for spec in C.values():
        assert Path(spec["manifest"]).is_file(), spec["manifest"]
    if SMOKE:
        plan = [(REF, c) for c in ("none_gain400_stand", "none_nominal_stand", "none_nominal_walk")]
        plan += [(s, "none_nominal_walk") for s in saves if s != REF]
    else:
        plan = [(s, c) for s in saves for c, spec in C.items() if s != REF or spec["load"] == "none"]
    plan = [(f"{s}__{c}", s, c) for s, c in plan if "only" not in opts or opts["only"] in f"{s}__{c}"]
    summ, todo = {}, []
    for label, s, c in plan:  # resume: a cell whose file is complete is kept (never in the smoke)
        try:
            old = json.loads((OUT / f"{label}.json").read_text())
            if not SMOKE and sorted(e["seed"] for e in old["episodes"]) == list(range(SEED0, SEED0 + SEEDS)):
                summ[label] = old["summary"]
                continue
        except (OSError, ValueError, KeyError, IndexError):
            pass
        todo.append((label, s, c))
    hb(f"START pid {os.getpid()}: {len(todo)} cells x {SEEDS} seeds from {SEED0} ({len(summ)} kept from files), {WORKERS} workers; "
       f"robot walk gain {KP_ROBOT}; model files " + json.dumps({s: v['files']['walk61.onnx'] for s, v in saves.items()})
       + "; gain flag fed " + json.dumps({s: v['obs_set'] for s, v in saves.items() if v['obs_set']})
       + (f"; NOT ON THIS MACHINE, not run: {absent}" if absent else ""))
    jobs = [(label, saves[s]["models"], C[c]["manifest"], C[c]["case"], C[c]["extra"], saves[s]["obs_set"], KP[C[c]["cond"]], seed)
            for label, s, c in todo for seed in range(SEED0, SEED0 + SEEDS)]
    got = {label: [] for label, _, _ in todo}
    t_start = time.time()

    def write():
        v = verdict(summ, saves, C)
        full = (not SMOKE and "only" not in opts and SEED0 == VERDICT_SEED0 and SEEDS == VERDICT_SEEDS
                and all(x["complete"] for x in v.values()) and len(v) == len(CANDIDATES))
        (OUT / "summary.json").write_text(json.dumps(dict(
            stage="B1", smoke=SMOKE, seeds=dict(seed0=SEED0, count=SEEDS), only=opts.get("only"),
            rule=dict(max_falls_in_window=FALL_MAX, windows_s=WINDOW, speed="nominal no-pack walking speed (mean over upright episodes) "
                      f"at least {SPEED_FRACTION} x the deployed walk61's in this run",
                      jumps="median jumps per 10 s at most max(1.5 x walk61, walk61 + 2) in the nominal-condition cells; a payload cell "
                            "is held to walk61's no-pack nominal cell of the same case"),
            conditions={k: dict(flags=f, walk_mode_gain=KP[k]) for k, f in COND.items()},
            cells={c: dict(manifest=Path(s["manifest"]).name, case=s["case"], condition=s["cond"], flags=s["extra"]) for c, s in C.items()},
            saves={s: dict(models=v_["models"], files_sha256_16=v_["files"], reads=v_["reads"], cells=v_["cells"], fed=feed_record(v_))
                   for s, v_ in saves.items()},
            results=summ, verdict=v,
            stage_verdict=dict(valid_for_the_stage=full, any_save_passes=any(x["passes"] for x in v.values()) if full else None,
                               passing_saves=[s for s, x in v.items() if x["passes"]] if full else None)), indent=1, default=str))
        return v

    with ProcessPoolExecutor(WORKERS) as ex:
        for label, r in ex.map(one, jobs):
            got[label].append(r)
            if len(got[label]) < SEEDS:
                continue
            s = summarise(label, got[label])
            summ[label] = s
            (OUT / f"{label}.json").write_text(json.dumps(dict(summary=s, episodes=got[label]), indent=1, default=str))
            write()
            hb(f"{label}: window falls {s['falls_in_window']} of {SEEDS} (blocks of 10: {s['falls_in_window_per_block_of_10']}, "
               f"95 % {s['falls_in_window_wilson95']}); whole episode {s['falls_whole_episode']}; jumps/10 s median "
               f"{s['jumps_per_10s_median']} quartiles {s['jumps_per_10s_quartiles']}; speed {s['speed_mean_upright']}; walk gain "
               f"{s['kp_rl']}; obs_set calls {s['obs_set_calls_min']}")
    v = write()
    wall = time.time() - t_start
    if SMOKE:
        return smoke_report(saves, absent, plan, summ, got, wall, C)
    for save, x in v.items():
        hb(f"VERDICT {save}: passes {x['passes']}; cells over {FALL_MAX} window falls {x['cells_over_the_fall_line']}; speed "
           f"{x['speed_line']['value']} against {x['speed_line']['need']} ok {x['speed_line']['ok']}; cells over the jump line "
           f"{x['cells_over_the_jump_line']}; missing {len(x['cells_missing'])}")
    hb("DONE")


def smoke_report(saves, absent, plan, summ, got, wall, C):
    """the feed check, printed: every save loaded and stepped, the reference stood, and what each was fed"""
    bad, secs = [], []
    for name in absent:
        print(f"{name}: NOT ON THIS MACHINE ({HERE / 'ckpt' / name}): not loaded, not run")
    for label, eps in got.items():
        save, cell = label.split("__")
        s = saves[save]
        f = s["facts"]
        print(f"{label}: file {s['files']['walk61.onnx']}, {s['reads']}")
        for e in sorted(eps, key=lambda e: e["seed"]):
            ran = e["fell_at"] if e["fell_at"] is not None else 20.0
            secs.append(e["secs"])
            print(f"    seed {e['seed']}: ran {ran} s, fell_at {e['fell_at']}, moved {e['dist_x']} m, speed {e['speed']}, jumps "
                  f"{e['action_jumps']}, walk gain {e['kp_rl']} (worker held {e['kp_rl_found_on_entry']} on entry), obs_set calls "
                  f"{e['obs_set_calls']}" + ("" if f["gain_flag_col"] is None else f" writing column {s['obs_set']}") + f", {e['secs']} s")
            if e["fell_at"] is not None:
                bad.append(f"{label} seed {e['seed']} fell at {e['fell_at']} s")
    ref_stand = {c: summ.get(f"{REF}__none_{c}_stand") for c in COND if any(p[0] == f"{REF}__none_{c}_stand" for p in plan)}
    stood = bool(ref_stand) and all(x is not None and x["falls_whole_episode"] == 0 for x in ref_stand.values())
    reset = sum(e["kp_rl_found_on_entry"] not in (None, KP_ROBOT) for eps in got.values() for e in eps)
    full_eps = (len(CANDIDATES) * len(C) + sum(spec["load"] == "none" for spec in C.values())) * VERDICT_SEEDS
    mean = sum(secs) / len(secs)
    ran = len(got) == len(plan) and all(len(eps) == SEEDS for eps in got.values())
    print(f"reference pair standing without a fall in {list(ref_stand)}: {stood if ref_stand else 'not in this run'}")
    print(f"episodes that entered a worker holding another gain and were put back to {KP_ROBOT}: {reset}")
    print(f"falls in the smoke: {bad or 'none'}")
    print(f"timing: {len(secs)} episodes, mean {mean:.2f} s each with {WORKERS} workers, wall {wall:.0f} s; the full job is "
          f"{full_eps} episodes: about {full_eps * mean / WORKERS / 60:.0f} min at this rate")
    # OK = every planned cell ran through the feed assertions, the reference stood where it was run, no candidate is absent
    ok = ran and (stood or not ref_stand) and not absent
    line = (f"SMOKE {'OK' if ok else 'NOT OK'}: {len(got)} of {len(plan)} cells x {SEEDS} ran; reference stood "
            f"{stood if ref_stand else 'not run'}; candidates not on this machine {absent or 'none'}; falls {bad or 'none'}; "
            f"gain put back in {reset} episodes; mean {mean:.2f} s per episode; full job about {full_eps * mean / WORKERS / 60:.0f} min")
    hb(line)
    hb("DONE" if ok else "FAILED smoke: see the line above")
    print(line)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    if INVENTORY:
        inventory()
    else:
        try:
            main()
        except Exception as e:
            hb(f"FAILED {type(e).__name__}: {e}")
            raise
