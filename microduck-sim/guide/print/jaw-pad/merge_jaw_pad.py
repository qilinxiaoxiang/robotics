"""Print the lower lip pad as part of the jaw frame.

The lower lip pad (source q.obj / ID42) was glued into its pocket on the jaw frame (source 4.obj / ID4). Glue is
irreversible and the pad has no other retention, so the two now print as one yellow part, upright as the 10/1 batch
printed the jaw (layers horizontal, so the arms flex within their layers when they are sprung into the shell). The pad
sits on the pocket floor with a 0-0.08 mm fit gap (95th percentile) and up to 1.8 mm over a few floor openings; a
0.9 mm bridge under the pad, its outline inset 1.5 mm so it stays over jaw material, ties the pad bottom to the floor.
Side gaps to the pocket walls stay as modelled (median 0.02 mm); the slicer closes the sub-0.1 mm ones.
Acceptance: one closed body, the bridge entirely above jaw material, and nothing changed outside the pad pocket box.
Writes ../world/jaw_frame.stl and merge_jaw_pad.json.

    /tmp/microduck-cad-venv/bin/python merge_jaw_pad.py
"""
import base64, hashlib, json
from pathlib import Path
import numpy as np
import manifold3d as m3
import trimesh

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]
CACHE = SIM / 'build-pack-20260913/redesign-20260913/head-redesign-20261008/camera-ribbon-repair/head-source-cache'
OUT = HERE.parent / 'world/jaw_frame.stl'
BRIDGE_INSET, BRIDGE_Z = 1.5, (99.4, 100.3)


def source(key):
    idx = json.loads((CACHE / 'index.json').read_text())
    p = json.loads((CACHE / idx['parts'][key]).read_text())
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    return trimesh.Trimesh(v, f, process=True)


def man(t):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def main():
    jt, pt = source('jaw_frame'), source('lower_pad')
    jaw, pad = man(jt), man(pt)
    outline = pad.project()
    bridge = outline.offset(-BRIDGE_INSET, m3.JoinType.Round).extrude(BRIDGE_Z[1] - BRIDGE_Z[0]).translate([0, 0, BRIDGE_Z[0]])
    extra = bridge - jaw - pad
    em = extra.to_mesh()
    ev = em.vert_properties[:, :3].astype(np.float64)
    over_jaw = jt.ray.intersects_any(ev - [0, 0, 0.01], np.tile([0, 0, -1.0], (len(ev), 1))) if len(ev) else np.array([True])
    pieces = (jaw + pad + bridge).decompose()
    assert len(pieces) == 1, [m.volume() for m in pieces]
    new = pieces[0]
    lo, hi = np.array(pt.bounds[0]) - 1.0, np.array(pt.bounds[1]) + 1.0
    box = m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())
    mm = new.to_mesh()
    trimesh.Trimesh(mm.vert_properties[:, :3].astype(np.float64), mm.tri_verts.astype(np.int64), process=False).export(OUT)
    r = trimesh.load(OUT)
    zmin = r.bounds[0][2]
    down = (r.face_normals[:, 2] < -0.999) & (np.abs(r.triangles_center[:, 2] - zmin) < 0.05)
    res = dict(out=str(OUT), jawVolumeMm3=round(float(jaw.volume()), 3), padVolumeMm3=round(float(pad.volume()), 3),
               padJawOverlapMm3=round(float((jaw ^ pad).volume()), 3), bridgeInsetMm=BRIDGE_INSET, bridgeZ=BRIDGE_Z,
               bridgeAddedMm3=round(float(extra.volume()), 3), bridgeVerticesOverJawFraction=round(float(np.mean(over_jaw)), 4),
               changeOutsidePadBoxMm3=round(float(((new - box) - (jaw - box)).volume() + ((jaw - box) - (new - box)).volume()), 5),
               genusJaw=int(jaw.genus()), genusAfter=int(new.genus()), volumeMm3=round(float(new.volume()), 3),
               bedContactUprightMm2=round(float(r.area_faces[down].sum()), 1),
               readback=dict(watertight=bool(r.is_watertight), bodies=int(len(r.split(only_watertight=False))),
                             bounds=np.round(r.bounds, 3).tolist(), faces=int(len(r.faces))),
               sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(), bytes=OUT.stat().st_size)
    (HERE / 'merge_jaw_pad.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    assert res['readback']['watertight'] and res['readback']['bodies'] == 1
    assert res['bridgeVerticesOverJawFraction'] == 1.0 and res['changeOutsidePadBoxMm3'] == 0


if __name__ == '__main__':
    main()
