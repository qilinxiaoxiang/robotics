"""50 Hz trace of one full-sequence row from its touchdown hand-over to the end (every 0.1 s).

  $PY sim/fullseq_trace.py sim/out/fullseq_handover/ARE_thrust90__hover__s1.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

PH = ["idle", "spool", "climb", "hold1", "move", "hold2", "hover", "land", "spooldown", "disarmed", "cut"]
f = Path(sys.argv[1])
r = json.loads(f.read_text())
L = np.load(f.with_suffix(".npz"))["log"]
ho = ((r.get("policy") or {}).get("handover") or {}).get("to_policy") or {}
t0 = ho.get("t", r.get("disarm_t") or 0) - 0.2
print("to_policy", ho, "disarm", r["disarm_t"], "nacelle_hit", r["nacelle_hit_at"], "tilt_end", r["tilt_end_deg"],
      "support_end", r["support_end"])
print("[t, phase, x, y, trunk z, roll, pitch, mean fan N, leg tau max]")
for x in L[L[:, 0] >= t0][::5]:
    print([round(float(x[0]), 2), PH[int(x[25])], round(float(x[1]), 3), round(float(x[2]), 3), round(float(x[3]), 3),
           round(math.degrees(x[4]), 1), round(math.degrees(x[5]), 1), round(float(np.mean(x[17:21])), 2), round(float(x[24]), 3)])
