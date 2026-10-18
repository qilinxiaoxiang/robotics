#!/usr/bin/env python3
"""Cache the V1.6 robot-frame meshes used by the fastener audit as .npz files.

Two mesh sets are written to --out:
  full/<key>.npz   full-resolution world meshes: full-build-data-current.json parts (motors undecimated), with the V1.6
                   head cap, OpenRB tray and OpenRB board from guide/print/world, and the V1.6 release jaw support
                   (jaw_support_original-print.stl) registered back to the robot frame.
  guide/<key>.npz  the exact meshes the viewer draws (guide/data/guide-data.json; motors decimated).
A manifest records every source path and sha256.
"""
import argparse, base64, hashlib, json
from pathlib import Path
import numpy as np, trimesh

G = Path(__file__).resolve().parents[2]
SRC = G / 'data/sources/full-build-data-current.json'
GUIDE = G / 'data/guide-data.json'
REL = G / 'print/release-V1.6-final/final-V1.6.json'
WORLD = G / 'print/world'
SKIP = ('head_pi_zero_w_header_pin_', 'head_pi_gpio_pin_')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dec(p):
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    return v, f


def save(out, key, v, f, src):
    np.savez_compressed(out / f'{key}.npz', v=v, f=f)
    return {'key': key, 'faces': int(len(f)), 'source': src}


def register(moving: trimesh.Trimesh, fixed: trimesh.Trimesh):
    """Find the axis-permutation/sign rigid transform plus translation that best maps moving onto fixed.
    Both meshes are the same printed body exported in different poses; scored by mean nearest-vertex distance."""
    best = None
    fixed_pts = fixed.vertices
    tree = trimesh.proximity.ProximityQuery(fixed)
    import itertools
    sample = moving.vertices[np.random.default_rng(0).choice(len(moving.vertices), min(800, len(moving.vertices)), replace=False)]
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            R = np.zeros((3, 3))
            for i, (j, s) in enumerate(zip(perm, signs)):
                R[i, j] = s
            if np.linalg.det(R) < 0:
                continue
            mv = moving.vertices @ R.T
            t = (fixed.bounds.mean(0) - (mv.min(0) + mv.max(0)) / 2)
            if np.abs((mv.max(0) - mv.min(0)) - (fixed.bounds[1] - fixed.bounds[0])).max() > 0.05:
                continue
            d = np.abs(tree.signed_distance(sample @ R.T + t)).mean()
            if best is None or d < best[0]:
                best = (d, R, t)
    T = np.eye(4); T[:3, :3] = best[1]; T[:3, 3] = best[2]
    return T, float(best[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out); (out / 'full').mkdir(parents=True, exist_ok=True); (out / 'guide').mkdir(parents=True, exist_ok=True)
    man = {'sources': {str(SRC): sha(SRC), str(GUIDE): sha(GUIDE), str(REL): sha(REL)}, 'full': [], 'guide': []}

    gd = json.loads(GUIDE.read_text())
    for p in gd['parts']:
        if p['key'].startswith(SKIP):
            continue
        v, f = dec(p)
        man['guide'].append(save(out / 'guide', p['key'], v, f, 'guide-data.json'))
    del gd

    src = json.loads(SRC.read_text())
    for p in src['parts']:
        if p['key'].startswith(SKIP) or p['key'] in ('openrb', 'head_cap', 'jaw_support'):
            continue
        v, f = dec(p)
        man['full'].append(save(out / 'full', p['key'], v, f, 'full-build-data-current.json'))
    full_jaw = None
    for p in src['parts']:
        if p['key'] == 'jaw_support':
            full_jaw = trimesh.Trimesh(*dec(p), process=False)
    del src

    for key, name in (('head_cap', 'head_cap.stl'), ('openrb_tray', 'openrb_tray.stl'), ('openrb_board', 'openrb-board.stl')):
        m = trimesh.load(WORLD / name, force='mesh')
        man['full'].append(save(out / 'full', key, np.asarray(m.vertices, float), np.asarray(m.faces, np.int64), str(WORLD / name)))
        man['sources'][str(WORLD / name)] = sha(WORLD / name)

    rel = json.loads(REL.read_text())
    jaw = next(p for p in rel['parts'] if p['key'] == 'jaw_support_original')
    m = trimesh.load(jaw['path'], force='mesh')
    T, err = register(m, full_jaw)
    m.apply_transform(T)
    man['full'].append(save(out / 'full', 'jaw_support', np.asarray(m.vertices, float), np.asarray(m.faces, np.int64), jaw['path']))
    man['sources'][jaw['path']] = sha(jaw['path'])
    man['jawSupportRegistration'] = {'printToWorld': T.round(6).tolist(), 'meanAbsSurfaceDistanceMm': round(err, 4),
                                     'note': 'V1.6 print mesh mapped onto the guide jaw_support pose by the best axis-permutation rotation plus bounds-centre translation.'}
    np.savez_compressed(out / 'full' / 'jaw_support_guide_pose.npz', v=full_jaw.vertices, f=full_jaw.faces)
    (out / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps({'full': len(man['full']), 'guide': len(man['guide']), 'jaw': man['jawSupportRegistration']}, indent=1))


if __name__ == '__main__':
    main()
