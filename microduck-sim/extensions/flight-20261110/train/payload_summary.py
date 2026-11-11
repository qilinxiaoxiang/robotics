"""Summarise the per-load probe (payload_probe.sh) for UNIVERSAL-PLAN.md: falls, speed and the hip servos' load.

  python3 train/payload_summary.py  -> train/out/payload_probe.json
Per policy, load and case: falls of N, median tracked speed (upright episodes), and for the six hip servos (yaw, roll,
pitch, both legs) and the knees/ankles: the median over episodes of each joint's p99 |torque| and the mean share of
time at >= 95 % of the 0.538 N m clamp (flight_eval.py per_joint_all, all ticks after 1 s), plus the worst joint.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
LOADS = ("load000", "load025", "load050", "nobatt", "load075", "load100")
POL = {"fq2_1999": "fq2 1999 (with-pack policy, policy from the first tick)",
       "spec": "stand61/walk61 today (0.3 s open-loop stand, as the no-pack robot starts)"}
GROUPS = {"hip": ("hip_yaw", "hip_roll", "hip_pitch"), "knee": ("knee",), "ankle": ("ankle",)}


def main():
    pay = json.loads((HERE / "manifests" / "payload_loads.json").read_text())
    out = {"note": __doc__.strip().splitlines()[0], "policies": POL, "loads": pay, "results": {}}
    for p in POL:
        for ld in LOADS:
            for c in ("stand", "walk", "turnL", "turnR", "stand_olstart", "walk_olstart", "turnL_olstart", "turnR_olstart"):
                f = HERE / "eval" / f"pl_{p}_{ld}_{c}.json"
                if not f.exists():
                    continue
                d = json.loads(f.read_text())
                s, eps = d["summary"], d["episodes"]
                joints = {}
                for j in eps[0]["per_joint_all"]:
                    joints[j] = dict(mean_nm=round(float(np.median([e["per_joint_all"][j]["mean_nm"] for e in eps])), 3),
                                     p99_nm=round(float(np.median([e["per_joint_all"][j]["p99_nm"] for e in eps])), 3),
                                     sat_frac=round(float(np.mean([e["per_joint_all"][j]["sat_frac"] for e in eps])), 4))
                grp = {}
                for g, keys in GROUPS.items():
                    sel = {j: v for j, v in joints.items() if any(j.endswith(k) for k in keys)}
                    worst = max(sel, key=lambda j: sel[j]["p99_nm"])
                    grp[g] = dict(p99_max_nm=sel[worst]["p99_nm"], worst=worst,
                                  mean_max_nm=max(v["mean_nm"] for v in sel.values()),
                                  sat_frac_max=max(v["sat_frac"] for v in sel.values()))
                out["results"][f"{p}/{ld}/{c}"] = dict(payload_kg=pay[ld]["payload_kg"], falls=s["falls"],
                                                       episodes=s["episodes"], speed=s["speed_median_upright"],
                                                       groups=grp, joints=joints)
                r = out["results"][f"{p}/{ld}/{c}"]
                print(f"{p:9s} {ld} {c:5s} {pay[ld]['payload_kg']:.3f} kg falls {s['falls']}/{s['episodes']} "
                      f"speed {s['speed_median_upright']} | hip p99 {grp['hip']['p99_max_nm']} ({grp['hip']['worst']}) "
                      f"sat {grp['hip']['sat_frac_max']} | knee {grp['knee']['p99_max_nm']} sat {grp['knee']['sat_frac_max']} "
                      f"| ankle {grp['ankle']['p99_max_nm']} sat {grp['ankle']['sat_frac_max']}")
    (HERE / "out" / "payload_probe.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
