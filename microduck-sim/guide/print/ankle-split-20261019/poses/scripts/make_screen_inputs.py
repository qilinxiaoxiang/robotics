#!/usr/bin/env python3
"""Write the screening inputs for the six split-ankle parts (ankle-redesign-20261007/PRINT-STL):
  manifest-screen.json   13-RELEASE-PIPELINE-format part rows, path = PRINT-STL file, sourceToPrint = identity
                         (the PRINT files are already the 10/07 trial poses, bottom at z = 0, XY centred),
                         flatContact = the measured contact of that trial pose.
  extra-poses.json       named alternative poses per part, expressed in the PRINT-STL frame but named by the LOCAL
                         axis that faces the bed (print-review.json sourceLocalToPrint4x4 maps local -> PRINT frame):
                         base +X/-X/+Z/-Z down, cheek +Z/-Z/+X/-X/+Y/-Y down, sleeve +Z/-Z (axial) and +X (sideways).
  local-to-printstl.json the 10/07 matrices, copied from print-review.json, for composing final local-frame poses.

    /tmp/microduck-cad-venv/bin/python make_screen_inputs.py
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; OUT = HERE.parent
SIM = Path('/Users/xiangzheng/code/robotics/microduck-sim')
ANKLE = SIM / 'build-pack-20260913/redesign-20260913/ankle-redesign-20261007'
STUDY = SIM / 'guide/print/orientation-study'
sys.path.insert(0, str(STUDY)); sys.dont_write_bytecode = True
from orientation_check import load_mesh, rotation_to_down, min_area_yaw, normalise  # noqa: E402

KEYS = ['left_base', 'right_base', 'left_cheek', 'right_cheek', 'left_sleeve', 'right_sleeve']
COLOR = {'base': 'Orange', 'cheek': 'Orange', 'sleeve': 'Black'}
LOCAL_DOWN = {  # local axis that faces the bed, per part type
    'base': {'+X': [1, 0, 0], '-X': [-1, 0, 0], '+Z': [0, 0, 1], '-Z': [0, 0, -1], '+Y': [0, 1, 0], '-Y': [0, -1, 0]},
    'cheek': {'+Z': [0, 0, 1], '-Z': [0, 0, -1], '+X': [1, 0, 0], '-X': [-1, 0, 0], '+Y': [0, 1, 0], '-Y': [0, -1, 0]},
    'sleeve': {'-Z': [0, 0, -1], '+Z': [0, 0, 1], '+X': [1, 0, 0]},
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    review = json.loads((ANKLE / 'print-review.json').read_text())
    rows = {c['key']: c for c in review['candidate_reviews']}
    parts, extras, l2p = [], {}, {}
    for key in KEYS:
        side, kind = key.split('_')
        c = rows[key]; pe = c['print_export']
        print_stl = Path(pe['file']); assert sha(print_stl) == pe['sha256'], key
        local_stl = Path(c['file']); assert sha(local_stl) == c['sha256'], key
        L = np.array(pe['sourceLocalToPrint4x4'], float)
        l2p[key] = dict(localStl=str(local_stl), localSha256=c['sha256'], printStl=str(print_stl), printSha256=pe['sha256'],
                        localToPrintStl=L.tolist(), trialName=c.get('recommended_orientation') or 'local_positive_Z_down (trial only)')
        m = load_mesh(print_stl)
        contact = float(m.area_faces[m.triangles[:, :, 2].max(1) <= 0.01].sum())
        parts.append(dict(key=key, color=COLOR[kind], quantity=1, decision='addition', replacesStockIds=[],
                          path=str(print_stl), sha256=pe['sha256'], sourceToPrint=np.eye(4).tolist(),
                          flatContact={'minimumAreaMm2': round(contact * 0.95, 2)},
                          sourceFrame='PRINT-STL frame of the 10/07 trial pose (bottom z = 0, XY centred)',
                          changeReason='orientation screen input only', incrementalEvidence={'path': str(ANKLE / 'print-review.json'), 'sha256': sha(ANKLE / 'print-review.json')}))
        # Alternative poses: a local axis faces the bed; yaw to the minimum footprint; drop to the bed (orientation_check rules).
        ex = []
        R_l2p = L[:3, :3]
        for name, d_local in LOCAL_DOWN[kind].items():
            d_print = R_l2p @ np.array(d_local, float)
            R = rotation_to_down(d_print)
            yaw = min_area_yaw((m.convex_hull.vertices @ R.T)[:, :2])
            cs, sn = np.cos(yaw), np.sin(yaw)
            T = np.eye(4); T[:3, :3] = np.array([[cs, -sn, 0], [sn, cs, 0], [0, 0, 1.0]]) @ R
            T = normalise(m, T)
            ex.append(dict(name=f'local {name} down', localDown=d_local, sourceToPrint=T.tolist()))
        extras[key] = ex
    base = json.loads((SIM / 'guide/print/release-V1.22/manifest-V1.22.json').read_text())
    manifest = dict(schemaVersion=1, releaseKind='incremental', version='SCREEN-ankle-split-20261019', prototype=True,
                    prototypeScope='ORIENTATION SCREEN ONLY, NOT A RELEASE: the six split-ankle parts in their 10/07 trial poses.',
                    baselineStock=base['baselineStock'], profiles=base['profiles'], parts=parts)
    (OUT / 'manifest-screen.json').write_text(json.dumps(manifest, indent=1) + '\n')
    (OUT / 'extra-poses.json').write_text(json.dumps(extras, indent=1) + '\n')
    (OUT / 'local-to-printstl.json').write_text(json.dumps(l2p, indent=1) + '\n')
    print(json.dumps({p['key']: p['flatContact'] for p in parts}))


if __name__ == '__main__':
    main()
