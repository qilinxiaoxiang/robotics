"""Rebind poses.json to changed ankle STLs when the change does not touch the chosen print pose's bed face.

    /tmp/microduck-cad-venv/bin/python scripts/rebind_geometry.py "<reason>" [key=expectedBedContactMm2:why ...]

For every part whose localStl sha256 no longer matches, the chosen sourceToPrint is applied to the new STL and the
result is compared with the pose's recorded bedContactMm2, heightMm and footprintMm (the old local STL has been
overwritten, so the recorded numbers stand for it). The rebind is refused unless the new bed contact is within 2 % of the
recorded one (or of an expected value given on the command line with the reason the bed face shrank or grew) and the
height and footprint within 0.05 mm, i.e. the part still stands on the same face the same way.
The previous sha256 and the measured values are kept under geometryRebinds. Support and bridging on the changed
faces are judged by the release's native slicing and review, not here.
"""
import hashlib, json, sys, datetime
from pathlib import Path
import numpy as np
import trimesh

POSES = Path(__file__).resolve().parents[1] / 'poses.json'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pose_numbers(path, T):
    m = trimesh.load(path, force='mesh', process=False).apply_transform(np.asarray(T, float))
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    area = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    ext = m.bounds[1] - m.bounds[0]
    return dict(bedContactMm2=round(area, 2), heightMm=round(float(ext[2]), 2), footprintMm=[round(float(ext[0]), 2), round(float(ext[1]), 2)])


def main():
    reason = sys.argv[1] if len(sys.argv) > 1 else ''
    assert reason.strip(), 'give the reason for the geometry change'
    expect = {}
    for a in sys.argv[2:]:
        k, rest = a.split('=', 1); v, why = rest.split(':', 1); assert why.strip(), a
        expect[k] = (float(v), why.strip())
    p = json.loads(POSES.read_text()); bad = []
    for key, e in p['parts'].items():
        stl = e['localStl']['path']; new_sha = sha(stl)
        if new_sha == e['localStl']['sha256']:
            continue
        c = e['chosen']; now = pose_numbers(stl, c['sourceToPrint'])
        target, why = expect.get(key, (c['bedContactMm2'], None))
        ok = (abs(now['bedContactMm2'] - target) <= 0.02 * target
              and abs(now['heightMm'] - c['heightMm']) <= 0.05
              and all(abs(a - b) <= 0.05 for a, b in zip(sorted(now['footprintMm']), sorted(c['footprintMm']))))
        print(key, 'recorded', {k: c[k] for k in ('bedContactMm2', 'heightMm', 'footprintMm')}, 'now', now, 'OK' if ok else 'REFUSED')
        if not ok:
            bad.append(key); continue
        e.setdefault('geometryRebinds', []).append(dict(date=datetime.date.today().isoformat(), previousSha256=e['localStl']['sha256'],
                                                       sha256=new_sha, reason=reason, chosenPoseNow=now,
                                                       **({'bedContactChange': why} if why else {})))
        e['localStl']['sha256'] = new_sha
    if bad:
        sys.exit(f'pose changed for {bad}: rerun the pose study for these parts')
    POSES.write_text(json.dumps(p, indent=1) + '\n')


if __name__ == '__main__':
    main()
