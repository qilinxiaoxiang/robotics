"""MicroDuck Dual Lock back plate (DESIGN-CONTRACT.json, 2026-10-31). World = guide frame, mm (x forward, y left, z up).
The plate replaces the V1.8 rear pack cover: same outline (rear-pack/build_rear_pack.py COVER) and the same four M2 x 6
into the pack posts, 3 mm thick (x -48..-45), no lip, no counterbores (a dia 4.4 counterbore at |y| 16.1 left a 0.3 mm
sliver to the 18.6 edge; the pan heads stand on the rear face outside the Dual Lock area, 3 mm of thread in the 4.8 pilots). Both backpacks stick to its rear face
(x -48) with Dual Lock. A top notch (|y| <= 13.5, z 27.0 up) lets the charger box's old front lip (|y| <= 13.2,
z 27.3..28.5) pass. Writes build/duallock_plate-{world,print}.stl and build/build.json with the fit check.
Run with the CAD venv: /tmp/microduck-cad-venv/bin/python build_plate.py
"""
import json, sys
from pathlib import Path
import numpy as np
import trimesh
HERE = Path(__file__).resolve().parent; OUT = HERE / 'build'; OUT.mkdir(exist_ok=True)
PRINT = HERE.parents[1]
sys.path.insert(0, str(PRINT / 'rear-pack'))
sys.argv = sys.argv[:1]                                   # build_rear_pack reads optional chamfer args from argv
import build_rear_pack as B                               # noqa: E402
P = B.P

X_REAR, X_FRONT = -48.0, -45.0                            # Dual Lock face, pack-post face
NOTCH = dict(hy=13.5, z0=27.0)                            # lip |y| 13.2 + 0.3, lip bottom 27.3 - 0.3
# print pose as the V1.8 cover (release-V1.8 rear_pack_cover): the Dual Lock face (x -48) flat on the bed, robot y -> print x
SOURCE_TO_PRINT = [[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, -X_REAR], [0, 0, 0, 1]]


def build():
    B.COVER = dict(B.COVER, x0=X_REAR, x1=X_FRONT)
    plate = B.build_cover() - P.box((X_FRONT, -40, -60), (-30, 40, 40))              # drop the lip (x > -45)
    plate = plate - P.box((X_REAR - 1, -NOTCH['hy'], NOTCH['z0']), (X_FRONT + 1, NOTCH['hy'], 40))
    # square lower corners: the cover's 45-degree corners (following the post undersides) left 0.8 mm from the lower holes
    # to the edge; the plate sits inside the backpack front-plate outline, so the corners add nothing visible
    c = B.COVER
    for s in (1, -1):
        plate = plate + P.box((X_REAR, min(s * c['low_half_w'], s * c['half_w']), c['low_z']),
                              (X_FRONT, max(s * c['low_half_w'], s * c['half_w']), c['low_z'] + 3.4))
    for (y, z) in B.POST['holes']:
        plate = plate - P.cyl_x(c['hole_r'], X_REAR - 1, X_FRONT + 1, y, z)
    return plate


def fit(mesh):
    """overlap volume with every world part at rest except the pack (face contact by design), the old cover it replaces
    and the two backpacks with their contents (they move back by the plate and the Dual Lock). openrb-board.stl and
    openrb_tray.stl are the retired flat OpenRB pose under the old tray (pack_lib.RETIRED); the fitted board is
    openrb-board-upright.stl."""
    world = PRINT / 'world'
    skip = ('rear_pack', 'battery_backpack', 'bp_', 'rear_frame', 'rear_lid', 'pd5991', 'xl4015', 'openrb-board.', 'openrb_tray')
    pm = P.mesh_to_m(mesh); res = {}
    lo, hi = mesh.bounds[0] - 3, mesh.bounds[1] + 3
    for f in sorted(world.glob('*.stl')):
        if f.name.startswith(skip):
            continue
        m = trimesh.load(f, force='mesh')
        if np.any(m.bounds[1] < lo) or np.any(m.bounds[0] > hi):
            continue
        try:
            v = P.volume(pm ^ P.mesh_to_m(m))
        except Exception as e:                            # non-manifold reference meshes: report, do not hide
            res[f.stem] = f'not checked ({type(e).__name__})'; continue
        d = float(np.min(np.abs(trimesh.proximity.signed_distance(m, mesh.vertices)))) if len(m.faces) < 400000 else None
        res[f.stem] = dict(overlap_mm3=round(v, 3), min_gap_mm=None if d is None else round(d, 2))
    return res


if __name__ == '__main__':
    man = build(); mesh = P.clean_mesh(man)
    mesh.export(OUT / 'duallock_plate-world.stl')
    pr = mesh.copy(); pr.apply_transform(np.array(SOURCE_TO_PRINT, float)); pr.export(OUT / 'duallock_plate-print.stl')
    info = dict(watertight=bool(mesh.is_watertight), bodies=len(mesh.split(only_watertight=False)),
                volume_mm3=round(float(mesh.volume), 1), bounds=np.round(mesh.bounds, 3).tolist(),
                print_bounds=np.round(pr.bounds, 3).tolist(), bed_face='Dual Lock face (x -48) down, as the V1.8 cover',
                source_to_print=SOURCE_TO_PRINT,
                bed_contact_mm2=round(float(pr.area_faces[np.max(np.abs(pr.triangles[:, :, 2]), axis=1) <= .01].sum()), 1),
                params=dict(X_REAR=X_REAR, X_FRONT=X_FRONT, NOTCH=NOTCH, holes=B.POST['holes']),
                thinnest_mm=dict(notch_to_hole=round(16.1 - B.COVER['hole_r'] - NOTCH['hy'], 2),
                                 hole_to_edge=round(B.COVER['half_w'] - 16.1 - B.COVER['hole_r'], 2),
                                 thread_in_post=round(6.0 - (X_FRONT - X_REAR), 2)),
                fit=fit(mesh))
    (OUT / 'build.json').write_text(json.dumps(info, indent=1))
    print(json.dumps({k: v for k, v in info.items() if k != 'fit'}, indent=1))
    bad = {k: v for k, v in info['fit'].items() if not isinstance(v, dict) or v['overlap_mm3'] > 0.01}
    print('fit: checked', len(info['fit']), 'parts; overlaps / unchecked:', bad or 'none')
    near = sorted(((v['min_gap_mm'], k) for k, v in info['fit'].items() if isinstance(v, dict) and v['min_gap_mm'] is not None))[:5]
    print('nearest:', near)
