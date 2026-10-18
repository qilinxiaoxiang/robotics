"""V1.17: where the A7Z cap's new down-facing faces are, and where the extra native support sits (read-only).

    /tmp/microduck-cad-venv/bin/python scripts/a7z_overhang_clusters.py

New faces of the A7Z cap (not on the V1.9 cap surface) that face down more than 45 deg in the V1.9 print pose, grouped into
connected patches: area, print z, robot-frame box and normal. Then, per machine, the support toolpath in the changed rail
region of the V1.17 and V1.16 White slices, split by robot y band (+Y slot end, middle, -Y slot end) and by robot z.
Writes review/a7z-overhang-clusters.json.
"""
import json, math, sys
from pathlib import Path
import numpy as np
import trimesh
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
sys.path.insert(0, str(HERE))
import printability_a7z as pa  # noqa: E402
import review_a7z_native as rn  # noqa: E402


def clusters():
    T = pa.V19['head_cap_v19']['sourceToPrint']
    new, Tp = pa.posed(pa.load_mesh(PRINT / 'a7z-head/head_cap_a7z-world.stl'), T); old, _ = pa.posed(pa.load_mesh(PRINT / 'ext-v19/head_cap_v19-world.stl'), T)
    d = pa.dist(old, new.triangles_center); n = new.face_normals
    sel = np.nonzero((d > 0.005) & (-n[:, 2] > math.sin(math.radians(45))))[0]
    sub = new.submesh([sel], append=True); comps = sub.split(only_watertight=False)
    Tinv = np.linalg.inv(Tp); out = []
    for c in comps:
        w = (np.c_[c.vertices, np.ones(len(c.vertices))] @ Tinv.T)[:, :3]; nz = float((c.face_normals[:, 2] * c.area_faces).sum() / c.area)
        out.append(dict(areaMm2=round(float(c.area), 2), printZ=[round(float(c.vertices[:, 2].min()), 2), round(float(c.vertices[:, 2].max()), 2)],
                        robotBox=[np.round(w.min(0), 1).tolist(), np.round(w.max(0), 1).tolist()], meanNormalZ=round(nz, 3),
                        printExtentXY=np.round(c.extents[:2], 2).tolist()))
    return sorted(out, key=lambda x: -x['areaMm2'])


def bands(run, machine, key):
    prep, row, g, segs, arch, _ = rn.payload(run, 'White', machine); Tm, b = rn.placed(prep, row, key)
    P, L = rn.support_points(segs)
    W = (np.c_[P, np.ones(len(P))] @ np.linalg.inv(Tm).T)[:, :3]
    ch = np.all(W >= rn.CHANGED['lo'], axis=1) & np.all(W <= rn.CHANGED['hi'], axis=1)
    res = {}
    for name, lo, hi in (('+Y end (y 20..37)', 20, 37), ('middle (|y| < 20)', -20, 20), ('-Y end (y -37..-20)', -37, -20)):
        m = ch & (W[:, 1] >= lo) & (W[:, 1] < hi)
        res[name] = dict(supportMm=round(float(L[m].sum()), 1), robotZ=[round(float(W[m, 2].min()), 1), round(float(W[m, 2].max()), 1)] if m.any() else None,
                         robotX=[round(float(W[m, 0].min()), 1), round(float(W[m, 0].max()), 1)] if m.any() else None)
    return res


def main():
    out = dict(newDownFacingPatches=clusters())
    for machine in ('Bambu', 'Elegoo'):
        out[machine] = dict(before=bands(PRINT / 'release-V1.16/run', machine, 'head_cap_v19_white'), after=bands(REL / 'run', machine, 'head_cap_a7z'))
    (REL / 'review/a7z-overhang-clusters.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
