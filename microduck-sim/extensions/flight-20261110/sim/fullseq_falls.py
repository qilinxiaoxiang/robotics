"""Hand-over readback for the full-sequence rows (sim/out/fullseq_<legs>): touchdown hand-over state, what happened after
the disarm, and for each fall its direction and the 50 Hz trace around it.

  $PY sim/fullseq_falls.py sim/out/fullseq_handover   -> prints, writes <dir>/falls.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

PH = ["idle", "spool", "climb", "hold1", "move", "hold2", "hover", "land", "spooldown", "disarmed", "cut"]
D = Path(sys.argv[1])
rows_out = []
for f in sorted(D.glob("*__*__s*.json")):
    r = json.loads(f.read_text())
    pol = r.get("policy") or {}
    ho = (pol.get("handover") or {})
    tp = ho.get("to_policy") or {}
    rec = dict(row=f.stem, airborne=r["airborne_success"], full=r["full_success"], disarm_t=r["disarm_t"],
               fell45_at=r["fell45_at"], fell45_phase=r["fell45_phase"], to_stand=ho.get("to_stand"), at_stand=ho.get("at_stand"),
               to_policy=tp, touchdown_vz=r["landing_vz_mps"], touchdown_tilt=r["touchdown_tilt_deg"],
               touch_err=r["touchdown_pos_err_m"], tilt_after_touch=r["tilt_max_after_touch_deg"], support_end=r["support_end"])
    npz = f.with_suffix(".npz")
    if r["fell45_at"] is not None and npz.exists():
        L = np.load(npz)["log"]
        tf = r["fell45_at"]
        w = L[(L[:, 0] >= tf - 1.0) & (L[:, 0] <= tf + 0.1)]
        k = int(np.argmin(abs(L[:, 0] - tf)))
        rec["fall"] = dict(roll_deg=round(math.degrees(L[k, 4]), 1), pitch_deg=round(math.degrees(L[k, 5]), 1),
                           xy=[round(float(L[k, 1]), 3), round(float(L[k, 2]), 3)], z=round(float(L[k, 3]), 3),
                           leg_tau_max_last_1s=round(float(w[:, 24].max()), 3),
                           trace=[[round(float(x[0]), 2), PH[int(x[25])], round(math.degrees(x[4]), 1), round(math.degrees(x[5]), 1),
                                   round(float(x[3]), 3), round(float(np.mean(x[17:21])), 2), round(float(x[24]), 3)]
                                  for x in w[::5]])
    rows_out.append(rec)
    print(json.dumps({k: v for k, v in rec.items() if k != "fall"}))
    if "fall" in rec:
        fl = rec["fall"]
        print("   fall: roll", fl["roll_deg"], "pitch", fl["pitch_deg"], "xy", fl["xy"], "z", fl["z"], "leg tau max", fl["leg_tau_max_last_1s"])
        print("   trace [t, phase, roll, pitch, trunk z, mean fan N, leg tau max]:")
        for x in fl["trace"]:
            print("     ", x)
(D / "falls.json").write_text(json.dumps(rows_out, indent=1))
