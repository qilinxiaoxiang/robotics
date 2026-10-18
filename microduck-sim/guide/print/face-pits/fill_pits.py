"""Fill the three dead pits on the back of the V1.8 face panel.

The V1.6 face held the camera with a three-screw clamp (M2 x 4 TAP, camera-ribbon-repair/positive-x225/
camera-three-screw-clamp-report.json): its 2.8 mm pilots ran 0.58 mm into the 1.3 mm plate. V1.8 removed the clamp
anchors down to the plate's back face (x 80.1) but left those pilot bottoms as three blind pits (about 1.7 mm across,
0.58 mm deep) at (y, z) = (-18.09, 119.0), (-18.09, 147.2), (17.91, 147.2). Nothing uses them. Each pit is covered with
the plate's own plain material from 5 mm above it (a 4 x 4 mm patch through the full plate thickness), so the back face
stays one flat plane. Acceptance: one closed body, plate thickness 1.3 mm across each former pit, and no change
outside the three patches. Writes ../world/face_panel.stl and fill_pits.json.

    /tmp/microduck-cad-venv/bin/python fill_pits.py
"""
import hashlib, json
from pathlib import Path
import numpy as np
import manifold3d as m3
import trimesh

HERE = Path(__file__).resolve().parent
BEFORE = HERE / 'face_panel-before-pits.stl'
OUT = HERE.parent / 'world/face_panel.stl'
PITS = [(-18.09, 119.0), (-18.09, 147.2), (17.91, 147.2)]
HALF, DONOR_DZ = 2.0, 5.0


def main():
    if not BEFORE.exists():
        BEFORE.write_bytes(OUT.read_bytes())
    old = trimesh.load(BEFORE)
    cur = m3.Manifold(m3.Mesh(vert_properties=np.asarray(old.vertices, np.float32), tri_verts=np.asarray(old.faces, np.uint32)))
    patches, boxes = [], []
    for y, z in PITS:
        donor = m3.Manifold.cube([1.7, 2 * HALF, 2 * HALF]).translate([79.9, y - HALF, z + DONOR_DZ - HALF])
        patches.append((cur ^ donor).translate([0, 0, -DONOR_DZ]))
        boxes.append(m3.Manifold.cube([1.7, 2 * HALF, 2 * HALF]).translate([79.9, y - HALF, z - HALF]))
    pieces = (cur + m3.Manifold.batch_boolean(patches, m3.OpType.Add)).decompose()
    assert len(pieces) == 1, [m.volume() for m in pieces]
    new = pieces[0]
    allbox = m3.Manifold.batch_boolean(boxes, m3.OpType.Add)
    mm = new.to_mesh()
    trimesh.Trimesh(mm.vert_properties[:, :3].astype(np.float64), mm.tri_verts.astype(np.int64), process=False).export(OUT)
    r = trimesh.load(OUT)
    thick = {}
    for y, z in PITS:
        a, _, _ = r.ray.intersects_location([[60.0, y, z]], [[1.0, 0, 0]])
        thick[f'{y},{z}'] = np.sort(a[:, 0]).round(3).tolist()
    res = dict(before=str(BEFORE), out=str(OUT), pits=PITS, addedVolumeMm3=round(float(new.volume() - cur.volume()), 4),
               changeOutsidePatchesMm3=round(float(((new - allbox) - (cur - allbox)).volume() + ((cur - allbox) - (new - allbox)).volume()), 5),
               xHitsAtPits=thick, genusBefore=int(cur.genus()), genusAfter=int(new.genus()),
               readback=dict(watertight=bool(r.is_watertight), bodies=int(len(r.split(only_watertight=False))), volume=round(float(r.volume), 3),
                             bounds=np.round(r.bounds, 3).tolist()),
               sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(), bytes=OUT.stat().st_size)
    (HERE / 'fill_pits.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    assert res['readback']['watertight'] and res['readback']['bodies'] == 1
    assert all(len(v) == 2 and abs(v[0] - 80.1) < 0.005 and abs(v[1] - 81.4) < 0.005 for v in thick.values()), thick
    assert res['changeOutsidePatchesMm3'] == 0


if __name__ == '__main__':
    main()
