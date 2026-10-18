"""Copy the battery backpack (D-010) into guide/print/world for build_guide_data.py and the print gate.
Run after build_bp.py and release_rows.py. The printed frame and cap are the release-named world STLs; the bought parts
come from build/. The DFR1202 and its pads become one closed solid (manifold union).
    /tmp/microduck-cad-venv/bin/python to_guide_world.py"""
import hashlib, json, shutil
from pathlib import Path
import numpy as np, trimesh, manifold3d as m3
HERE = Path(__file__).resolve().parent; B = HERE / 'build'
WORLD = HERE.parents[1] / 'world'
COPY = {'battery_backpack_frame.stl': HERE / 'battery_backpack_frame-world.stl',
        'battery_backpack_cap.stl': HERE / 'battery_backpack_cap-world.stl',
        'bp_switch.stl': B / 'switch-world.stl', 'bp_battery.stl': B / 'battery-world.stl',
        'bp_plugs.stl': B / 'plugs-world.stl', 'bp_swap_plugs.stl': B / 'swap_plugs-world.stl'}


def man(p):
    m = trimesh.load(p, force='mesh', process=True)
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


out = {}
for name, src in COPY.items():
    shutil.copyfile(src, WORLD / name)
    out[name] = str(src)
u = (man(B / 'dfr1202-world.stl') + man(B / 'dfr_pads-world.stl')).to_mesh()
d = trimesh.Trimesh(np.asarray(u.vert_properties)[:, :3], np.asarray(u.tri_verts), process=False)
assert d.is_watertight and d.is_volume
d.export(WORLD / 'bp_dfr1202.stl')
out['bp_dfr1202.stl'] = 'build/dfr1202-world.stl + build/dfr_pads-world.stl'
sha = {n: hashlib.sha256((WORLD / n).read_bytes()).hexdigest() for n in out}
(HERE / 'guide-world.json').write_text(json.dumps({'world': str(WORLD), 'sources': out, 'sha256': sha}, indent=1) + '\n')
print(WORLD, {n: s[:12] for n, s in sha.items()})
