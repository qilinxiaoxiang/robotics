"""Write the V1.18 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.18 is a delta package: only the D-010 battery backpack frame and cap on one Orange plate. Shawn started printing V1.17 on
2026-10-15 ("1.18可以把1.17里面剔除掉"), so V1.17 stays the print baseline and none of its parts are re-issued. The profiles, baseline stock and
delivery rules come from the released manifest-V1.17.json (pinned by sha256); the parts are the two Orange rows from
back-plate/battery-backpack-20261015/release-rows-orange.json (rim-down frame and rear-face-down cap, the rear_frame / rear_lid
print axes), side by side at y 22 (x 20.0 and 96.1, 12 mm apart). White process overrides and the retired-parts list are dropped.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.18.json]
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V117_PATH = PRINT / 'release-V1.17/manifest-V1.17.json'
V117_SHA = '00af527717f3e4e7c5a0ba3042b2d0ac3958ab08d9603c6b6eb5fbad8736cb9d'
BP = PRINT / 'back-plate/battery-backpack-20261015'
ORANGE = [('battery_backpack_frame', 20.0, 22.0), ('battery_backpack_cap', 96.1, 22.0)]
DELTA = [k for k, _, _ in ORANGE]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p); assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def rebind(parts):
    """V1.17 evidence files rewritten since its release (the A7Z session reran build_face_a7z.py at 12:31 on 2026-10-15) are
    rebound to their current sha256 only when the part's STL is byte-identical to V1.17's and a rewritten checks file still
    names that STL sha256. Every STL (part, print pose) must be unchanged: V1.18 reprints none of the V1.17 geometry."""
    out = []
    for p in parts:
        assert sha(p['path']) == p['sha256'], f"{p['key']}: STL changed since V1.17"
        refs = [('incrementalEvidence', p['incrementalEvidence'])] + [(f'evidenceAlso[{i}]', r) for i, r in enumerate(p.get('evidenceAlso', []))]
        if p.get('poseCheck', {}).get('printStl'):
            refs.append(('poseCheck.printStl', p['poseCheck']['printStl']))
        for where, r in refs:
            new = sha(r['path'])
            if new == r['sha256']:
                continue
            assert not r['path'].endswith('.stl'), f"{p['key']} {where}: STL changed since V1.17"
            if r['path'].endswith('checks.json'):
                named = json.dumps(json.loads(Path(r['path']).read_text()))
                assert p['sha256'] in named, f"{p['key']} {where}: rewritten checks no longer name the released STL"
            out.append({'part': p['key'], 'ref': where, 'path': r['path'], 'v117Sha256': r['sha256'], 'sha256': new})
            r['sha256'] = new
    return out


def printed(path, T):
    m = trimesh.load(path, force='mesh', process=False)
    v, inv = np.unique(m.vertices, axis=0, return_inverse=True)
    m = trimesh.Trimesh(v, inv.reshape(-1)[m.faces], process=False); m.apply_transform(np.array(T, float))
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    area = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    return area, (m.bounds[1] - m.bounds[0]).round(2).tolist(), m.bounds[0]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.18.json'); a = ap.parse_args()
    assert sha(V117_PATH) == V117_SHA, 'manifest-V1.17.json changed since V1.18 was set up'
    m = json.loads(V117_PATH.read_text())
    parts = []   # delta: V1.17 is being printed (Shawn 2026-10-15), so none of its parts are re-issued
    for r in json.loads((BP / 'release-rows-orange.json').read_text()):
        src = ref(r['path']); assert src['sha256'] == r['sha256'], f"{r['key']}: STL changed after release_rows.py"
        area, size, _ = printed(src['path'], r['sourceToPrint'])
        assert r['flatContactMinimumMm2'] <= area, f"{r['key']}: bed contact {area:.1f} below {r['flatContactMinimumMm2']}"
        key = r['key']
        parts.append(dict(key=key, color='Orange', quantity=1, decision=r['decision'], replacesStockIds=[], path=src['path'], sha256=src['sha256'],
                          sourceFrame='robot frame (mm, x forward, y left, z up)', sourceToPrint=r['sourceToPrint'],
                          flatContact={'minimumAreaMm2': r['flatContactMinimumMm2'], 'reason': r['flatContactMinimumReason']},
                          poseOrigin=r['poseOrigin'],
                          poseCheck=dict(printStl=ref(BP / f"{key}-print.stl"), bedContactMm2=round(area, 2), printSizeMm=size,
                                         note='contact from the world STL with the row sourceToPrint'),
                          changeReason=r['changeReason'], supersedes=r['supersedes'], incrementalEvidence=ref(r['incrementalEvidence']),
                          evidenceAlso=[ref(x) for x in r['evidenceAlso']], supportBlockers=[]))
    by = {p['key']: p for p in parts}
    assert sorted(k for k, _, _ in ORANGE) == sorted(p['key'] for p in parts if p['color'] == 'Orange')
    pl = []
    for key, x0, y0 in ORANGE:
        _, size, lo = printed(by[key]['path'], by[key]['sourceToPrint'])
        assert 18.0 <= x0 and x0 + size[0] <= 238.0 and 18.0 <= y0 and y0 + size[1] <= 238.0, (key, x0, y0, size)
        pl.append(dict(key=key, copy=1, translation=[round(x0 - float(lo[0]), 4), round(y0 - float(lo[1]), 4), 0.0]))
    m['parts'] = parts
    m['placements'] = {'Orange': pl}
    m['processOverrides'] = {k: v for k, v in m['processOverrides'].items() if k.split('_')[0] == 'Orange'}
    m['processOverrideReason'] = 'No process overrides: the White cap overrides of V1.12-V1.17 apply to the White plate, which V1.18 does not carry.'
    m['retiredParts'] = []
    m['version'] = 'V1.18'
    m['prototypeScope'] = ('V1.18 delta package: only the D-010 battery backpack frame and cap on one Orange plate. V1.17 is the printed '
                           'baseline (Shawn started printing it on 2026-10-15: "1.18可以把1.17里面剔除掉"), so none of its parts are re-issued.')
    m['knownFitBoundary'] += (' Battery backpack: built for the Tattu 2S 650 listing size (57 x 31 x 12 mm) in a 58 x 32 x 13 pocket; '
                              'measure the pack before printing if it may be larger. It mounts on the same four cover screws as the '
                              'rear converter box (swap one for the other); cap 3 x M2 x 6, fixing 4 x M2 x 6.')
    dc = m['deliveryContract']
    dc.update(colors=['Orange'], fileCount=2,
              baseline='printed V1.8 set, the V1.9 Orange plate and V1.17 (printing since 2026-10-15)',
              supersedes=['the first V1.18 cut of 2026-10-15 13:35 (all of V1.17 plus the backpack), replaced the same day before printing'])
    a.out.write_text(json.dumps(m, indent=1))
    print(json.dumps(dict(out=str(a.out), orange=[(p['key'], p['poseCheck']['bedContactMm2']) for p in parts if p['color'] == 'Orange'],
                          placements=pl), indent=1))


if __name__ == '__main__':
    main()
