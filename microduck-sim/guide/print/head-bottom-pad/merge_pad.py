"""Print the upper lip pad as part of the lower head shell.

The separate upper pad (source p.obj / ID40) was glued under the beak roof after the head was closed, and it sits right
under the two front head-closure screws (K-head_close-01/02 at x 75.6, y +/-39): once glued, the head could no longer be
opened. This script unions the pad into the V1.8 lower shell (strip already closed, ../head-bottom-strip/) and cuts a
5.2 mm driver hole through the pad under each front screw, coaxial with the shell's existing 5.2-6 mm screw-head pocket
(the M2.5 x 8 TAP head is 4.0 mm). The hole stops at z 112.2, below the tab the screw head bears on (z 112.31).
The pad top does not sit flush under the roof (a 0.3-0.8 mm glue gap at the rear, under 0.3 mm elsewhere), so the pad
outline, inset 0.05 mm, is extruded from z 108.5 to 110.3 to fill that gap; it stays under the roof top (z > 111 untouched).
Acceptance: one closed body, the pad volume added except the two holes, a clear 2.6 mm driver corridor under both
screws, and the shell outside the pad footprint unchanged. Writes ../world/head_bottom.stl and merge_pad.json.

    /tmp/microduck-cad-venv/bin/python merge_pad.py
"""
import base64, hashlib, json, math
from pathlib import Path
import numpy as np
import manifold3d as m3
import trimesh

HERE = Path(__file__).resolve().parent
SIM = HERE.parents[2]
CACHE = SIM / 'build-pack-20260913/redesign-20260913/head-redesign-20261008/camera-ribbon-repair/head-source-cache'
BEFORE = HERE / 'head_bottom-before-pad.stl'
OUT = HERE.parent / 'world/head_bottom.stl'
SCREWS = [(75.6, 39.0), (75.6, -39.0)]
HOLE_R, HOLE_Z = 2.6, (104.0, 112.2)
BRIDGE_INSET, BRIDGE_Z = 0.05, (108.5, 110.3)


def man(v, f):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(v, np.float32), tri_verts=np.asarray(f, np.uint32)))


def source(key):
    idx = json.loads((CACHE / 'index.json').read_text())
    p = json.loads((CACHE / idx['parts'][key]).read_text())
    v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
    f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
    return trimesh.Trimesh(v, f, process=True)


def main():
    if not BEFORE.exists():
        BEFORE.write_bytes(OUT.read_bytes())
    old = trimesh.load(BEFORE)
    cur = man(old.vertices, old.faces)
    pt = source('upper_pad')
    pad = man(pt.vertices, pt.faces)
    holes = m3.Manifold.batch_boolean([m3.Manifold.cylinder(HOLE_Z[1] - HOLE_Z[0], HOLE_R, circular_segments=48).translate([x, y, HOLE_Z[0]])
                                       for x, y in SCREWS], m3.OpType.Add)
    assert (cur ^ holes).volume() < 1e-6, 'the driver hole would cut the shell itself'
    bridge = pad.project().offset(-BRIDGE_INSET, m3.JoinType.Miter).extrude(BRIDGE_Z[1] - BRIDGE_Z[0]).translate([0, 0, BRIDGE_Z[0]])
    gapfill = bridge - cur - pad
    pieces = ((cur + pad + bridge) - holes).decompose()
    assert len(pieces) == 1, [m.volume() for m in pieces]
    new = max(pieces, key=lambda m: m.volume())
    mm = new.to_mesh()
    t = trimesh.Trimesh(mm.vert_properties[:, :3].astype(np.float64), mm.tri_verts.astype(np.int64), process=False)
    t.export(OUT)
    r = trimesh.load(OUT)
    # driver corridor: rays straight down from just under each screw seat must not hit the new shell
    corridor = {}
    for x, y in SCREWS:
        O = np.array([[x + rr * math.cos(a), y + rr * math.sin(a), 112.25] for rr in (0.0, 1.0, 2.0, 2.5) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)])
        loc, ri, _ = r.ray.intersects_location(O, np.repeat([[0, 0, -1.0]], len(O), 0))
        corridor[f'{x},{y}'] = {'rays': len(O), 'blockedAbove95': int(len(set(ri[loc[:, 2] > 95].tolist())))}
    fp = m3.Manifold.cube([40, 96, 10]).translate([48, -48, 103])      # box around the pad footprint
    res = dict(before=str(BEFORE), out=str(OUT), screws=SCREWS, holeRadiusMm=HOLE_R, holeZ=HOLE_Z,
               padVolumeMm3=round(float(pad.volume()), 3), holeVolumeInPadMm3=round(float((pad ^ holes).volume()), 3),
               gapFillMm3=round(float(gapfill.volume()), 3), gapFillAboveZ111Mm3=round(float((gapfill ^ m3.Manifold.cube([200, 200, 10]).translate([-50, -100, 111.0])).volume()), 4),
               addedVolumeMm3=round(float(new.volume() - cur.volume()), 3), droppedPiecesMm3=[round(float(m.volume()), 4) for m in pieces if m is not new],
               shellChangeOutsidePadBoxMm3=round(float(((new - fp) - (cur - fp)).volume() + ((cur - fp) - (new - fp)).volume()), 4),
               genusBefore=int(cur.genus()), genusAfter=int(new.genus()), corridor=corridor,
               readback=dict(watertight=bool(r.is_watertight), windingConsistent=bool(r.is_winding_consistent), volume=round(float(r.volume), 3),
                             bodies=int(len(r.split(only_watertight=False))), faces=int(len(r.faces)), bounds=np.round(r.bounds, 3).tolist()),
               sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(), bytes=OUT.stat().st_size)
    (HERE / 'merge_pad.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    assert res['readback']['watertight'] and res['readback']['bodies'] == 1, 'not one closed body'
    assert res['gapFillAboveZ111Mm3'] == 0 and res['shellChangeOutsidePadBoxMm3'] == 0, 'material outside the pad seat'
    assert all(c['blockedAbove95'] == 0 for c in corridor.values()), 'driver corridor blocked'


if __name__ == '__main__':
    main()
