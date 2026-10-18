"""Cap feature facts: reconstruct the V1.6 cap around the Pi rails and front controller bosses from its documented sources."""
import json, sys
import numpy as np
sys.path.insert(0, __import__('os').path.dirname(__file__))
from vc import *

out = {}
cap = load_stl(CAP_V16); C = to_mf(cap)
base = to_mf(load_stl(BASE_SHELL))
rails = [to_mf(load_stl(p)) for p in RAILS]
bosses = [to_mf(load_stl(p)) for p in BOSSES]
out['files'] = {str(p): sha(p) for p in [CAP_V16, BASE_SHELL] + RAILS + BOSSES}
out['capVolume'] = C.volume(); out['capGenus'] = C.genus(); out['capBounds'] = bbox(C).round(3).tolist()
for i, R in enumerate(rails):
    out[f'rail{i}'] = dict(bounds=bbox(R).round(3).tolist(), volume=round(R.volume(), 3))
for i, B in enumerate(bosses):
    out[f'boss{i}'] = dict(bounds=bbox(B).round(3).tolist(), volume=round(B.volume(), 3))

# Reconstruction check in boxes around each rail and each front boss: cap vs (base U feature), XOR volume
def recon(feature_list, box_lo, box_hi):
    Bx = box(box_lo, box_hi)
    ref = union([base] + feature_list) ^ Bx
    cc = C ^ Bx
    return dict(capInBox=round(cc.volume(), 3), refInBox=round(ref.volume(), 3), capMinusRef=round((cc - ref).volume(), 4),
                refMinusCap=round((ref - cc).volume(), 4))

for i, R in enumerate(rails):
    b = bbox(R); lo = b[0] - [1, 1, 1]; hi = b[1] + [1, 1, 0]
    out[f'rail{i}Recon'] = recon([R], lo, hi)
for i in (0, 2):
    b = bbox(bosses[i]); lo = b[0] - [1, 1, 1]; hi = b[1] + [1, 1, 0]
    out[f'boss{i}Recon'] = recon([bosses[i]], lo, hi)

# Roof: inner and outer surface z above the rail tops, at current and shifted x
def roof_z(x, y):
    o = np.array([[x, y, 200.0]]); d = np.array([[0, 0, -1.0]])
    loc, idx, _ = cap.ray.intersects_location(o, d, multiple_hits=True)
    return sorted(np.round(loc[:, 2], 3).tolist(), reverse=True)
prof = {}
for y in (-29.0, 29.0, -10.25, 10.25):
    prof[str(y)] = {str(x): roof_z(x, y) for x in np.arange(48.0, 70.1, 1.0)}
out['roofHitsZ_byY_byX'] = prof
base_tm = load_stl(BASE_SHELL)
def base_roof(x, y):
    loc, idx, _ = base_tm.ray.intersects_location(np.array([[x, y, 200.0]]), np.array([[0, 0, -1.0]]), multiple_hits=True)
    return sorted(np.round(loc[:, 2], 3).tolist(), reverse=True)
out['baseRoofHitsZ_y29'] = {str(x): base_roof(x, 29.0) for x in np.arange(48.0, 70.1, 1.0)}

# Rail mesh cross-section: x-extent of rail material by z level, and its top
for i, p in enumerate(RAILS):
    m = load_stl(p)
    zs = {}
    for z in np.arange(112.0, 150.0, 2.0):
        sec = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            continue
        P = np.vstack([d for d in sec.discrete])
        zs[str(z)] = dict(x=r3([P[:, 0].min(), P[:, 0].max()]), y=r3([P[:, 1].min(), P[:, 1].max()]))
    out[f'rail{i}SectionsZ'] = zs
json.dump(out, open(HERE / 'inspect2.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('roofHitsZ_byY_byX', 'baseRoofHitsZ_y29', 'files')}, indent=1))
