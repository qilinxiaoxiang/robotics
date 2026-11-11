"""Held-legs mode reproduces the earlier rows: every field of sim/out/batch/<row> equals the rerun in --out-dir.

  $PY sim/heldcheck.py sim/out/heldcheck      -> prints each row's differing fields; exit 1 if any field differs
New fields (legs, full_success, liftoff, ...) are only in the rerun and are listed, not compared.
"""
import json
import sys
from pathlib import Path

H = Path(__file__).resolve().parent
new_dir = Path(sys.argv[1])
bad = 0
out = []
for f in sorted(new_dir.glob("*__*__s*.json")):
    old_f = H / "out" / "batch" / f.name
    if not old_f.exists():
        continue
    old, new = json.loads(old_f.read_text()), json.loads(f.read_text())
    diff = {k: (old[k], new.get(k)) for k in old if old[k] != new.get(k)}
    added = sorted(set(new) - set(old))
    bad += bool(diff)
    out.append(dict(row=f.name, fields_compared=len(old), differing=diff, new_fields=added))
    print(f.name, "identical" if not diff else f"DIFFERS {diff}", f"({len(old)} fields)")
(new_dir / "heldcheck.json").write_text(json.dumps(out, indent=1))
sys.exit(1 if bad else 0)
