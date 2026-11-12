"""Static checks behind NEXT-PLAN.md (2026-11-11): can the failing cases be held inside the servo limit at all?

1. Standing with the pack COM moved: the brain stand pose (BRAIN_STAND) on the full-pack model and on the acceptance's
   COM variants (flightpack-comx+10 / comx-10: 70 pack parts, 0.94 kg, moved 20.2 mm along trunk x, i.e. the
   whole-robot COM about 10 mm), plus a sweep of a uniform trunk lean (hip pitch and ankle together) to find the
   lean that puts the whole-robot COM over the middle of the soles. Reported: gravity torque per leg pitch joint, COM
   margin to the sole patch edge, COM x relative to the patch centre.
2. Bend poses at full pack: the policy's lowest pose from the bend_a2 clip (seed 0) and the lowest-torque bend-like
   pose of out/bend_statics.json (trunk pitch >= 20 deg, mouth <= 3 cm), with torques and COM margins.
3. The training COM offset in run A: the payload event adds U(-r, r) per axis to the loaded trunk_base COM (r = the
   com_range curriculum, 0.015 m at the end); the whole-robot COM moves by m_trunk / m_total of that. Reported: the
   loaded trunk mass and the whole-robot equivalent per load, and the fraction of resets whose forward whole-robot
   shift is at least 10 mm.
Static gravity torques only (bend_statics.Statics): no dynamics, no contact other than the soles.
Run on the Mac mini: $PY train/plan_statics.py --out train/out/plan_statics.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bend_statics as bs  # noqa: E402

M = HERE / "manifests"


def leg_tau(t):
    return {k: round(v, 3) for k, v in t.items() if k.startswith(("left_", "right_"))}


def patch(st):
    pts = st._soles()
    touch = pts[pts[:, 2] < 1.5e-3]
    return float(touch[:, 0].min()), float(touch[:, 0].max())


def stand_case(st, pose):
    s = st.state(pose)
    x0, x1 = patch(st)
    com = st.d.subtree_com[0]
    return dict(tau=leg_tau(s["tau"]), worst_nm=round(max(abs(v) for v in leg_tau(s["tau"]).values()), 3),
                com_margin_mm=round(1000 * s["com_margin"], 1), com_x_from_patch_centre_mm=round(1000 * (com[0] - (x0 + x1) / 2), 1),
                patch_length_mm=round(1000 * (x1 - x0), 1), trunk_pitch_deg=round(s["trunk_pitch_deg"], 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clip", default=str(HERE / "video/bend_a2_bend_pack.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    # 1. standing with the COM variants
    stand_res = {}
    for name in ("load100", "nominal", "comx+10", "comx-10", "none"):
        b, m, d, names = bs.load_model(M / f"flightpack-{name}.json")
        st = bs.Statics(b, m, d, names)
        stand = {n: float(b.BRAIN_STAND[n]) for n in names}
        r = dict(total_kg=round(float(m.body_subtreemass[0]), 4), trunk_kg=round(float(m.body_mass[m.body("trunk_base").id]), 4),
                 brain_stand=stand_case(st, stand))
        # lean sweep: hip pitch and ankle moved together (mirrored legs), trunk tilts, feet stay flat
        sweep = []
        for dq in np.linspace(-0.3, 0.3, 13):
            p = bs.mirror_pose(stand, {"left_hip_pitch": stand["left_hip_pitch"] + dq, "left_ankle": stand["left_ankle"] + dq},
                               stand, st.mirror)
            c = stand_case(st, p)
            c["dq_rad"] = round(float(dq), 3)
            sweep.append(c)
        r["lean_sweep"] = sweep
        r["best_centred"] = min(sweep, key=lambda c: abs(c["com_x_from_patch_centre_mm"]))
        stand_res[name] = r
        print(f"[plan-statics] stand {name}: {r['brain_stand']}", flush=True)
    res["stand"] = stand_res
    # 3. training offset equivalence
    full = stand_res["load100"]
    eq = {}
    for name in ("load100", "none"):
        r = stand_res[name]
        frac = r["trunk_kg"] / r["total_kg"]
        need = 0.010 / frac  # trunk COM offset that moves the whole robot 10 mm
        eq[name] = dict(trunk_share=round(frac, 3), trunk_offset_for_10mm_m=round(need, 4),
                        whole_robot_mm_at_r15=round(15 * frac, 1),
                        p_forward_10mm_at_r15=round(max(0.0, (0.015 - need) / 0.030), 3))
    res["training_offset"] = eq
    # 2. bend poses at full pack
    b, m, d, names = bs.load_model(M / "flightpack-load100.json")
    st = bs.Statics(b, m, d, names)
    stand = {n: float(b.BRAIN_STAND[n]) for n in names}
    clip = json.loads(Path(a.clip).read_text())
    pm = clip["probe"]["groundpick"]["pose_at_min"]
    pose = dict(stand)
    pose.update({k: float(v) for k, v in pm.items() if k in pose})
    s = st.state(pose)
    res["bend_policy_lowest"] = dict(pose=pm, mouth_z=round(s["mouth_z"], 4), trunk_pitch_deg=round(s["trunk_pitch_deg"], 1),
                                     com_margin_mm=round(1000 * s["com_margin"], 1), tau=leg_tau(s["tau"]))
    bst = json.loads((HERE / "out/bend_statics.json").read_text())["loads"]["full"]["search_bend_like"]["lowest_worst_joint"]
    p2 = bs.mirror_pose(stand, bst["pose"], stand, st.mirror)
    s2 = st.state(p2)
    res["bend_statics_best"] = dict(pose=bst["pose"], mouth_z=round(s2["mouth_z"], 4), trunk_pitch_deg=round(s2["trunk_pitch_deg"], 1),
                                    com_margin_mm=round(1000 * s2["com_margin"], 1), tau=leg_tau(s2["tau"]),
                                    joint_pose={k: round(v, 3) for k, v in p2.items() if any(j in k for j in ("hip_pitch", "knee", "ankle"))})
    print(f"[plan-statics] bend policy {res['bend_policy_lowest']}; statics best {res['bend_statics_best']}", flush=True)
    Path(a.out).write_text(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
