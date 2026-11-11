"""Incentive-audit gate for the flight-pack Kaggle launches (the Kaggle twin of finetune.py::run's require_audit).

  python3 audit_gate.py record universal2 out/audit2_chosen_full.json out/audit2_chosen_nobatt.json out/audit2_chosen_none.json
  python3 audit_gate.py record bend out/bend_audit_full.json ...     (bend_audit.py output, same verdict layout)
  python3 audit_gate.py check universal2                               (exit 1 unless every recorded load passed)

record reads each audit file's verdict (flight_audit.py universal2 layout: results.<job>.verdict.verdict, or a top-level
"verdict" for bend_audit.py) and writes out/audit_gate.json: delta -> {verdict, loads, files, sha256, time}.
kaggle_flight.py push calls check for every --delta it launches and refuses one without a PASS on every load.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

GATE = Path(__file__).resolve().parent / "out/audit_gate.json"
NEED_LOADS = {"full", "nobatt", "none"}


def verdict_of(d):
    if "verdict" in d and isinstance(d["verdict"], str):
        return d["verdict"], d.get("load")
    for job in d.get("results", {}).values():
        v = job.get("verdict", {})
        loads = {k.split(":")[0] for k in v.get("checks", {})}
        return v.get("verdict"), (loads.pop() if len(loads) == 1 else None)
    return None, None


def record(delta, files):
    gate = json.loads(GATE.read_text()) if GATE.exists() else {}
    loads, ok, shas = {}, True, {}
    for f in files:
        p = Path(f)
        d = json.loads(p.read_text())
        v, ld = verdict_of(d)
        loads[ld] = v
        ok &= v == "PASS"
        shas[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    ok &= NEED_LOADS <= set(loads)
    gate[delta] = dict(verdict="PASS" if ok else "FAIL", loads=loads, files=shas, time=time.strftime("%Y-%m-%dT%H:%M:%S"))
    GATE.write_text(json.dumps(gate, indent=1))
    print(delta, gate[delta])
    return ok


def check(delta):
    gate = json.loads(GATE.read_text()) if GATE.exists() else {}
    g = gate.get(delta)
    if not g or g["verdict"] != "PASS":
        print(f"audit gate: no PASS for delta {delta!r} in {GATE} ({g}); run the incentive audit first")
        return False
    out = GATE.parent
    for name, sha in g["files"].items():
        p = out / name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()[:16] != sha:
            print(f"audit gate: {name} changed or missing since the gate was recorded")
            return False
    print(f"audit gate: {delta} PASS at {sorted(g['loads'])} ({g['time']})")
    return True


if __name__ == "__main__":
    cmd, delta, *files = sys.argv[1:]
    sys.exit(0 if (record(delta, files) if cmd == "record" else check(delta)) else 1)
