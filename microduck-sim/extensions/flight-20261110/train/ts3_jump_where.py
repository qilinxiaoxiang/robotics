"""Round 3 diagnostic: where the action jumps of a policy happen in a gate walk episode.

  $PY train/ts3_jump_where.py <dir under ckpt> <manifest name> <vx,vx,...> [probe flags ...]
  e.g.  $PY train/ts3_jump_where.py t3h_750 nominal 0.25,0.15,0.10 --stand-s 0

One walking episode per commanded speed, seed 0, through flight_eval.episode (the gate's own code path) with the
probe's tick log and tick diagnostics on. A jump is the gate's own measure: a tick whose action differs from the
previous tick's by more than 0.5 rad on any joint. For every jump the script records the time, which joints moved
more than 0.5 rad, and what the feet did around it (floor force of both feet two ticks before and at the jump), then
prints per speed: jumps, the joints that jump, how many jumps fall within 60 ms after a foot touches down or within
60 ms before a foot lifts, and the time histogram. Mac mini only (mini.sh run). Writes eval/jump_where_<dir>.json.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flight_eval as fe  # noqa: E402

LOADED_N = 0.5  # a foot counts as on the floor at or above this floor force
BRAIN_DEFAULT = {}


def default_pose(d):
    """joint -> default angle from the policy file's metadata (the runtime's goal is default + action)"""
    import onnxruntime as ort
    p = HERE / "ckpt" / d / "walk61.onnx"
    if d == "walk61":  # the deployed policy
        p = HERE / "../../../microduck_rl/cmu/whole/runtime-overlay/models/walk61.onnx"
    meta = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"]).get_modelmeta().custom_metadata_map
    if "joint_names" not in meta:  # a save without metadata: the family shares the deployed walk61's default pose
        p = HERE / "../../../microduck_rl/cmu/whole/runtime-overlay/models/walk61.onnx"
        meta = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"]).get_modelmeta().custom_metadata_map
    return dict(zip(meta["joint_names"].split(","), [float(v) for v in meta["default_joint_pos"].split(",")]))


def run(d, man, vx, extra):
    log = f"/tmp/ts3_jump_{d}_{vx}.jsonl"
    # TS3_KIND=stand: the gate's standing episode instead of the walk (the speed argument is then not passed);
    # TS3_SEED=<n>: another seed
    kind = os.environ.get("TS3_KIND", "walk")
    mdir = (HERE / "../../../microduck_rl/cmu/whole/runtime-overlay/models").resolve() if d == "walk61" else HERE / "ckpt" / d
    r = fe.episode((str(mdir), str(HERE / f"manifests/flightpack-{man}.json"), kind,
                    int(os.environ.get("TS3_SEED", 0)), 0.0, 8.0, False,
                    list(extra) + (["--vx", str(vx)] if kind == "walk" else []) + ["--tick-log", log, "--tick-diag"]))
    rows = [json.loads(x) for x in open(log)]
    os.remove(log)
    return r, rows


def analyse(rows, names):
    acts = [(x["t"], x["action"], x.get("diag")) for x in rows if x.get("action") is not None]
    # touch-down and lift-off times of each foot
    events = []
    for side in ("left", "right"):
        prev = None
        for t, _, dg in acts:
            if not dg or side not in dg:
                continue
            on = dg[side]["fn"] >= LOADED_N
            if prev is not None and on != prev:
                events.append((t, side, "down" if on else "up"))
            prev = on
    jumps, joints, near = [], Counter(), Counter()
    for i in range(1, len(acts)):
        t, a, dg = acts[i]
        dlt = [abs(x - y) for x, y in zip(a, acts[i - 1][1])]
        if max(dlt) <= 0.5:
            continue
        who = [names[k] if k < len(names) else str(k) for k, v in enumerate(dlt) if v > 0.5]
        joints.update(who)
        moves = {names[k]: [round(acts[i - 1][1][k], 3), round(a[k], 3)] for k, v in enumerate(dlt) if v > 0.5}
        after_down = [e for e in events if e[2] == "down" and 0.0 <= t - e[0] <= 0.06]
        before_up = [e for e in events if e[2] == "up" and 0.0 <= e[0] - t <= 0.06]
        tag = "after_touch_down" if after_down else ("before_lift_off" if before_up else "mid_stance_or_swing")
        near[tag] += 1
        jumps.append(dict(t=t, joints=who, size=round(max(dlt), 3), phase=tag, action_from_to=moves,
                          feet_n=None if not dg else [dg["left"]["fn"], dg["right"]["fn"]]))
    steps = sum(1 for e in events if e[2] == "down")
    # per joint over the walking part (t >= 2.5 s): the action's range and mean |tick-to-tick change|, and the share of
    # ticks whose servo goal (default + action) lies outside the runtime's joint range, where clamp_goal cuts it
    wb = sys.modules.get("walk_brain")
    walk = [a for t, a, _ in acts if t >= 2.5]
    per = {}
    for k, n in enumerate(names):
        col = [a[k] for a in walk]
        if not col:
            continue
        d1 = [abs(x - y) for x, y in zip(col[1:], col[:-1])]
        lo, hi = wb.JOINT_RANGE.get(n, (-9, 9))
        dflt = BRAIN_DEFAULT.get(n, 0.0)
        per[n] = dict(min=round(min(col), 2), max=round(max(col), 2), mean_step=round(sum(d1) / max(len(d1), 1), 3),
                      max_step=round(max(d1), 2) if d1 else 0.0,
                      clamped=round(sum(1 for v in col if dflt + v < lo or dflt + v > hi) / len(col), 3))
    return dict(ticks=len(acts), jumps=len(jumps), joints=dict(joints), phase=dict(near), touch_downs=steps, per_joint=per,
                per_second=dict(sorted(Counter(int(j["t"]) for j in jumps).items())), detail=jumps)


def check_order(rows, names, wb):
    """Index check before any joint is named (2026-11-20, after the NAMES mislabel): a knee action moves the knee.
    The logged action (policy order `names`) of each knee must track that knee's own logged position (rows' "q", servo
    order wb.NAMES, minus the default pose) a few ticks later better than any other joint's position."""
    import numpy as np
    rr = [x for x in rows if x.get("action") is not None and x.get("q")]
    # steady walking only: while standing and in the stand -> walk change both knees move together, which hides the side
    tw = next((x["t"] for x in rr if x.get("policy") == "walk"), None)
    if tw is not None and sum(1 for x in rr if x["t"] >= tw + 1.0) > 100:
        rr = [x for x in rr if x["t"] >= tw + 1.0]
    assert len(rr) > 100, f"only {len(rr)} tick rows carry both an action and joint positions"
    A = np.array([x["action"] for x in rr])
    Q = np.array([x["q"] for x in rr])
    said = []
    for name in ("left_knee", "right_knee"):
        k = names.index(name)
        best = None
        for lag in range(1, 9):  # the servo answers a few ticks late; take the lag at which the best joint is clearest
            cc = [float(np.corrcoef(A[:-lag, k], Q[lag:, j])[0, 1]) if Q[:, j].std() > 1e-6 else 0.0
                  for j in range(Q.shape[1])]
            if best is None or max(cc) > max(best[1]):
                best = (lag, cc)
        lag, cc = best
        j = int(np.argmax(cc))
        assert wb.NAMES[j] == name and cc[j] > 0.6, (name, wb.NAMES[j], lag, [round(c, 2) for c in cc])
        said.append(f"{name} action tracks {name} position {lag} ticks later (corr {cc[j]:.2f}, the largest of {Q.shape[1]})")
    print("[order] assertion ran: " + "; ".join(said), flush=True)


def main():
    d, man, vxs, extra = sys.argv[1], sys.argv[2], sys.argv[3].split(","), sys.argv[4:]
    out = {}
    # the index check runs on the deployed walk61 without the pack, through the same log path: the joint order is a
    # property of the code, and a policy that chatters (the t3g students) does not move its knees in step with its
    # actions, so the check cannot be made on the policy under study
    ref_log = "/tmp/ts3_jump_ordercheck.jsonl"
    fe.episode((str((HERE / "../../../microduck_rl/cmu/whole/runtime-overlay/models").resolve()),
                str(HERE / "manifests/flightpack-none.json"), "walk", 0, 0.0, 8.0, False,
                ["--tick-log", ref_log, "--tick-diag"]))
    ref_rows = [json.loads(x) for x in open(ref_log)]
    os.remove(ref_log)
    check_order(ref_rows, list(sys.modules["walk_brain"].OBSERVATION_DOF_ORDER), sys.modules["walk_brain"])
    for vx in vxs:
        r, rows = run(d, man, float(vx), extra)
        wb = sys.modules.get("walk_brain")
        # the logged action is in the policy's joint order (walk_brain.OBSERVATION_DOF_ORDER), NOT in servo-ID order
        # (walk_brain.NAMES): the first version of this script labelled with NAMES and named the wrong joints
        names = list(wb.OBSERVATION_DOF_ORDER)
        BRAIN_DEFAULT.update(default_pose(d))
        a = analyse(rows, names)
        a.update(fell_at=r["fell_at"], speed=r["speed"], gate_action_jumps=r["action_jumps"], max_tilt=r["max_tilt"])
        out[vx] = a
        print(json.dumps(dict(vx=vx, **{k: v for k, v in a.items() if k not in ("detail", "per_joint")})))
        for n, v in a["per_joint"].items():
            print("  J", n, json.dumps(v))
        for j in a["detail"][:8]:
            print("   ", json.dumps(j))
    (HERE / "eval").mkdir(exist_ok=True)
    tag = man + ("_g400" if "400" in extra else "")
    (HERE / "eval" / f"jump_where_{d}_{tag}.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
