"""Side-by-side read-out of the teacher-student round (TEACHER-STUDENT-PLAN.md section 7) from the result files.

  python3 train/ts_compare.py <dir> [<dir> ...]      -> out/ts_compare.json and a printed table

Per policy dir (under train/ckpt) and load state: falls of 20 standing and walking, median upright walk speed (m/s)
and leg torque p99 (N m) from eval/ua_<dir>_<case>.json (accept_universal.py, dev seeds 0..19); the added neck/head
walk from eval/uh_<dir>_neck_<load>.json (accept_head.py); the robustness cases with the pack; the acceptance verdict
and the number of failed lines from out/accept_<dir>.json.
"""
import json
import sys
from pathlib import Path

T = Path(__file__).resolve().parent
LOADS = (("none", "nopack_stand", "nopack_walk"), ("load025", "load025_stand", "load025_walk"),
         ("load050", "load050_stand", "load050_walk"), ("load075", "load075_stand", "load075_walk"),
         ("nobatt", "nobatt_stand", "nobatt_walk"), ("load100", "nominal_stand", "load100_walk"))
EXTRA = ("nominal_walk", "comx+10_stand", "comx+10_walk", "comx-10_walk", "mass+10_walk", "nominal_walk_shove05",
         "nominal_stand_shove05", "nominal_walk_landing", "nominal_turnL", "nopack_turnL")


def summ(d, case, prefix="ua"):
    p = T / f"eval/{prefix}_{d}_{case}.json"
    return json.loads(p.read_text())["summary"] if p.exists() else None


out = {}
for d in sys.argv[1:]:
    row = dict(loads={}, extra={})
    for ld, st, wk in LOADS:
        s, w, h = summ(d, st), summ(d, wk), summ(d, f"neck_{ld}", "uh")
        row["loads"][ld] = dict(stand_falls=s and s["falls"], walk_falls=w and w["falls"],
                                walk_speed=w and w.get("speed_median_upright"), walk_leg_p99_nm=w and w.get("leg_force_p99_nm_median"),
                                head_walk_falls=h and h["falls"], head_walk_speed=h and h.get("speed_median_upright"))
    for c in EXTRA:
        s = summ(d, c)
        row["extra"][c] = s and dict(falls=s["falls"], speed=s.get("speed_median_upright"))
    a = T / f"out/accept_{d}.json"
    if a.exists():
        j = json.loads(a.read_text())
        row["verdict"] = j["verdict"]
        row["failed_lines"] = [f"{ln['line']}: {ln['detail']}" for ln in j["lines"] if ln["result"] == "FAIL"]
        row["missing"] = j["missing"]
    out[d] = row
(T / "out/ts_compare.json").write_text(json.dumps(out, indent=1))
for ld, _, _ in LOADS:
    print(ld)
    for d, row in out.items():
        r = row["loads"][ld]
        print(f"  {d:12s} stand falls {r['stand_falls']}, walk falls {r['walk_falls']} at {r['walk_speed']} m/s, leg p99 {r['walk_leg_p99_nm']}, "
              f"head-command walk falls {r['head_walk_falls']} at {r['head_walk_speed']} m/s")
print("with pack, robustness (falls of 20)")
for d, row in out.items():
    print(f"  {d:12s}", ", ".join(f"{c} {v['falls'] if v else None}" for c, v in row["extra"].items()))
for d, row in out.items():
    print(f"{d}: verdict {row.get('verdict')}, {len(row.get('failed_lines', []))} failed lines, missing {row.get('missing')}")
