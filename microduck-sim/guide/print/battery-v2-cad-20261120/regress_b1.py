"""Regression for the insertion sweep (checks.py STEPS): run it on the rev B1 frame and cap (commit 723160c4, the
geometry the guide gate rejected at bv2-battery) and require the battery path to collide. Prints both sweeps.
    python regress_b1.py <b1_build_dir>      (b1_build_dir holds battery_v2_frame-world.stl and battery_v2_cap-world.stl
                                              built by build_v2.py at 723160c4)
Exit 1 when the sweep passes the B1 battery path (the check would have missed the defect)."""
import json, sys
from pathlib import Path
import checks as C

d = Path(sys.argv[1])
frame, cap = C.load(d / "battery_v2_frame-world.stl"), C.load(d / "battery_v2_cap-world.stl")
mating = {f.stem: C.load(f) for f in sorted((C.B.BP / "mating").glob("*.stl")) if f.stem not in ("rear_frame", "rear_lid")}
res = C.insertion(frame, cap, mating, C.B.bought_parts())
for r in res: print(r["id"], r["max_overlap_mm3"], r["worst_offset"], "COLLIDES" if r["collides"] else "clear")
bat = next(r for r in res if r["id"] == "battery")
(C.CK / "regress_b1.json").write_text(json.dumps(res, indent=1))
sys.exit(0 if bat["collides"] else 1)
