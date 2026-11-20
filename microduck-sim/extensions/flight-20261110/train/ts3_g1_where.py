"""Round 3 diagnosis: where does a student's G1 distance come from? (G1 = ts3_gates.distance: mean 14-joint norm of
candidate action minus walk61 action on the 649 logged walk61 robot states, 5 segments.)

  $PY train/ts3_g1_where.py <student dir> <teacher dir> [<student dir> <teacher dir> ...]
  PY = /Users/xiangzheng/.venvs/microduck-walk/bin/python ; seconds on the MacBook (ONNX on 649 logged states).

On the same robot states it computes walk61 (W), the student (S, recurrent state zeroed at each segment start as the
gate does) and the student's own teacher (T) with its privileged inputs set to the robot's case: payload 0 and the
no-pack trunk COM (flight_eval.NOPACK_PRIV), body velocity not in the log so three assumptions (0, walk61's measured
0.09 m/s forward, the 0.25 command... the logged command), gain scale 1.0 and 2.0 (69-input teachers; 2.0 = the
gain400 cell the robot matches). Splits: legs / head joints, per joint mean |diff| and mean signed diff (a constant
offset), per segment, by ticks since the segment start (recurrent start-up), and the student with its state carried
across segments or warmed on the first state. Writes train/eval/g1_where_<student>.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort

T = Path(__file__).resolve().parent
sys.path.insert(0, str(T))
import ts3_gates as g  # noqa: E402

NOPACK = (0.0, -0.0335, 0.0007, 0.0186)  # flight_eval.NOPACK_PRIV: payload kg, trunk_base COM x, y, z (m)


def sess(p):
    return ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])


def run_student(s, X, new, mode="gate"):
    ins = s.get_inputs()
    acts, st = [], None
    for x, n in zip(X, new):
        if st is None or (n and mode != "carry"):
            st = np.zeros(tuple(ins[1].shape), np.float32)
            if mode == "warm":  # 50 ticks on the segment's first state before the first counted tick
                for _ in range(50):
                    st = s.run(None, {ins[0].name: x[None], ins[1].name: st})[1]
        res = s.run(None, {ins[0].name: x[None], ins[1].name: st})
        st = res[1]
        acts.append(res[0][0])
    return np.array(acts)


def run_teacher(s, X, vel, kp):
    w = s.get_inputs()[0].shape[1]
    priv = np.zeros((len(X), w - 61), np.float32)
    priv[:, :4] = NOPACK
    priv[:, 4:7] = vel
    if w == 69:
        priv[:, 7] = kp
    name = s.get_inputs()[0].name
    return np.stack([s.run(None, {name: np.concatenate([x, p])[None]})[0][0] for x, p in zip(X, priv)])


def nrm(a, cols=None):
    a = a if cols is None else a[:, cols]
    return round(float(np.linalg.norm(a, axis=1).mean()), 3)


OBS_DIMS = dict(base_ang_vel=3, projected_gravity=3, joint_pos=14, joint_vel=14, actions=14, command=3, head_command=4,
                body_command=6)


def check_layout(X, meta, order):
    """Index check before any number is read (2026-11-20: two mislabels in one night, joint order then command
    columns). Columns come from the policy file's own observation term list; three known quantities must land
    where expected: the logged walks are commanded vx 0.25 (read again from the raw log), gravity points down, and
    the knee's previous-action input moves the knee's own position input more than any other joint's."""
    terms = meta["observation_names"].split(",")
    assert sum(OBS_DIMS[t] for t in terms) == 61 == X.shape[1], terms
    col, at = {}, 0
    for t in terms:
        col[t] = (at, at + OBS_DIMS[t])
        at += OBS_DIMS[t]
    assert col["command"] == (48, 51) and col["head_command"] == (51, 55), col
    raw = set()
    for line in open(g.LOG, errors="ignore"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("mode") == "walk" and r.get("policy") == "walk" and r.get("action"):
            raw.add(round(float((r.get("cmd") or {}).get("vx") or 0), 3))
    assert raw == {0.25}, raw
    assert np.allclose(X[:, col["command"][0]], 0.25), "commanded vx is not at the command block's first column"
    assert float(X[:, col["projected_gravity"][0] + 2].mean()) < -0.9, "gravity z is not where expected"
    said = []
    for name in ("left_knee", "head_pitch"):  # the servo follows its goal about 4 ticks (80 ms) later
        k, lag = order.index(name), 4
        a, q = X[:-lag, col["actions"][0] + k], X[lag:, col["joint_pos"][0]:col["joint_pos"][1]]
        cc = [float(np.corrcoef(a, q[:, j])[0, 1]) for j in range(14)]
        assert int(np.argmax(cc)) == k and cc[k] > 0.8, (name, order[int(np.argmax(cc))], [round(c, 2) for c in cc])
        said.append(f"{name} action input tracks {name} position 4 ticks later (corr {cc[k]:.2f}, the largest of 14)")
    print(f"[layout] assertion ran: vx 0.25 at column {col['command'][0]}, gravity z at {col['projected_gravity'][0] + 2}, "
          + "; ".join(said))
    return col


def one(student, teacher):
    ref = sess(T / g.WALK61 / "walk61.onnx")
    meta = ref.get_modelmeta().custom_metadata_map
    order = meta["joint_names"].split(",")
    default = dict(zip(order, [float(v) for v in meta["default_joint_pos"].split(",")]))
    X, new = g.rebuild(order, default)
    check_layout(X, meta, order)
    seg = np.cumsum(new) - 1
    tick = np.array([i - np.flatnonzero(new)[s] for i, s in enumerate(seg)])
    legs = [k for k, j in enumerate(order) if not ("neck" in j or "head" in j)]
    head = [k for k in range(14) if k not in legs]
    W = np.stack([ref.run(None, {ref.get_inputs()[0].name: x[None]})[0][0] for x in X])
    ss = sess(T / f"ckpt/{student}/walk61.onnx")
    S = run_student(ss, X, new)
    d = S - W
    out = dict(student=student, teacher=teacher, states=len(X), segments=int(seg.max() + 1), joints=order,
               # actor inputs 48:51 twist command (vx, vy, turn), 51:55 head command (neck_pitch, head_pitch, head_yaw,
               # head_roll), 55:61 body pose. (The first version read 54:61 here and reported "command 0, head
               # command 0", which was wrong: the walks are at vx 0.25 with turn and head-pitch commands.)
               command=dict(vx=[round(float(v), 3) for v in np.unique(X[:, 48])], vy=[round(float(v), 3) for v in np.unique(X[:, 49])],
                            turn_range=[round(float(X[:, 50].min()), 3), round(float(X[:, 50].max()), 3)],
                            turn_abs_mean=round(float(np.abs(X[:, 50]).mean()), 3),
                            turn_beyond_0p5_share=round(float((np.abs(X[:, 50]) > 0.5).mean()), 3),
                            head_cmd_abs_mean=[round(float(v), 3) for v in np.abs(X[:, 51:55]).mean(axis=0)],
                            head_cmd_max=[round(float(v), 3) for v in np.abs(X[:, 51:55]).max(axis=0)],
                            head_cmd_zero_share=round(float((X[:, 51:55] == 0).all(axis=1).mean()), 3)),
               by_turn_cmd={f"{a}-{b}": dict(states=int(m.sum()), all14=nrm(d[m]), legs=nrm(d[m], legs), head=nrm(d[m], head))
                            for a, b in ((0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 3.0))
                            for m in [(np.abs(X[:, 50]) >= a) & (np.abs(X[:, 50]) < b)] if m.any()},
               by_head_pitch_cmd={f"{a}-{b}": dict(states=int(m.sum()), all14=nrm(d[m]), legs=nrm(d[m], legs), head=nrm(d[m], head),
                                                   head_pitch_signed=round(float(d[m][:, order.index("head_pitch")].mean()), 3))
                                  for a, b in ((0, 0.02), (0.02, 0.1), (0.1, 0.3), (0.3, 1.2))
                                  for m in [(np.abs(X[:, 52]) >= a) & (np.abs(X[:, 52]) < b)] if m.any()},
               student_vs_walk61=dict(all14=nrm(d), legs=nrm(d, legs), head=nrm(d, head)),
               per_joint_abs={j: round(float(np.abs(d[:, k]).mean()), 3) for k, j in enumerate(order)},
               per_joint_signed={j: round(float(d[:, k].mean()), 3) for k, j in enumerate(order)},
               offset_norm=dict(all14=round(float(np.linalg.norm(d.mean(axis=0))), 3),
                                legs=round(float(np.linalg.norm(d.mean(axis=0)[legs])), 3),
                                head=round(float(np.linalg.norm(d.mean(axis=0)[head])), 3)),
               after_removing_offset=dict(all14=nrm(d - d.mean(axis=0)), legs=nrm(d - d.mean(axis=0), legs)),
               per_segment=[dict(states=int((seg == s).sum()), all14=nrm(d[seg == s]), legs=nrm(d[seg == s], legs),
                                 head=nrm(d[seg == s], head)) for s in range(seg.max() + 1)],
               by_tick={f"{a}-{b}": dict(states=int(((tick >= a) & (tick < b)).sum()), all14=nrm(d[(tick >= a) & (tick < b)]),
                                         legs=nrm(d[(tick >= a) & (tick < b)], legs))
                        for a, b in ((0, 5), (5, 20), (20, 50), (50, 10 ** 6)) if ((tick >= a) & (tick < b)).any()},
               state_handling={m: dict(all14=nrm(run_student(ss, X, new, m) - W), legs=nrm(run_student(ss, X, new, m) - W, legs))
                               for m in ("carry", "warm")},
               walk61_action_norm=dict(all14=nrm(W), legs=nrm(W, legs), head=nrm(W, head)),
               student_action_norm=dict(all14=nrm(S), legs=nrm(S, legs), head=nrm(S, head)))
    ts = sess(T / f"ckpt/{teacher}/walk61.onnx")
    wide = ts.get_inputs()[0].shape[1]
    cases = {}
    vx_cmd = X[:, 48]
    for vname, vel in (("vel0", np.zeros((len(X), 3), np.float32)),
                       ("vel0.09", np.tile(np.array([0.09, 0, 0], np.float32), (len(X), 1))),
                       ("velcmd", np.stack([vx_cmd, X[:, 49], np.zeros(len(X), np.float32)], axis=1))):
        for kp in ((1.0, 2.0) if wide == 69 else (None,)):
            Tm = run_teacher(ts, X, vel, kp)
            key = vname + ("" if kp is None else f"_kp{kp}")
            cases[key] = dict(teacher_vs_walk61=dict(all14=nrm(Tm - W), legs=nrm(Tm - W, legs), head=nrm(Tm - W, head)),
                              teacher_by_turn_cmd={f"{a}-{b}": dict(states=int(m.sum()), legs=nrm((Tm - W)[m], legs), head=nrm((Tm - W)[m], head))
                                                   for a, b in ((0, 0.5), (0.5, 1.0), (1.0, 3.0))
                                                   for m in [(np.abs(X[:, 50]) >= a) & (np.abs(X[:, 50]) < b)] if m.any()},
                              teacher_by_head_pitch_cmd={f"{a}-{b}": dict(states=int(m.sum()), legs=nrm((Tm - W)[m], legs), head=nrm((Tm - W)[m], head))
                                                         for a, b in ((0, 0.02), (0.02, 0.1), (0.1, 0.3), (0.3, 1.2))
                                                         for m in [(np.abs(X[:, 52]) >= a) & (np.abs(X[:, 52]) < b)] if m.any()},
                              student_vs_teacher=dict(all14=nrm(S - Tm), legs=nrm(S - Tm, legs), head=nrm(S - Tm, head)),
                              teacher_per_joint_abs={j: round(float(np.abs((Tm - W)[:, k]).mean()), 3) for k, j in enumerate(order)},
                              student_minus_teacher_signed={j: round(float((S - Tm)[:, k].mean()), 3) for k, j in enumerate(order)})
    out["teacher_inputs"] = wide
    out["teacher_cases"] = cases
    (T / f"eval/g1_where_{student}_vs_{teacher}.json").write_text(json.dumps(out, indent=1))
    print(f"== {student} (teacher {teacher}, {wide} inputs): {len(X)} states, {out['segments']} segments; command {out['command']}")
    print("student vs walk61", out["student_vs_walk61"], "| constant offset", out["offset_norm"], "| after removing it",
          out["after_removing_offset"])
    print("per joint |diff| ", out["per_joint_abs"])
    print("per joint signed ", out["per_joint_signed"])
    print("per segment      ", out["per_segment"])
    print("by tick in segment", out["by_tick"])
    print("by |turn command| ", out["by_turn_cmd"])
    print("by |head pitch cmd|", out["by_head_pitch_cmd"])
    print("state carried / warmed", out["state_handling"])
    print("action norms: walk61", out["walk61_action_norm"], "student", out["student_action_norm"])
    for k, c in cases.items():
        print(f"teacher[{k}] vs walk61 {c['teacher_vs_walk61']} | student vs teacher {c['student_vs_teacher']}")
    best = min(cases, key=lambda k: cases[k]["student_vs_teacher"]["all14"])
    print(f"closest teacher case {best}: teacher per joint |diff to walk61| {cases[best]['teacher_per_joint_abs']}")
    print(f"   student minus teacher, signed {cases[best]['student_minus_teacher_signed']}")
    print(f"   teacher by |turn command| {cases[best]['teacher_by_turn_cmd']}")
    print(f"   teacher by |head pitch command| {cases[best]['teacher_by_head_pitch_cmd']}")


if __name__ == "__main__":
    a = sys.argv[1:]
    for i in range(0, len(a), 2):
        one(a[i], a[i + 1])
