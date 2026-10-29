"""Joint-space search over the four head joints (neck_pitch, head_pitch, head_yaw, head_roll) for camera elevation.

Two joint boxes: "policy" = the stand61/walk61 head_pose command (deltas from the NEUTRAL head within
walk_brain.HEAD_RANGE 1.10/1.10/1.40/0.31, then clamped to the MJCF range as walk_brain does) and "openloop" = the
MJCF hinge ranges (walk_brain.JOINT_RANGE), which the open-loop stand can command directly. Legs at STAND, trunk
upright (the sim rest tilt is small and added separately). Pure kinematics (duck_kin); self-collision and balance
are checked afterwards by collide.py and sim_batch.py on the picks.

Score: optical-axis elevation, counted only while the camera still looks forward-ish or sideways (the robot can turn
its body toward a person, so the horizontal heading is free), never past the vertical (image upside down, looking
behind). Also recorded: the horizontal heading of the view, the image roll (frame rotation needed before face
detection), the camera height and, at 0.3 / 0.5 / 1.0 m along the view heading, the highest face centre inside the
frame and the IPD of a 1.6 m standing face.

  ~/.venvs/microduck-dyn/bin/python headsearch.py  -> results/headsearch.json and the top lists on stdout
"""
import itertools
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import facegeom as fg  # noqa: E402
from facegeom import HEAD_JOINTS, HEAD_RANGE, JOINT_RANGE, NEUTRAL, STAND  # noqa: E402

RES = os.path.join(HERE, "results")
os.makedirs(RES, exist_ok=True)
STEP = 0.1  # rad


def box(kind):
    lo, hi = {}, {}
    for k, n in enumerate(HEAD_JOINTS):
        jl, jh = JOINT_RANGE[n]
        if kind == "policy":
            lo[n] = max(jl, NEUTRAL[n] - HEAD_RANGE[k])
            hi[n] = min(jh, NEUTRAL[n] + HEAD_RANGE[k])
        else:
            lo[n], hi[n] = jl, jh
    return lo, hi


def grid(lo, hi, step=STEP):
    axes = []
    for n in HEAD_JOINTS:
        vals = list(np.arange(lo[n], hi[n] + 1e-9, step))
        if vals[-1] < hi[n] - 1e-6:
            vals.append(hi[n])
        vals = sorted(set(round(float(v), 4) for v in vals) | {0.0, round(NEUTRAL[n], 4), round(STAND[n], 4)})
        axes.append([v for v in vals if lo[n] - 1e-9 <= v <= hi[n] + 1e-9])
    return axes


def evaluate(head, legs=STAND):
    q = dict(legs, **head)
    pos, R = fg.camera(q)
    a = R[:, 0]
    elev = fg.elevation_deg(R)
    heading = math.degrees(math.atan2(a[1], a[0]))  # 0 = the robot's forward, + = left
    rec = dict(head={n: round(head[n], 3) for n in HEAD_JOINTS}, elev_deg=round(elev, 1), heading_deg=round(heading, 1),
               image_roll_deg=round(fg.image_roll_deg(R), 1), cam_height_m=round(float(pos[2]), 3),
               cam_x_m=round(float(pos[0]), 3), forward=bool(abs(heading) <= 90.0 + 1e-6))
    rec["top_edge_deg"] = round(elev + fg.HALF_V_DEG, 1)
    for D in (0.3, 0.5, 1.0):
        rec[f"highest_face_m@{D}"] = fg.highest_face(pos, elev, D)
        f = fg.face_view(pos, R, D, 1.6, yaw_deg=heading)
        rec[f"adult_1.6m@{D}"] = dict(inside=f["inside"], ipd_px=f["ipd_px"], los_up_deg=f["los_up_deg"])
    return rec


def search(kind):
    lo, hi = box(kind)
    axes = grid(lo, hi)
    recs = []
    for vals in itertools.product(*axes):
        head = dict(zip(HEAD_JOINTS, vals))
        r = evaluate(head)
        if not r["forward"] or r["elev_deg"] > 89.0:
            continue  # past the vertical or looking behind the robot
        recs.append(r)
    recs.sort(key=lambda r: -r["elev_deg"])
    return dict(kind=kind, lo=lo, hi=hi, step=STEP, n=len(recs), recs=recs)


def pitch_only_best(res):
    return max((r for r in res["recs"] if abs(r["head"]["head_yaw"]) < 1e-6 and abs(r["head"]["head_roll"]) < 1e-6),
               key=lambda r: r["elev_deg"])


def distinct_top(res, n=12, min_sep=0.25):
    """Top records that differ from each other by at least min_sep rad in some head joint."""
    out = []
    for r in res["recs"]:
        if all(max(abs(r["head"][j] - o["head"][j]) for j in HEAD_JOINTS) >= min_sep for o in out):
            out.append(r)
        if len(out) >= n:
            break
    return out


if __name__ == "__main__":
    out = {}
    for kind in ("policy", "openloop"):
        res = search(kind)
        best_pitch = pitch_only_best(res)
        res["pitch_only_best"] = best_pitch
        res["top_distinct"] = distinct_top(res)
        res["top_yawed"] = [r for r in res["recs"] if abs(r["head"]["head_yaw"]) >= 0.8][:40]
        # head mass kept forward: the pose with the camera furthest forward (cam_x) in each elevation band, yawed
        # (|head_yaw| >= 0.8: roll becomes elevation) and unyawed; a forward head is what the back-leaning robot needs
        res["forward_mass"] = {}
        for lo_e, hi_e in ((30, 45), (45, 60), (60, 75), (75, 89)):
            band = [r for r in res["recs"] if lo_e <= r["elev_deg"] < hi_e]
            for tag, sel in (("yawed", [r for r in band if abs(r["head"]["head_yaw"]) >= 0.8]),
                             ("unyawed", [r for r in band if abs(r["head"]["head_yaw"]) < 0.8])):
                if sel:
                    best = max(sel, key=lambda r: r["cam_x_m"])
                    res["forward_mass"][f"{lo_e}-{hi_e}_{tag}"] = best
                    print(f"  forward-mass {lo_e}-{hi_e} {tag:<8} cam_x {best['cam_x_m']:.3f} z {best['cam_height_m']:.3f} elev {best['elev_deg']:+5.1f} heading {best['heading_deg']:+6.1f} roll {best['image_roll_deg']:+6.1f} head {best['head']}")
        print(f"== {kind}: {res['n']} forward poses; pitch-only best elev {best_pitch['elev_deg']} at {best_pitch['head']}")
        for r in res["top_distinct"]:
            print(f"  elev {r['elev_deg']:+6.1f} heading {r['heading_deg']:+6.1f} roll {r['image_roll_deg']:+6.1f} z {r['cam_height_m']:.3f} "
                  f"head {r['head']}  adult@0.5 inside {r['adult_1.6m@0.5']['inside']} ipd {r['adult_1.6m@0.5']['ipd_px']}")
        print("  best with |yaw| >= 0.8:")
        for r in distinct_top(dict(recs=res["top_yawed"]), n=5):
            print(f"  elev {r['elev_deg']:+6.1f} heading {r['heading_deg']:+6.1f} roll {r['image_roll_deg']:+6.1f} z {r['cam_height_m']:.3f} head {r['head']}")
        res["recs"] = res["recs"][:400]
        out[kind] = res
    with open(os.path.join(RES, "headsearch.json"), "w") as f:
        json.dump(out, f, indent=1)
