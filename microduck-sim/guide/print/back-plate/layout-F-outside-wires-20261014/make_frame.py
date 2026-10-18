"""Frame for the outside-wire draft: the hidden-screw option frame (layout-F-ear-20261014/options/frame_hidden-world.stl,
Shawn's cap fixing choice 2026-10-14) with passage P1 filled solid (x -47..-45, y 2.9..12.7, z 12.5..15.3, the exact
plate volume P1 removed). Also checks the V1.11-based P1-free frame from build_f.py. Writes frame_hidden_noP1-world.stl
and frame_check.json."""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as m3
HERE = Path(__file__).resolve().parent
OPT = HERE.parent / 'layout-F-ear-20261014' / 'options'
sys.path.insert(0, str(HERE.parent.parent / 'rear-pack')); import pack_lib as P
def info(tm):
    man = P.mesh_to_m(tm)
    return dict(volume_mm3=round(float(man.volume()), 1), genus=int(man.genus()), watertight=bool(tm.is_watertight),
                bodies=sum(1 for q in tm.split(only_watertight=False) if abs(q.volume) > 1.0), bounds=np.round(tm.bounds, 2).tolist())
def p1_material(tm):
    """fraction of P1 sample points inside the solid"""
    g = np.stack(np.meshgrid(np.linspace(-46.9, -45.1, 4), np.linspace(3.2, 12.4, 8), np.linspace(12.8, 15.0, 4), indexing='ij'), -1).reshape(-1, 3)
    return round(float(np.mean(tm.contains(g))), 3)
out = {}
fh = trimesh.load(str(OPT / 'frame_hidden-world.stl'), force='mesh')
out['frame_hidden (P1 open)'] = dict(info(fh), p1MaterialFraction=p1_material(fh))
filled = P.mesh_to_m(fh) + P.box((-47.0, 2.9, 12.5), (-45.0, 12.7, 15.3))
tm = P.from_m(filled); tm.merge_vertices(); tm.export(HERE / 'frame_hidden_noP1-world.stl')
tm = trimesh.load(str(HERE / 'frame_hidden_noP1-world.stl'), force='mesh')
out['frame_hidden_noP1'] = dict(info(tm), p1MaterialFraction=p1_material(tm))
out['frame_hidden_noP1']['addedVolume_mm3'] = round(out['frame_hidden_noP1']['volume_mm3'] - out['frame_hidden (P1 open)']['volume_mm3'], 1)
v11 = trimesh.load(str(HERE / 'frame_F-world.stl'), force='mesh'); rel = trimesh.load(str(HERE.parent / 'layout-F' / 'rear_frame-world.stl'), force='mesh')
out['frame_V1.11_noP1 (build_f.py, P1 deleted)'] = dict(info(v11), p1MaterialFraction=p1_material(v11))
out['rear_frame V1.11 release'] = dict(info(rel), p1MaterialFraction=p1_material(rel))
for k in ('lid_hidden-world.stl', 'screw_hidden-world.stl'):
    out[k] = info(trimesh.load(str(OPT / k), force='mesh'))
(HERE / 'frame_check.json').write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps(out, indent=1))
