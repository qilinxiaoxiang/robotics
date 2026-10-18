"""Exact geometry around the box-front / shell-lip slot for the drop-in notch (2026-10-14). World mm.
Shell lip underside and rear edge per y, cover top edge, cover lip, XL top-board pin face, top-wall front edge, DFR/IMU tops.
Writes probe/notch_geom.json and probe/notch_sec_y*.png."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent; D = HERE.parent
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit'); import ia_lib
man = ia_lib.manifest()
M = {k: trimesh.Trimesh(*ia_lib.load_solid(k), process=False) for k in man if k not in ('rear_frame', 'rear_lid')}
M['frame'] = trimesh.load(str(D / 'frame_hidden_noP1-world.stl'), force='mesh')
out = {}
def ray_hits(m, origins, d):
    loc, idx, _ = m.ray.intersects_location(origins, np.tile(d, (len(origins), 1)), multiple_hits=True)
    return loc, idx
# shell lip underside (lowest shell surface seen from below) per y at x -47..-44.5, and shell rear-most x at z 29..34
ys = np.arange(-18, 18.01, 1.0)
rows = {}
for y in ys:
    sh = M['shell_left'] if y >= 0 else M['shell_right']
    xs = np.arange(-47.0, -44.0, 0.1)
    o = np.c_[xs, np.full_like(xs, y), np.full_like(xs, 20.0)]
    loc, idx = ray_hits(sh, o, [0, 0, 1.0])
    under = {}
    for p, i in zip(loc, idx):
        under.setdefault(round(float(o[i][0]), 1), []).append(float(p[2]))
    under = {k: min(v) for k, v in under.items()}
    zs = np.arange(29.0, 34.01, 0.1)
    o2 = np.c_[np.full_like(zs, -60.0), np.full_like(zs, y), zs]
    loc2, idx2 = ray_hits(sh, o2, [1.0, 0, 0])
    rear = {}
    for p, i in zip(loc2, idx2):
        z = round(float(o2[i][2]), 1); rear[z] = min(rear.get(z, 99), float(p[0]))
    rows[f'{y:+.0f}'] = dict(lipUndersideZ_minOverX=round(min(under.values()), 2) if under else None,
                            lipUndersideZ_byX={f'{k:.1f}': round(v, 2) for k, v in sorted(under.items())} if under else None,
                            shellRearX_byZ={f'{k:.1f}': round(v, 2) for k, v in sorted(rear.items())})
out['shell'] = rows
# cover top edge z and cover lip per y (frame mesh), x -47..-45 and lip x -45..-37.5
cov = {}
for y in np.arange(0, 19.01, 1.0):
    xs = np.arange(-46.9, -37.0, 0.2); o = np.c_[xs, np.full_like(xs, y), np.full_like(xs, 60.0)]
    loc, idx = ray_hits(M['frame'], o, [0, 0, -1.0]); top = {}
    for p, i in zip(loc, idx):
        x = round(float(o[i][0]), 1)
        if p[2] > 20: top[x] = max(top.get(x, -99), float(p[2]))
    plate = [v for k, v in top.items() if k <= -45.05]; lip = [v for k, v in top.items() if -44.95 <= k <= -37.6]
    cov[f'{y:.0f}'] = dict(plateTopZ=round(max(plate), 2) if plate else None, lipTopZ=round(max(lip), 2) if lip else None)
out['cover'] = cov
# XL top board pin face (max x) in z 29..41, |y| < 20 ; top wall front edge
xl = M['xl4015_top']; v = xl.vertices; sel = (np.abs(v[:, 1]) < 20) & (v[:, 2] > 29)
out['xl_top_maxX_z29up_absY20'] = round(float(v[sel, 0].max()), 2); out['xl_top_maxZ'] = round(float(v[:, 2].max()), 2)
fv = M['frame'].vertices; sel = (fv[:, 2] > 41.0) & (np.abs(fv[:, 1]) < 20)
out['topWall_frontEdgeX'] = round(float(fv[sel, 0].max()), 2); out['topWall_topZ'] = round(float(fv[sel, 2].max()), 2)
sel = (fv[:, 2] > 29.6) & (fv[:, 2] < 41.7) & (np.abs(fv[:, 1]) < 20) & (fv[:, 0] > -60)
out['frame_maxX_between_cover_and_topwall_absY20'] = round(float(fv[sel, 0].max()), 2) if sel.any() else None
# pack interior parts tops at x -45..-30, |y| < 14
tops = {}
for k, m in M.items():
    b = m.bounds
    if b[1][0] < -46 or b[0][0] > -28 or b[0][1] > 14 or b[1][1] < -14 or b[1][2] < 20:
        continue
    vv = m.vertices; s = (vv[:, 0] > -45.5) & (vv[:, 0] < -28) & (np.abs(vv[:, 1]) < 14)
    if s.any(): tops[k] = dict(maxZ=round(float(vv[s, 2].max()), 2), xRange=[round(float(vv[s, 0].min()), 1), round(float(vv[s, 0].max()), 1)])
out['packPartsTops_x-45.5..-28_absY14'] = tops
(HERE / 'notch_geom.json').write_text(json.dumps(out, indent=1))
# sections
COL = {'shell_left': 'tab:blue', 'shell_right': 'tab:cyan', 'rear_pack': 'tab:green', 'frame': 'tab:orange', 'openrb_board': 'purple', 'xl4015_top': 'grey'}
for y in (6.0, 9.0, 12.0, 14.0):
    fig, ax = plt.subplots(figsize=(10, 8))
    for k, m in M.items():
        try: s = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
        except Exception: s = None
        if s is None: continue
        for e in s.discrete: ax.plot(e[:, 0], e[:, 2], color=COL.get(k, 'silver'), lw=0.9)
    ax.set_xlim(-54, -28); ax.set_ylim(22, 48); ax.set_aspect('equal'); ax.grid(True, lw=0.3)
    from matplotlib.ticker import MultipleLocator
    ax.xaxis.set_minor_locator(MultipleLocator(1)); ax.yaxis.set_minor_locator(MultipleLocator(1)); ax.grid(True, which='minor', lw=0.15)
    ax.set_title(f'xz section y = {y}'); fig.savefig(HERE / f'notch_sec_y{y:.0f}.png', dpi=110); plt.close(fig)
print(json.dumps({k: v for k, v in out.items() if k != 'shell'}, indent=1))
for y in ('+6', '+9', '+12', '+14'):
    r = out['shell'][y]; print(y, r['lipUndersideZ_minOverX'], {k: v for k, v in r['shellRearX_byZ'].items() if k in ('29.5', '30.0', '30.5', '31.0', '31.5', '32.0', '32.5', '33.0')})
