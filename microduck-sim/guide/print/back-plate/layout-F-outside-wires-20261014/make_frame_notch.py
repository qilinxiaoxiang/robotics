"""Frame for the drop-in notch option (Shawn 2026-10-14: wires drop into the pack where the shell top meets the box).
Starts from frame_hidden_noP1-world.stl (hidden-screw cap frame, P1 filled) and cuts two notches, both inside the
crevice between the box front and the shell rear edge:
  A  top-wall front edge: x -49.8 .. front (-47.0), y NY0..NY1, through the 1.2 top wall (z 41.8..43); inner corners r 1.0.
     Lets the four wires bend down from the box top (centreline z 45) into the box front cavity at x -47.8 with the
     0.3 clearance to the wall corner (bend radius 3).
  B  cover-plate top edge: x -47 .. -45, y NY0..NY1, z 28.5 .. 29.5 (1.0 deep, floor flush with the cover lip top z 28.5,
     the lip x -45..-37.5 is untouched); floor corners r 0.5. The wires pass under the shell lip (underside z 31.6..31.9)
     at centreline z 30.0 and ride on the cover lip into the pack.
Writes frame_hidden_noP1_notch-world.stl and frame_notch_check.json. Run under run_bounded_cad.py, CAD venv."""
import sys, json
from pathlib import Path
import numpy as np, trimesh, manifold3d as m3
from shapely.geometry import box as sbox
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'rear-pack')); import pack_lib as P
NY0, NY1 = 3.2, 12.4                     # notch y band: four 22 AWG lanes y 4.4 / 6.5 / 8.6 / 10.7 (pitch 2.1), 0.3 at y 3.2, 1.7 at y 12.4 for the yz-plane bend of the y 10.7 wire
A = dict(x0=-49.8, x1=-45.5, z0=41.3, z1=43.5, r=1.0)     # x1/z extend past the wall so the cut is open to the front and top
B = dict(x0=-47.5, x1=-44.95, z0=28.5, z1=30.5, r=0.5)
def notch_A():
    g = sbox(A['x0'], NY0, A['x1'] + A['r'] + 1, NY1).buffer(-A['r']).buffer(A['r'])   # rounded inner (rear) corners, open front
    return P.extrude_xy(g, A['z0'], A['z1'])
def notch_B():
    g = sbox(NY0, B['z0'], NY1, B['z1'] + B['r'] + 1).buffer(-B['r']).buffer(B['r'])   # rounded floor corners, open top (yz plane)
    return P.extrude_yz(g, B['x0'], B['x1'])
def info(tm):
    man = P.mesh_to_m(tm)
    return dict(volume_mm3=round(float(man.volume()), 1), genus=int(man.genus()), watertight=bool(tm.is_watertight),
                bodies=sum(1 for q in man.decompose() if q.volume() > 1.0), bounds=np.round(tm.bounds, 2).tolist())
base = trimesh.load(str(HERE / 'frame_hidden_noP1-world.stl'), force='mesh')
cut = P.union([notch_A(), notch_B()])
res = P.mesh_to_m(base) - cut
tm = P.from_m(res); tm.merge_vertices(); tm.export(HERE / 'frame_hidden_noP1_notch-world.stl')
tm = trimesh.load(str(HERE / 'frame_hidden_noP1_notch-world.stl'), force='mesh')
out = {'frame_hidden_noP1': info(base), 'frame_hidden_noP1_notch': info(tm)}
out['removed_mm3'] = round(out['frame_hidden_noP1']['volume_mm3'] - out['frame_hidden_noP1_notch']['volume_mm3'], 2)
# what the cuts actually removed (intersection with the base), per notch
for nm, c in (('A_topWall', notch_A()), ('B_coverTop', notch_B())):
    inter = P.mesh_to_m(base) ^ c; b = inter.bounding_box(); bl, bh = (np.array(b[0]), np.array(b[1])) if isinstance(b, tuple) else (np.array(b.min), np.array(b.max))
    out[f'notch_{nm}'] = dict(removed_mm3=round(float(inter.volume()), 2), boundsRemoved=[np.round(bl, 2).tolist(), np.round(bh, 2).tolist()] if inter.volume() > 0 else None)
# untouched checks: cover lip (x -45..-37.5, |y|<=13.2, z 27.3..28.5), tongue slots (|y| 23.8..30.4, z > 41) and the rest of the frame
def crop(m, lo, hi):
    c = m.triangles_center; keep = np.all((c >= np.asarray(lo) - 6) & (c <= np.asarray(hi) + 6), axis=1)
    return m.submesh([np.flatnonzero(keep)], append=True)
def same(lo, hi, n=6):
    # region sampled against the two solids: the removed volume (base minus result) must not reach into it
    g = np.stack(np.meshgrid(*[np.linspace(a, b, n) for a, b in zip(lo, hi)], indexing='ij'), -1).reshape(-1, 3)
    d = P.mesh_to_m(base) - P.mesh_to_m(tm); dm = P.from_m(d)
    if dm.volume < 1e-6: return True
    return not bool(dm.contains(g).any())
out['coverLip_untouched'] = same((-44.9, -13.1, 27.4), (-37.6, 13.1, 28.4))
def top_z(m, xs, ys, zmax=60.0, zmin=-99.0):
    o = np.array([[x, y, zmax] for x in xs for y in ys]); loc, _, _ = m.ray.intersects_location(o, np.tile([0, 0, -1.0], (len(o), 1)), multiple_hits=True)
    z = [float(l[2]) for l in loc if l[2] > zmin]
    return round(max(z), 2) if z else None
def front_x(m, ys, zs, x0=-60.0):
    o = np.array([[x0, y, z] for y in ys for z in zs]); loc, _, _ = m.ray.intersects_location(o, np.tile([1.0, 0, 0], (len(o), 1)), multiple_hits=True)
    x = [float(l[0]) for l in loc if l[0] < -40]
    return round(max(x), 2) if x else None
yb = np.linspace(NY0 + 0.6, NY1 - 0.6, 5)
out['coverLip_topZ_at_band'] = top_z(tm, np.linspace(-44.8, -37.7, 6), yb, zmin=27.0)
out['tongueSlots_untouched'] = all(same((-64.5, s * 23.8, 41.0), (-60.0, s * 30.4, 43.2)) for s in (1, -1))
out['plate_below_notchB_untouched'] = same((-46.9, NY0, 20.0), (-45.1, NY1, 28.4))
out['notchB_floorZ'] = top_z(tm, np.linspace(-46.9, -45.1, 5), yb, zmin=20.0)
out['plateTopZ_outside_band'] = top_z(tm, np.linspace(-46.9, -45.1, 5), [NY0 - 1.0, NY1 + 1.0], zmin=20.0)
out['topWall_frontEdgeX_in_notch'] = front_x(tm, yb, [42.0, 42.6])
out['topWall_frontEdgeX_outside_band'] = front_x(tm, [NY0 - 1.0, NY1 + 1.0], [42.0, 42.6])
out['notches'] = dict(yBand=[NY0, NY1], widthMm=round(NY1 - NY0, 2), A=dict(x=[A['x0'], -47.0], depthMm=round(-47.0 - A['x0'], 2), through='top wall z 41.8..43', cornerR=A['r']),
                      B=dict(x=[-47.0, -45.0], floorZ=B['z0'], depthMm=round(29.5 - B['z0'], 2), cornerR=B['r']))
(HERE / 'frame_notch_check.json').write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps(out, indent=1))
