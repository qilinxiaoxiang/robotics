"""Chatter gates (round 3, 2026-11-19): the checks that would have stopped s2r6_4 before the robot. s2r6_4 stood and
walked in every simulated cell and fell on the robot in 4.4 s at standstill with 172 action jumps per 10 s
(docs/PET_ROBOT_LOG.md 2026-11-19 16:00, 16:40, 17:40). A candidate that fails any line here does not go to
acceptance or to a robot checklist.

  python3 train/ts3_gates.py spec <tag> <dir under ckpt> [...]   -> train/eval/spec_gate_<tag>.json (missing cells only)
  modal run train/flight_eval_modal.py --spec train/eval/spec_gate_<tag>.json
  <python with numpy + onnxruntime> train/ts3_gates.py score <dir> [...]   -> train/out/gates/gates_<dir>.json,
                                                                              PASS / FAIL lines, exit 1 on any FAIL

Lines (reference = the deployed walk61 run by the same code in the same cell; SEEDS seeds; "jumps" = tick-to-tick
action jumps over 0.5 rad per 10 s of upright time, median over the seeds):
  G1  action distance from walk61 on walk61's own robot walks at most 0.25 rad (the t2b gate:
      guide/firmware/mac/robot-runs-20261030-t1/action_distance.py; the log is copied to train/gates/, 649 states).
      A recurrent policy runs the walks in order with its state carried, zeroed at every gap over 0.12 s.
  G2  no pack, simulation as it is: standstill and walking: falls no more than walk61, jumps at most
      max(1.5 x walk61, walk61 + 2).
  G3  no pack, matched cell gain400 (--kp-rl 400; the condition under which s2r6_4 falls at standstill 7 of 10 and
      walk61 0 of 10): standstill and walking: same two limits against walk61 in that cell.
  G4  nominal pack, simulation as it is: 0 falls; jumps within the G2 limits (walk61 cannot carry the pack, so its
      no-pack numbers are the level).
  G5  nominal pack, gain400: falls no more than walk61's no-pack gain400 cells; jumps within the G3 limits.
A privileged teacher (68 inputs) has no G1 (its extra inputs are not in a robot log); the line reads MISSING and the
verdict of a teacher rests on G2 to G5 (--teacher).
"""
import json
import os
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
WALK61 = "../../../microduck_rl/cmu/whole/runtime-overlay/models"
SEEDS = int(os.environ.get("GATE_SEEDS", 10))
G400 = ["--kp-rl", "400"]
S0 = ["--stand-s", "0"]
# cell: (manifest, case, probe flags); the reference runs the four no-pack cells
CELLS = {
    "none_stand": ("none", "stand", []), "none_walk": ("none", "walk", []),
    "none_g400_stand": ("none", "stand", G400), "none_g400_walk": ("none", "walk", G400),
    "pack_stand": ("nominal", "stand", S0), "pack_walk": ("nominal", "walk", S0),
    "pack_g400_stand": ("nominal", "stand", S0 + G400), "pack_g400_walk": ("nominal", "walk", S0 + G400),
}
REF_CELLS = [c for c in CELLS if c.startswith("none")]
LEVEL = {"pack_stand": "none_stand", "pack_walk": "none_walk", "pack_g400_stand": "none_g400_stand",
         "pack_g400_walk": "none_g400_walk"}
DIST_GATE = 0.25
LOG = TRAIN / "gates/walk61_see_walks.jsonl"
NAMES = ['right_ankle', 'right_knee', 'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw', 'left_ankle', 'left_knee',
         'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw', 'head_pitch', 'neck_pitch', 'head_yaw', 'head_roll']
HEAD_JOINTS, HEAD_RANGE, HEAD_ALPHA = ("neck_pitch", "head_pitch", "head_yaw", "head_roll"), (1.10, 1.10, 1.40, 0.31), 0.2


def ename(d, cell):
    return f"gate_{d}_{cell}"


def read(d, cell):
    p = TRAIN / f"eval/{ename(d, cell)}.json"
    if not p.exists():
        return None
    eps = json.loads(p.read_text())["episodes"]
    if len(eps) < SEEDS:
        return None
    per = sorted(round(e["action_jumps"] / max(e["fell_at"] if e["fell_at"] is not None else 20.0, 0.5) * 10, 1) for e in eps)
    med = per[len(per) // 2] if len(per) % 2 else round((per[len(per) // 2 - 1] + per[len(per) // 2]) / 2, 2)
    return dict(episodes=len(eps), falls=sum(e["fell_at"] is not None for e in eps),
                fall_times=sorted(e["fell_at"] for e in eps if e["fell_at"] is not None), jumps_per_10s=per, jumps_median=med)


def rebuild(ref_order, ref_default):
    """The 61 inputs of every logged walk61 tick, as robot-runs-20261030-t1/sensitivity.rebuild, plus a flag that
    starts a new segment (first state, or more than 0.12 s since the previous walking tick)."""
    import numpy as np
    rows = []
    for line in open(LOG, errors="ignore"):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    out, new, last, head, t_prev = [], [], None, np.zeros(4), None
    for r in rows:
        if r.get("mode") != "walk" or not r.get("q") or not r.get("gb"):
            continue
        cmd = r.get("cmd") or {}
        want_head = cmd.get("head") or {}
        target = np.zeros(4)
        for k, n in enumerate(HEAD_JOINTS):
            if want_head.get(n) is not None:
                target[k] = float(np.clip(float(want_head[n]) - ref_default[n], -HEAD_RANGE[k], HEAD_RANGE[k]))
        head = head + HEAD_ALPHA * (target - head)
        if r.get("policy") == "walk" and r.get("action") and last is not None:
            q, dq = dict(zip(NAMES, r["q"])), dict(zip(NAMES, r["dq"]))
            out.append(list(r["gyro_body"]) + list(r["gb"]) + [q[n] - ref_default[n] for n in ref_order]
                       + [dq[n] for n in ref_order] + list(last)
                       + [float(cmd.get("vx") or 0), float(cmd.get("vy") or 0), float(r.get("turn") or 0)]
                       + list(head) + [0.0] * 6)
            new.append(t_prev is None or r["t"] - t_prev > 0.12)
            t_prev = r["t"]
        if r.get("action"):
            last = r["action"]
    return np.array(out, dtype=np.float32), new


def distance(d):
    """G1: mean over the logged walk61 states of |candidate action - walk61 action| (14-joint norm), rad."""
    import numpy as np
    import onnxruntime as ort
    ref = ort.InferenceSession(str(TRAIN / WALK61 / "walk61.onnx"), providers=["CPUExecutionProvider"])
    cand = ort.InferenceSession(str(TRAIN / f"ckpt/{d}/walk61.onnx"), providers=["CPUExecutionProvider"])
    meta = ref.get_modelmeta().custom_metadata_map
    order = meta["joint_names"].split(",")
    default = dict(zip(order, [float(v) for v in meta["default_joint_pos"].split(",")]))
    cm = cand.get_modelmeta().custom_metadata_map
    assert cm["joint_names"] == meta["joint_names"] and cm["default_joint_pos"] == meta["default_joint_pos"], d
    ins = cand.get_inputs()
    if tuple(ins[0].shape) != (1, 61):
        return None  # a privileged teacher
    X, new = rebuild(order, default)
    base = np.stack([ref.run(None, {ref.get_inputs()[0].name: x[None]})[0][0] for x in X])
    acts, st = [], None
    for x, n in zip(X, new):
        feed = {ins[0].name: x[None]}
        if len(ins) > 1:
            if st is None or n:
                st = np.zeros(tuple(ins[1].shape), np.float32)
            feed[ins[1].name] = st
        res = cand.run(None, feed)
        if len(ins) > 1:
            st = res[1]
        acts.append(res[0][0])
    diff = np.array(acts) - base
    return dict(states=len(X), segments=int(sum(new)), distance=round(float(np.linalg.norm(diff, axis=1).mean()), 3),
                walk61_action_norm=round(float(np.linalg.norm(base, axis=1).mean()), 3),
                per_joint={j: round(float(np.abs(diff[:, k]).mean()), 3) for k, j in enumerate(order)})


def limit(ref_median):
    return round(max(1.5 * ref_median, ref_median + 2.0), 2)


def score(d, teacher=False):
    lines, ref = [], {c: read("walk61", c) for c in REF_CELLS}

    def add(name, ok, detail):
        lines.append(dict(line=name, result="MISSING" if ok is None else ("PASS" if ok else "FAIL"), detail=detail))

    dist = None if teacher else distance(d)
    if dist is None:
        add("G1 action distance from walk61 on its robot walks", None, "privileged teacher: not computable from a robot log")
    else:
        add("G1 action distance from walk61 on its robot walks", dist["distance"] <= DIST_GATE,
            f"{dist['distance']} rad against {DIST_GATE} ({dist['states']} states, {dist['segments']} segments)")
    for cell in CELLS:
        lvl = LEVEL.get(cell, cell)
        c, r = read(d, cell), ref[lvl]
        grp = {"none_stand": "G2", "none_walk": "G2", "none_g400_stand": "G3", "none_g400_walk": "G3", "pack_stand": "G4",
               "pack_walk": "G4"}.get(cell, "G5")
        if c is None or r is None:
            add(f"{grp} {cell}", None, "cell or its walk61 reference not run")
            continue
        fall_max = 0 if grp == "G4" else r["falls"]
        lim = limit(r["jumps_median"])
        add(f"{grp} {cell} falls", c["falls"] <= fall_max,
            f"{c['falls']} of {c['episodes']} at {c['fall_times']} against at most {fall_max} (walk61 {lvl}: {r['falls']})")
        add(f"{grp} {cell} jumps per 10 s", c["jumps_median"] <= lim,
            f"median {c['jumps_median']} (range {c['jumps_per_10s'][0]} to {c['jumps_per_10s'][-1]}) against at most {lim} "
            f"(walk61 {lvl}: median {r['jumps_median']})")
    fails = [x for x in lines if x["result"] == "FAIL"]
    missing = [x for x in lines if x["result"] == "MISSING" and not (teacher and x["line"].startswith("G1"))]
    out = dict(models=d, seeds=SEEDS, verdict="PASS" if not fails and not missing else "FAIL", failed_lines=len(fails),
               missing_lines=len(missing), lines=lines, distance=dist,
               cells={c: read(d, c) for c in CELLS}, walk61={c: ref[c] for c in REF_CELLS})
    (TRAIN / "out/gates").mkdir(parents=True, exist_ok=True)
    (TRAIN / f"out/gates/gates_{d}.json").write_text(json.dumps(out, indent=1))
    for x in lines:
        print(f"{x['result']:7s} {d}: {x['line']}: {x['detail']}")
    print(f"gates {d}: verdict {out['verdict']}, {len(fails)} failed lines, {len(missing)} missing")
    return out["verdict"] == "PASS"


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "spec":
        tag, dirs = sys.argv[2], sys.argv[3:]
        evals = []
        for d in ["walk61"] + dirs:
            for cell, (man, case, flags) in CELLS.items():
                if d == "walk61" and cell not in REF_CELLS:
                    continue
                if read(d, cell) is None:
                    evals.append(dict(name=ename(d, cell), models=WALK61 if d == "walk61" else f"ckpt/{d}",
                                      manifest=f"manifests/flightpack-{man}.json", case=case, episodes=SEEDS, extra=flags))
        out = TRAIN / f"eval/spec_gate_{tag}.json"
        out.write_text(json.dumps(dict(evals=evals), indent=1))
        print(f"{out}: {len(evals)} evals, {sum(e['episodes'] for e in evals)} episodes")
    elif mode == "score":
        args = [a for a in sys.argv[2:] if a != "--teacher"]
        ok = [score(d, teacher="--teacher" in sys.argv) for d in args]
        sys.exit(0 if all(ok) else 1)
