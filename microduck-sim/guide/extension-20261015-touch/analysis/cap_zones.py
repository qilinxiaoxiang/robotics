import sys, json, numpy as np, trimesh
from pathlib import Path
G = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print')
cap = trimesh.load(G/'a7z-head/head_cap_a7z-world.stl')
parts = {}
for p in (G/'a7z-head/a7z_parts').glob('*.stl'): parts['a7z:'+p.stem] = trimesh.load(p)
for n in ['speaker','speaker_retainer','amplifier','camera_board','face_panel','eye_trim','head_bottom','clip_head','clip_cap','jaw_frame','neck_pitch_ring']:
    parts[n] = trimesh.load(G/'world'/f'{n}.stl')
print('cap bounds', cap.bounds.round(1), 'watertight', cap.is_watertight)
for n,m in parts.items(): print(f'{n:28s}', m.bounds.round(1).tolist())
pts, fi = trimesh.sample.sample_surface_even(cap, 6000, seed=1)
nrm = cap.face_normals[fi]
# outer faces: ray along +normal escapes (no hit on cap)
ri = trimesh.ray.ray_triangle.RayMeshIntersector(cap)
eps = 0.05
hit_out = ri.intersects_any(pts + nrm*eps, nrm)
outer = ~hit_out
P, N = pts[outer], nrm[outer]
# thickness: ray inward
loc, idx, _ = ri.intersects_location(P - N*eps, -N, multiple_hits=False)
th = np.full(len(P), np.nan)
d = np.linalg.norm(loc - P[idx], axis=1); th[idx] = d
inner = P - N*np.nan_to_num(th, nan=2.0)[:,None]
# clearance from inner point to any part
allp = trimesh.util.concatenate(list(parts.values()))
pq = trimesh.proximity.ProximityQuery(allp)
_, clr, tri = pq.on_surface(inner)
owner = np.repeat(np.arange(len(parts)), [len(m.faces) for m in parts.values()])
names = list(parts)
near = [names[owner[t]] for t in tri]
np.savez(__import__('pathlib').Path(__file__).with_name('cap_samples.npz'), P=P, N=N, th=th, clr=clr)

# zones by outward normal
def zone(n, p):
    if n[2] > 0.6: return 'crown(top)'
    if n[0] < -0.5: return 'back'
    if n[1] > 0.5: return 'left side(+y)'
    if n[1] < -0.5: return 'right side(-y)'
    if n[0] > 0.5: return 'front'
    return 'other'
Z = np.array([zone(n,p) for n,p in zip(N,P)])
for z in sorted(set(Z)):
    m = Z==z
    area_frac = m.mean()
    good = m & (clr > 3.0)
    print(f'{z:16s} n={m.sum():4d} thick med {np.nanmedian(th[m]):.2f} [{np.nanpercentile(th[m],10):.2f},{np.nanpercentile(th[m],90):.2f}] '
          f'clear>3mm {good.sum()/m.sum():.0%}  clear med {np.median(clr[m]):.1f}  x[{P[m,0].min():.0f},{P[m,0].max():.0f}] z[{P[m,2].min():.0f},{P[m,2].max():.0f}]')
    from collections import Counter
    print('   nearest parts:', Counter(np.array(near)[m & (clr<3)]).most_common(4))
