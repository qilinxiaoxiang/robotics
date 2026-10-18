"""Room around the candidate's +y rail neck (z 122..131) for a stiffening web: section outlines of the cap in the band
y 20..36, x 50..62, the moved Pi parts and the fixed parts that come within reach of a slab x 54.5..rail front face.
Usage: probe_web.py <candidate-world.stl>.  Writes ../probe-web.json.
"""
import json, sys, os, gc
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *
import shapely.geometry as sg

CAND = Path(sys.argv[1]); SHIFT = np.array([-3.3, 0, 2.0])
tm = trimesh.load(CAND, force='mesh')
out = {'sections': {}}
for z in np.arange(121.0, 132.01, 1.0):
    sec = tm.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    pl, _ = sec.to_2D(to_2D=trimesh.transformations.translation_matrix([0, 0, -z]))
    win = sg.box(50.0, 20.0, 62.0, 36.5); polys = []
    for poly in pl.polygons_full:
        g = poly.intersection(win)
        if not g.is_empty and g.area > 0.01:
            for gg in getattr(g, 'geoms', [g]):
                polys.append({'area': round(gg.area, 2), 'bounds': [round(v, 2) for v in gg.bounds]})
    out['sections'][f'{z:.1f}'] = polys
C2 = to_mf(tm); del tm
S, prov = solids(None)
region = box([50.0, 18.0, 118.0], [62.0, 36.5, 134.0])
near = {}
for k, M in S.items():
    Mm = tr(M, SHIFT) if (k == 'pi' or k.startswith('head_pi')) else M
    I = Mm ^ region
    if not I.is_empty() and I.volume() > 1e-4:
        near[k] = {'moved': bool(k == 'pi' or k.startswith('head_pi')), 'boundsInRegion': bbox(I).round(2).tolist(),
                   'volumeInRegion': round(I.volume(), 2)}
out['partsInRegion'] = near
json.dump(out, open(OUT / 'probe-web.json', 'w'), indent=1)
print(json.dumps(out)[:6000])
