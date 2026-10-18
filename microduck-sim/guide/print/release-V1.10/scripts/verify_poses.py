"""Check that each V1.10 row's sourceToPrint reproduces the given back-plate print STL from the world STL, and measure
the bed contact with the release pipeline's rule (triangles within 0.01 mm of the bed after dropping to z = 0).

    /tmp/microduck-cad-venv/bin/python scripts/verify_poses.py      (writes pose-check.json next to rows.json)

Read-only on the back-plate sources. Vertices are compared after the pipeline's exact deduplication, as sorted sets.
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
BP = HERE.parents[1] / 'back-plate'
PRINT_STL = {'rear_frame': BP / 'rear_frame-print.stl', 'rear_lid': BP / 'rear_lid-print.stl'}


def load(p):
    m = trimesh.load(p, force='mesh', process=False)
    v, inv = np.unique(m.vertices, axis=0, return_inverse=True)
    return trimesh.Trimesh(v, inv.reshape(-1)[m.faces], process=False)


def main():
    rows = json.loads((HERE / 'rows.json').read_text()); out = {}
    ok = True
    for r in rows:
        T = np.array(r['sourceToPrint'], float)
        w = load(r['path']); w.apply_transform(T)
        p = load(PRINT_STL[r['key']])
        a = np.unique(np.round(w.vertices, 4), axis=0); b = np.unique(np.round(p.vertices, 4), axis=0)
        same_count = a.shape == b.shape
        maxdev = float(np.abs(a - b).max()) if same_count else None
        bdev = float(np.abs(w.bounds - p.bounds).max())
        # pipeline flat-contact rule on the transformed world mesh
        m = w.copy(); m.apply_translation([0, 0, -m.bounds[0, 2]])
        at_bottom = np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01
        contact = float(m.area_faces[at_bottom].sum())
        good = same_count and maxdev is not None and maxdev < 1e-3 and bdev < 1e-3 and abs(float(w.bounds[0, 2])) < 1e-6
        ok &= good
        out[r['key']] = dict(world=str(r['path']), worldSha256=hashlib.sha256(Path(r['path']).read_bytes()).hexdigest(),
                             printStl=str(PRINT_STL[r['key']]), printSha256=hashlib.sha256(PRINT_STL[r['key']].read_bytes()).hexdigest(),
                             vertexCountWorld=int(len(a)), vertexCountPrint=int(len(b)), maxVertexDeviationMm=maxdev,
                             maxBoundsDeviationMm=bdev, transformedBounds=w.bounds.round(4).tolist(), printBounds=p.bounds.round(4).tolist(),
                             bedContactMm2=round(contact, 2), flatContactMinimumMm2=r['flatContactMinimumMm2'],
                             minimumBelowContact=r['flatContactMinimumMm2'] <= contact, passed=bool(good and r['flatContactMinimumMm2'] <= contact))
        ok &= out[r['key']]['passed']
    res = dict(passed=bool(ok), rule='sorted unique vertices (rounded 1e-4 mm) and bounds of T(world) equal the print STL within 1e-3 mm; '
               'contact = triangles within 0.01 mm of the bed (release_pipeline.source_receipt)', parts=out)
    (HERE / 'pose-check.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
