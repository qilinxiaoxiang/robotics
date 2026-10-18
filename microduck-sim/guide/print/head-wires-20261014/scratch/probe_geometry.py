#!/usr/bin/env python3
"""Probe the head/neck geometry that the wire route depends on (read-only). Prints JSON to stdout."""
import sys, json
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/scripts')
import numpy as np, trimesh
import ext_lib as E
from nr_lib import FK, body_of, BODY_ORDER
fk = FK()
anc = {j: {'anchor': [round(float(x), 2) for x in a], 'axis': [round(float(x), 3) for x in b]} for j, (a, b) in fk.anchors().items()}
rng = {j: [round(float(np.degrees(v)), 1) for v in r] for j, r in fk.range.items()}
man = E.ia_lib.manifest()
keys = ['head_bottom', 'jaw_support', 'motor13', 'motor14', 'motor15', 'jaw_frame', 'pi', 'amplifier', 'speaker', 'speaker_retainer',
        'clip_torso', 'clip_bracket', 'clip_head', 'clip_cap', 'neck_pitch', 'motor11', 'motor12', 'idler11', 'idler_cap11', 'head_yaw_link',
        'head_roll_ring_a', 'head_roll_ring_b', 'neck_link_a', 'neck_link_b', 'shell_left', 'shell_right', 'rear_pack', 'camera_board', 'face_panel',
        'head_pi_zero_w_header_base', 'mouth_sliding_ring']
out = {'anchors': anc, 'rangeDeg': rng, 'bounds': {}, 'missing': []}
M = {}
for k in keys:
    if k not in man:
        out['missing'].append(k); continue
    v, f = E.ia_lib.load_solid(k); m = trimesh.Trimesh(v, f, process=False); M[k] = m
    out['bounds'][k] = {'body': body_of(k), 'min': [round(float(x), 1) for x in m.bounds[0]], 'max': [round(float(x), 1) for x in m.bounds[1]]}
cap = trimesh.load(str(E.PARTS['head_cap_v19']), force='mesh'); M['head_cap_v19'] = cap
out['bounds']['head_cap_v19'] = {'min': [round(float(x), 1) for x in cap.bounds[0]], 'max': [round(float(x), 1) for x in cap.bounds[1]]}
# head_bottom floor: histogram of downward-facing face area by z to find the floor plate level
hb = M['head_bottom']
nz = hb.face_normals[:, 2]; area = hb.area_faces; zc = hb.triangles_center[:, 2]
hist = {}
for sel, nm in ((nz < -0.9, 'down'), (nz > 0.9, 'up')):
    z = np.round(zc[sel] * 2) / 2; a = area[sel]
    s = {}
    for zz, aa in zip(z, a): s[float(zz)] = s.get(float(zz), 0) + float(aa)
    hist[nm] = sorted(((round(k, 1), round(v, 0)) for k, v in s.items() if v > 80), key=lambda t: -t[1])[:12]
out['head_bottom_face_hist'] = hist
# jaw support: same for its base plate and walls
js = M['jaw_support']
nz = js.face_normals; area = js.area_faces; c = js.triangles_center
h2 = {}
for ax, nm in ((2, 'z'), (0, 'x'), (1, 'y')):
    sel = np.abs(nz[:, ax]) > 0.95
    v = np.round(c[sel, ax] * 2) / 2; a = area[sel]; s = {}
    for zz, aa in zip(v, a): s[float(zz)] = s.get(float(zz), 0) + float(aa)
    h2[nm] = sorted(((round(k, 1), round(v, 0)) for k, v in s.items() if v > 40), key=lambda t: -t[1])[:12]
out['jaw_support_face_hist'] = h2
# sections of head_bottom at several z, to see the floor opening (polygons with holes)
def section(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return None
    p, _ = s.to_2D(); polys = p.polygons_full
    return [{'exterior_bounds': [round(float(x), 1) for x in np.array(pg.exterior.coords).min(0)] + [round(float(x), 1) for x in np.array(pg.exterior.coords).max(0)],
             'holes': [[[round(float(x), 1) for x in np.array(h.coords).min(0)], [round(float(x), 1) for x in np.array(h.coords).max(0)], round(float(trimesh.path.polygons.Polygon(h).area), 0)] for h in pg.interiors]} for pg in polys]
# to_2D on a z-plane keeps x,y (maybe flipped); use raw 3D section polylines instead for robustness
def section3(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return None
    res = []
    for ent in s.discrete:
        e = np.asarray(ent)
        res.append({'n': len(e), 'min': [round(float(x), 1) for x in e.min(0)[:2]], 'max': [round(float(x), 1) for x in e.max(0)[:2]], 'closed': bool(np.allclose(e[0], e[-1]))})
    return res
out['head_bottom_sections'] = {}
for z in (100, 103, 105, 107, 109, 111):
    out['head_bottom_sections'][z] = section3(hb, z)
out['jaw_support_sections'] = {z: section3(js, z) for z in (112, 114, 116, 118, 120, 124, 128, 132)}
print(json.dumps(out, indent=1))
