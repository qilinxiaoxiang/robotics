#!/usr/bin/env python3
"""Recover the 10/1 print pose for each V1.6 part that replaces a 10/1 stock instance.

The 10/1 STLs (printing/01-STL) are already in their printed pose: the 10/1 Bambu project applies only yaw to
them (checked in study notes). Each V1.6 source mesh is registered rigidly onto the stock mesh it replaces
(trimmed ICP from all 24 proper PCA-frame starts, no scaling or reflection). The resulting source->10/1-print matrix is written as an extra
candidate pose for orientation_check.py. Residuals show how much of the part changed; a pose is accepted only when
most of the new surface lies on the old one.

    run_bounded_cad.py ... -- /tmp/microduck-cad-venv/bin/python scripts/register_10_1.py OUT.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from orientation_check import load_mesh, normalise  # noqa: E402

FINAL = HERE.parent / 'release-V1.6-final' / 'final-V1.6.json'
PRINTING = HERE.parents[2] / 'build-pack-20260913' / 'redesign-20260913' / 'printing'
COPY = PRINTING / 'copy-manifest.json'


def residual(a, b, n=3000, seed=0):
    pts, _ = trimesh.sample.sample_surface(a, n, seed=seed)
    _, d, _ = trimesh.proximity.closest_point(b, pts)
    return d


def kabsch(p, q):
    """Proper rotation + translation minimising |R p + t - q|."""
    cp, cq = p.mean(0), q.mean(0)
    U, _, Vt = np.linalg.svd((p - cp).T @ (q - cq))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, cq - R @ cp


def register(new, old, n=4000, iters=60, keep=0.8):
    """Trimmed point-to-point ICP from all 24 proper rotations of the PCA frames; returns 4x4 new->old and RMS."""
    from scipy.spatial import cKDTree
    a, _ = trimesh.sample.sample_surface(new, n, seed=2)
    b, _ = trimesh.sample.sample_surface(old, 4 * n, seed=3)
    tree = cKDTree(b)
    ea = np.linalg.eigh(np.cov((a - a.mean(0)).T))[1]
    eb = np.linalg.eigh(np.cov((b - b.mean(0)).T))[1]
    starts = []
    for perm in ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)):
        for sx in (1, -1):
            for sy in (1, -1):
                for sz in (1, -1):
                    P = eb[:, perm] * np.array([sx, sy, sz])
                    R = P @ ea.T
                    if np.linalg.det(R) > 0:
                        starts.append(R)
    best = None
    for R in starts:
        t = b.mean(0) - R @ a.mean(0)
        for _ in range(iters):
            moved = a @ R.T + t
            d, j = tree.query(moved)
            sel = d <= np.quantile(d, keep)
            R2, t2 = kabsch(a[sel], b[j[sel]])
            done = np.allclose(R2, R, atol=1e-7) and np.allclose(t2, t, atol=1e-5)
            R, t = R2, t2
            if done:
                break
        d, _ = tree.query(a @ R.T + t)
        rms = float(np.sqrt(np.mean(np.sort(d)[: int(keep * len(d))] ** 2)))
        if best is None or rms < best[2]:
            best = (R, t, rms)
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = best[0], best[1]
    return T, best[2]


def main():
    out = Path(sys.argv[1])
    final = json.loads(FINAL.read_text())
    stock = {str(r['object_id']): r for r in json.loads(COPY.read_text())['copy_records'] if 'manifest_instance_index' in r}
    rows, extras = [], {}
    for p in final['parts']:
        ids = p.get('replacesStockIds') or []
        if not ids:
            continue
        rec = stock[str(ids[0])]
        old_path = PRINTING / rec['copy']
        new = load_mesh(p['path'])
        old = load_mesh(old_path)
        T, cost = register(new, old)
        best = (T, cost)
        R = T[:3, :3]
        assert np.allclose(R.T @ R, np.eye(3), atol=1e-6) and np.linalg.det(R) > 0.999, 'non-rigid registration'
        moved = new.copy()
        moved.apply_transform(T)
        d_new = residual(moved, old)
        d_old = residual(old, moved, seed=1)
        old_ext = old.extents
        row = dict(key=p['key'], stockObjectId=str(ids[0]), stockCopy=str(old_path), stockSha256=rec['sha256'],
                   stockExtentMm=[round(float(x), 2) for x in old_ext], newInOldPoseExtentMm=[round(float(x), 2) for x in moved.extents],
                   cost=float(best[1]),
                   newToOldMm=dict(p50=round(float(np.percentile(d_new, 50)), 3), p90=round(float(np.percentile(d_new, 90)), 3),
                                   within0p5=round(float(np.mean(d_new < 0.5)), 3)),
                   oldToNewMm=dict(p50=round(float(np.percentile(d_old, 50)), 3), p90=round(float(np.percentile(d_old, 90)), 3),
                                   within0p5=round(float(np.mean(d_old < 0.5)), 3)),
                   sourceTo10_1Print=normalise(new, T).tolist())
        row['accepted'] = row['newToOldMm']['within0p5'] >= 0.85 or (row['newToOldMm']['within0p5'] >= 0.6 and abs(row['newInOldPoseExtentMm'][2] - row['stockExtentMm'][2]) < 3)
        rows.append(row)
        if row['accepted']:
            extras[p['key']] = [dict(name='10/1 pose', sourceToPrint=row['sourceTo10_1Print'])]
        print(p['key'], ids[0], Path(rec['copy']).name, 'old', row['stockExtentMm'], 'new-in-old', row['newInOldPoseExtentMm'],
              'new->old', row['newToOldMm'], 'old->new', row['oldToNewMm'], 'accepted', row['accepted'])
        del new, old, moved
    out.write_text(json.dumps(dict(method='trimmed (80%) point-to-point ICP from the 24 proper rotations between PCA frames; rigid, no scale', rows=rows,
                                   extraPoses=extras), indent=1) + '\n')


if __name__ == '__main__':
    main()
