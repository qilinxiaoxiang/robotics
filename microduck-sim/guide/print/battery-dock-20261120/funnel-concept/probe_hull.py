"""Does the backpack collision hull change the baseline? Same sit + stand-up with and without it; floor contacts seated."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import simcore as S
out = {}
for h in (False, True):
    r = S.run(dock_boxes=None, sit_at=4.0, unsit_at=10.0, hull=h)
    sm = r["summary"]
    fl = {round(t, 1): f for t, f in zip(r["t"], r["floor"]) if abs(t % 1.0) < 0.03}
    out[str(h)] = dict(fell_at=sm.get("fell_at"), fall_dir=sm.get("fall_dir"), sit=sm.get("sit"), floor_contacts=fl)
    print(h, sm.get("fell_at"), sm.get("fall_dir"), sm.get("sit", {}).get("rise"), sm.get("sit", {}).get("done"))
    for t in (3.0, 8.0, 11.0, 13.0, 15.0):
        print("  ", t, fl.get(t))
(S.HERE / "checks/hull_effect.json").write_text(json.dumps(out, indent=1, default=str))
