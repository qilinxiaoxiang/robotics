"""+y Pi rail neck and the jaw_support behind it.
1. Cap sections every 0.5 mm in z inside the +y rail band (y 25.7..32.3) for V1.6, V1.7 and the candidate: area and
   x extent, to find the thinnest section between the lower screw boss and the roof.
2. jaw_support depth map behind the rail: for y in 24..34 and z in 112..140 (0.5 mm grid), the largest x of jaw_support
   (ray from +x), and the rail's back face (smallest x) in each cap.
Usage: rail_neck.py <candidate-world.stl>.  Writes ../rail-neck.json.
"""
import json, sys, os, gc
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *
import shapely.geometry as sg

CAND = Path(sys.argv[1])
S, prov = solids(['jaw_support', 'motor15'])
out = {'method': __doc__.strip()}
ZS = np.arange(114.0, 150.01, 0.5)
YS = np.arange(24.0, 34.01, 0.5); ZG = np.arange(112.0, 140.01, 0.5)


def first_x(tm, y, z, from_plus=True):
    o = np.column_stack([np.full(len(y), 120.0 if from_plus else 0.0), y, z])
    d = np.tile([-1.0 if from_plus else 1.0, 0, 0], (len(y), 1))
    loc, ind, _ = tm.ray.intersects_location(o, d, multiple_hits=True)
    res = np.full(len(y), np.nan)
    for q, i in zip(loc, ind):
        if from_plus:
            res[i] = q[0] if np.isnan(res[i]) else max(res[i], q[0])
        else:
            res[i] = q[0] if np.isnan(res[i]) else min(res[i], q[0])
    return res


Y, Z = np.meshgrid(YS, ZG, indexing='ij')
for k in ['jaw_support', 'motor15']:
    tm = mf_to_tm(S[k])
    xm = first_x(tm, Y.ravel(), Z.ravel(), True).reshape(Y.shape)
    out[f'{k}MaxX'] = {'y': YS.tolist(), 'z': ZG.tolist(), 'x': np.where(np.isnan(xm), None, np.round(xm, 3)).tolist()}
del S; gc.collect()

for lab, path, h0 in [('V1.6', CAP_V16, CAP_V16_SHA), ('V1.7', CAP_V17, CAP_V17_SHA), ('candidate', CAND, None)]:
    tm = trimesh.load(path, force='mesh')
    if h0:
        assert sha(path) == h0
    secs = {}
    for z in ZS:
        sec = tm.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            continue
        pl, _ = sec.to_2D(to_2D=trimesh.transformations.translation_matrix([0, 0, -z]))
        win = sg.box(45.0, 25.7, 70.0, 32.3); area, xs = 0.0, []
        for poly in pl.polygons_full:
            g = poly.intersection(win)
            if not g.is_empty and g.area > 0:
                area += g.area; xs.append((g.bounds[0], g.bounds[2]))
        if area > 0:
            secs[f'{z:.1f}'] = [round(area, 2), round(min(a for a, b in xs), 2), round(max(b for a, b in xs), 2)]
    # rail back face (smallest x of cap material in x 45..70) per (y, z): ray from x = 45 towards +x
    o = np.column_stack([np.full(Y.size, 45.0), Y.ravel(), Z.ravel()])
    loc, ind, _ = tm.ray.intersects_location(o, np.tile([1.0, 0, 0], (Y.size, 1)), multiple_hits=True)
    back = np.full(Y.size, np.nan)
    for q, i in zip(loc, ind):
        if q[0] < 70.0:
            back[i] = q[0] if np.isnan(back[i]) else min(back[i], q[0])
    out[lab] = {'sectionsAreaXminXmax': secs, 'railBackX': np.where(np.isnan(back), None, np.round(back, 3)).reshape(Y.shape).tolist()}
    print(lab, json.dumps(secs), flush=True)
    del tm; gc.collect()
json.dump(out, open(OUT / 'rail-neck.json', 'w'), indent=0)
