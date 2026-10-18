#!/usr/bin/env python3
"""Study solid: the V1.8 head cap with the rear cable notch and zip-tie hood undone.

Method: inside the notch edit box recorded by the V1.6 cap change (release-V1.6/evidence/cap-notch-report-snapshot.json,
unchangedGeometry.editBoxWorldMm) take the pre-notch V1.5 cap (v15Source print file mapped to the robot frame with the
inverse of the recorded worldToPrint); outside it keep the V1.8 cap unchanged.
  nonotch = (V1.8 - box) + (V1.5 & box)
Checks: XOR volume of nonotch against V1.8 outside the box (must be ~0), XOR of V1.5 against V1.8 inside the box
(= notch + hood), the box faces cut through a region where V1.5 and V1.8 agree (seam check), closed manifold.
Writes study-solids/head_cap-no-notch.stl (robot frame) and nonotch-cap.json. Study file only, not a print file.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as m3

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nr_lib import HERE, SIM, GUIDE, ia_lib, jdump, rnd  # noqa: E402

EVID = GUIDE / 'print/release-V1.6/evidence'
change = json.loads((EVID / 'head_cap-change.json').read_text())
snap = json.loads((EVID / 'cap-notch-report-snapshot.json').read_text())
V15 = Path(change['v15Source']['path'])
V18 = GUIDE / 'print/world/head_cap.stl'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(V15) == change['v15Source']['sha256'], 'V1.5 source changed'

W2P = np.array(snap['worldToPrint']['matrix4x4'])
P2W = np.linalg.inv(W2P)
box = snap['unchangedGeometry']['editBoxWorldMm']
lo, hi = np.array(box['min']), np.array(box['max'])


def man(m):
    return ia_lib.to_manifold(np.asarray(m.vertices), np.asarray(m.faces))


v15 = trimesh.load(V15, force='mesh')
v15.apply_transform(P2W)
v18 = trimesh.load(V18, force='mesh')
A15, A18 = man(v15), man(v18)
assert ia_lib.manifold_ok(A15) and ia_lib.manifold_ok(A18)
B = m3.Manifold.cube(list(hi - lo)).translate(list(lo))
new = (A18 - B) + (A15 ^ B)
assert ia_lib.manifold_ok(new)

xor = lambda a, b: (a - b).volume() + (b - a).volume()
out_new = xor(new - B, A18 - B)               # outside the box: must equal V1.8
in_box_15_18 = xor(A15 ^ B, A18 ^ B)          # inside the box: what the notch + hood edit changed
# Seam: on a 0.6 mm shell around the box faces the two caps must agree, otherwise the splice leaves a step.
B_in = m3.Manifold.cube(list(hi - lo - 1.2)).translate(list(lo + 0.6))
B_out = m3.Manifold.cube(list(hi - lo + 1.2)).translate(list(lo - 0.6))
shell = B_out - B_in
seam = xor(A15 ^ shell, A18 ^ shell)
# Notch and hood volumes, from the V1.5 -> V1.8 difference inside the box.
removed = ((A15 - A18) ^ B).volume()
added = ((A18 - A15) ^ B).volume()

vv, ff = ia_lib.from_manifold(new)
mesh = trimesh.Trimesh(vv, ff, process=True)
(HERE / 'study-solids').mkdir(exist_ok=True)
outp = HERE / 'study-solids' / 'head_cap-no-notch.stl'
mesh.export(outp)
chk = trimesh.load(outp, force='mesh')
res = {
    'what': 'Study solid: V1.8 head cap without the rear cable notch and zip-tie hood (not a print file).',
    'method': 'nonotch = (V1.8 cap - edit box) + (V1.5 pre-notch cap & edit box); exact manifold3d booleans',
    'inputs': {'v18Cap': {'path': str(V18), 'sha256': sha(V18)},
               'v15PreNotchCapPrint': {'path': str(V15), 'sha256': sha(V15), 'mappedBy': 'inverse of cap-notch-report-snapshot.json worldToPrint'},
               'editBoxWorldMm': box},
    'xorOutsideEditBoxMm3': rnd(out_new, 6),
    'xorV15vsV18InsideBoxMm3': rnd(in_box_15_18, 3),
    'notchMaterialRestoredMm3': rnd(removed, 3),
    'hoodMaterialRemovedMm3': rnd(added, 3),
    'seamShellXorMm3_0p6mm': rnd(seam, 6),
    'volumes': {'v18': rnd(A18.volume(), 3), 'v15': rnd(A15.volume(), 3), 'nonotch': rnd(new.volume(), 3)},
    'output': {'path': str(outp), 'sha256': sha(outp), 'watertight': bool(chk.is_watertight),
               'windingConsistent': bool(chk.is_winding_consistent), 'bodies': len(chk.split(only_watertight=False)),
               'boundsMm': rnd(chk.bounds, 3)},
}
jdump(res, HERE / 'nonotch-cap.json')
print(json.dumps(res, indent=1))
