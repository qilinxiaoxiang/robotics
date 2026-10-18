"""Neck pitch ring, 4.9 mm: the 22 x 16.4 x 4 mm community sliding ring lengthened so it fills the gap under ID13.

    ~/.venvs/microduck-guide/bin/python print/neck-ring/thicken_ring.py

In the assembled model the 4 mm ring sits on the pitch bracket's shoulder and its top face stops 0.91 mm below the ID13
case (motor13 case face z 104.12, ring top z 103.21). Nothing surrounds its outside, so the ring floats and never takes
the tipping load it is there for. The hip-yaw rings, which work, touch both faces (yaw link below, torso base above).
Every vertex in the upper half of the ring moves +0.90 mm along the axis; the chamfers keep their shape. Output is in the
robot frame (print/world/neck_pitch_ring.stl) and a check record (thicken_ring.json).
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, trimesh
from trimesh.intersections import mesh_plane

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[1]
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
from ia_lib import decode_guide_part  # noqa: E402

EXTRA = 0.90
# Read the 4 mm source ring from the 10/1 print set rather than the guide data, which may already carry this output.
SRC = GUIDE.parent / 'team-share-20261001/02-STL-and-Editable-Projects/STL-Instances/plate-05/17_community-102.stl'


def main():
    g = json.loads((GUIDE / 'data' / 'guide-data.json').read_text())
    parts = {p['key']: p for p in g['parts']}
    motor = trimesh.Trimesh(*decode_guide_part(parts['motor13']), process=False)
    # Place the 10/1 source ring onto the 4 mm ring position the guide uses (pure translation; same orientation).
    src = trimesh.load(SRC, force='mesh', process=True)
    lo, hi = np.array([15.0, -11.0, 99.2146]), np.array([37.0, 11.0, 103.2146])
    assert np.allclose(np.sort(src.extents), [4, 22, 22], atol=0.01), src.extents
    assert int(np.argmin(src.extents)) == 2, 'source ring axis must be z'
    src.apply_translation((lo + hi) / 2 - src.bounds.mean(0))
    assert src.is_watertight
    c = src.bounds.mean(0)
    v = src.vertices.copy()
    v[v[:, 2] > c[2], 2] += EXTRA
    ring = trimesh.Trimesh(v, src.faces, process=True)
    assert ring.is_watertight and ring.is_volume
    # Motor case face over the ring annulus.
    face = None
    for z in np.arange(103.2, 104.6, 0.005):
        seg = mesh_plane(motor, [0, 0, 1], [c[0], c[1], z])
        if len(seg) and ((np.linalg.norm(seg.reshape(-1, 3)[:, :2] - c[:2], axis=1) > 8.3)
                         & (np.linalg.norm(seg.reshape(-1, 3)[:, :2] - c[:2], axis=1) < 10.9)).any():
            face = z
            break
    out = GUIDE / 'print' / 'world' / 'neck_pitch_ring.stl'
    ring.export(out)
    rec = dict(source=str(SRC), sourceSha256=hashlib.sha256(SRC.read_bytes()).hexdigest(), extraMm=EXTRA,
               thicknessMm=round(float(ring.extents[2]), 3), outerDiameterMm=round(float(ring.extents[0]), 3),
               boundsZ=[round(float(x), 3) for x in ring.bounds[:, 2]], motor13CaseFaceZ=round(float(face), 3),
               gapToCaseMm=round(float(face - ring.bounds[1, 2]), 3), volumeMm3=round(float(ring.volume), 2),
               output=str(out), outputSha256=hashlib.sha256(out.read_bytes()).hexdigest())
    (HERE / 'thicken_ring.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps(rec, indent=1))


if __name__ == '__main__':
    main()
