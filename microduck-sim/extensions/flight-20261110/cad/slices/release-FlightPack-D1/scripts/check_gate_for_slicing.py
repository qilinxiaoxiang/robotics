"""Exit 0 only when STATUS.json records a passing gate (RELEASED, or RELEASED_WITH_EXCEPTION under A-GATE-BPHATCH) for the
printed STLs that run_fp.sh will slice: each cad/build/<part>-world.stl must equal guide/print/world/<part>.stl and match the
hash STATUS.json recorded when the gate ran. Run by scripts/run_fp.sh before anything is sliced.
    /tmp/microduck-cad-venv/bin/python scripts/check_gate_for_slicing.py
"""
import hashlib
import json
import sys
from pathlib import Path

REL = Path(__file__).resolve().parents[1]
CAD = REL.parents[1]
WORLD = CAD.parents[2] / 'guide' / 'print' / 'world'
PARTS = ['wing_plate', 'tray_L', 'tray_R', 'fc_bracket', 'nacelle_inner_L', 'nacelle_outer_L', 'nacelle_inner_R', 'nacelle_outer_R']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


st = json.loads((REL / 'STATUS.json').read_text())
errs = []
if st.get('status') not in ('RELEASED', 'RELEASED_WITH_EXCEPTION'):
    errs.append(f"STATUS.json status {st.get('status')}")
geo = st.get('geometry') if isinstance(st.get('geometry'), dict) else {}
for k in PARTS:
    b, w = sha(CAD / 'build' / f'{k}-world.stl'), sha(WORLD / f'{k}.stl')
    if b != w:
        errs.append(f'{k}: cad/build differs from guide/print/world (run cad/sync_world.py, then the guide build and gate_status.py)')
    if geo.get(k) != w[:12]:
        errs.append(f'{k}: gate ran on {geo.get(k)}, world STL is now {w[:12]} (rerun gate_status.py)')
print('gate covers the current geometry' if not errs else '\n'.join(errs))
sys.exit(1 if errs else 0)
