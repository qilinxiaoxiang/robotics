"""Exact clearance of a board box at one pose against every closed gate solid and drawn cable (no voxels)."""
import json, sys
from pathlib import Path
import numpy as np, trimesh
from scipy.spatial.transform import Rotation as R
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'content' / 'interference-audit'))
from ia_lib import load_solid, manifest, load_guide  # noqa: E402

dims, ypr, centre = json.loads(sys.argv[1]), json.loads(sys.argv[2]), np.array(json.loads(sys.argv[3]))
box = trimesh.creation.box(extents=dims)
T = np.eye(4); T[:3, :3] = R.from_euler('zyx', ypr, degrees=True).as_matrix(); T[:3, 3] = centre
box.apply_transform(T)
pts = np.vstack([box.vertices, trimesh.sample.sample_surface_even(box, 6000, seed=0)[0]])
lo, hi = box.bounds[0] - 15, box.bounds[1] + 15
res = []
for k, m in manifest().items():
    b = np.array(m['bounds'])
    if np.any(b[1] < lo) or np.any(b[0] > hi):
        continue
    v, f = load_solid(k)
    s = trimesh.Trimesh(v, f, process=False)
    dist = trimesh.proximity.ProximityQuery(s).on_surface(pts)[1]
    pen = s.contains(pts).any() or box.contains(s.vertices).any()
    res.append((float(-dist.min() if pen else dist.min()), k, int(box.contains(s.vertices).sum())))
for c in load_guide()['cables']:
    p = np.array(c['path'], float)
    seg = np.concatenate([np.linspace(a, b, max(2, int(np.linalg.norm(b - a) / 0.5))) for a, b in zip(p[:-1], p[1:])])
    if np.all(seg.max(0) < lo) or np.all(seg.min(0) > hi):
        continue
    r = float(c.get('radius') or 0.9)
    dist = trimesh.proximity.ProximityQuery(box).on_surface(seg)[1] * np.where(box.contains(seg), -1, 1)
    res.append((float(dist.min() - r), 'cable:' + c['id'], 0))
res.sort()
for gap, k, n in res[:10]:
    print(f'{gap:7.2f} mm  {k}' + (f'  ({n} solid vertices inside the box)' if n else ''))
print('box corners', np.round(box.bounds, 1).tolist())
