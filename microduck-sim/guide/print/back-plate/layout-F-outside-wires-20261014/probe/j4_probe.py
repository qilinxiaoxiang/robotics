import sys, numpy as np, trimesh, json
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit'); import ia_lib
m = trimesh.Trimesh(*ia_lib.load_solid('openrb_board'), process=False)
v = m.vertices; s = v[(v[:, 2] > 24.0) & (np.abs(v[:, 1]) < 6)]
print('openrb verts z>24 |y|<6: bounds', np.round(s.min(0), 2), np.round(s.max(0), 2), len(s))
for zc in (25, 26, 27, 28, 29, 30, 31, 32):
    sec = m.section(plane_origin=[0, 0, zc], plane_normal=[0, 0, 1])
    if sec is None: print(zc, 'none'); continue
    pts = np.vstack([e for e in sec.discrete]); pts = pts[np.abs(pts[:, 1]) < 8]
    print(zc, 'x', np.round(pts[:, 0].min(), 2), np.round(pts[:, 0].max(), 2), 'y', np.round(pts[:, 1].min(), 2), np.round(pts[:, 1].max(), 2)) if len(pts) else print(zc, '-')
for k in ('shell_left', 'shell_right', 'rear_pack'):
    mm = trimesh.Trimesh(*ia_lib.load_solid(k), process=False)
    for x in (-20.0, -24.0, -28.0, -31.0, -34.0, -36.0):
        for y in (0.0, 2.5, 4.0):
            r = mm.ray.intersects_location([[x, y, 20.0]], [[0, 0, 1.0]])[0]
            zs = sorted(r[:, 2].round(2).tolist()) if len(r) else []
            if zs: print(k, x, y, 'hits up from z20:', zs[:4])
g = json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/data/guide-data.json'))
c = {q['id']: q for q in g['cables']}
print('pw-7v', np.round(np.array(c['pw-7v']['path'])[-8:], 2).tolist(), c['pw-7v'].get('radius'))
print('pi-lead tail from notch', [p for p in c['pi-lead']['path'] if p[0] > -27][:6])
