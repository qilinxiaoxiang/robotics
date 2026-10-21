"""Rebuild the printed V1.24 inner ankle halves (45 deg teardrop roof) into retired/ for the parts sheet, from
make_halves.py as released in commit 6cdda66, and check them against the sha256 the V1.24 pose study recorded.

    /tmp/microduck-cad-venv/bin/python scripts/make_retired.py
"""
import hashlib, subprocess
from pathlib import Path

REL = Path(__file__).resolve().parents[1]; HALVES = REL.parent / 'ankle-halves-20261020'
V124_SHA = {'left': '39a50f3ba5e355a55d023e99b3ecd461e86edc2f988af0be822d265472b5d55a',
            'right': '64bee9a6ffc4d061067e4531aaef10d6d7297e6fa4b6b6e0efea65b49125cef8'}
src = subprocess.run(['git', 'show', '6cdda66:microduck-sim/guide/print/ankle-halves-20261020/make_halves.py'],
                     cwd=HALVES, check=True, capture_output=True, text=True).stdout
src = src.replace('HERE = Path(__file__).resolve().parent', f'HERE = Path({str(HALVES)!r})')
ns = {'__name__': 'v124_make_halves', '__file__': str(HALVES / 'make_halves.py')}
exec(compile(src, 'make_halves@6cdda66', 'exec'), ns)
for side, K in ns['SIDES'].items():
    T = ns['frame'](K['sign']); old = ns['stock_local'](K['ankle'], T)
    inner = old ^ ns['box_z'](ns['CUT'] + ns['CUT_GAP'], 100)
    lip = (ns['cyl'](ns['LIP_R_OUT'], ns['LIP_Z0'], ns['LIP_TOP']) - ns['cyl'](ns['LIP_R_IN'], ns['LIP_Z0'] - 1, ns['LIP_TOP'] + 1)) \
        ^ inner.project().extrude(ns['LIP_TOP'] - ns['LIP_Z0']).translate([0, 0, ns['LIP_Z0']])
    roof = ns['tear'](K['sign'], *ns['TEAR_POCKET']) + ns['tear'](K['sign'], *ns['TEAR_BORE'])
    inner = ns['single'](((inner + lip) - roof).simplify(1e-4), f'{side}-inner')
    out = REL / 'retired' / f'ankle_inner_{side}-V1.24.stl'; ns['tm'](inner).export(out)
    got = hashlib.sha256(out.read_bytes()).hexdigest()
    print(side, out.name, got == V124_SHA[side])
    assert got == V124_SHA[side], (side, got)
