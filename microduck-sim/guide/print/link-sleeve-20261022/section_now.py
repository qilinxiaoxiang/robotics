"""Section through the ankle passive-side axis (ankle local frame of make_halves.py: shaft = local z) of the lower-leg link,
the V1.22 sleeve, the XL330, its washer and the V1.25 ankle halves, both legs. Writes section-now-<side>.png.
    /tmp/microduck-cad-venv/bin/python section_now.py
"""
import sys
from pathlib import Path
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
HERE = Path(__file__).resolve().parent; GUIDE = HERE.parents[1]; SIM = GUIDE.parent
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit')); import ia_lib as L  # noqa: E402
sys.path.insert(0, str(GUIDE / 'print' / 'ankle-halves-20261020'))
import make_halves as H  # noqa: E402
AR = H.AR


def local(key, T):
    v, f = L.load_solid(key); return trimesh.Trimesh(trimesh.transform_points(np.asarray(v, float), np.linalg.inv(T)), f, process=True)


def parts(side):
    K = H.SIDES[side]; T = H.frame(K['sign'])
    out = {n: local(K[k], T) for n, k in (('link', 'lower'), ('servo', 'motor'), ('washer', 'washer'))}
    out['sleeve'] = trimesh.load(AR / 'STL' / f'{side}-sleeve-local.stl', process=True)
    for h in ('outer', 'inner'):
        out[h] = trimesh.load(H.HERE / 'STL' / f'{side}-{h}-local.stl', process=True)
    return out


COL = dict(link='#2b2b2b', sleeve='#7a7a7a', servo='#9db4d0', washer='#d0b05a', outer='#f08a24', inner='#f5b46a')


def draw(ax, ms, title, plane_y=0.0):
    for n, m in ms.items():
        R = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, plane_y], [0, 0, 0, 1]], float)   # (x, y, z) -> (x, z, plane_y - y)
        s = m.copy().apply_transform(R).section(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1])
        if s is None: continue
        p, _ = s.to_2D(to_2D=np.eye(4))
        for poly in p.polygons_full:
            x, y = poly.exterior.xy; ax.fill(x, y, color=COL.get(n, '#444'), alpha=.9, lw=.3, ec='k', label=n)
            for h in poly.interiors:
                x, y = h.xy; ax.fill(x, y, color='white', lw=.3, ec='k')
    hs, ls = ax.get_legend_handles_labels(); u = dict(zip(ls, hs)); ax.legend(u.values(), u.keys(), fontsize=7, loc='upper right')
    ax.set_aspect('equal'); ax.set_xlabel('local x (mm)'); ax.set_ylabel('local z = shaft (mm)'); ax.set_title(title, fontsize=9)


if __name__ == '__main__':
    for side in ('left', 'right'):
        ms = parts(side)
        for n, m in ms.items(): print(side, n, m.bounds.round(2).tolist())
        fig, ax = plt.subplots(figsize=(8, 8)); draw(ax, ms, f'{side}: section through the ankle shaft (local y = 0)')
        ax.set_xlim(-25, 25); ax.set_ylim(-20, 25); fig.savefig(HERE / f'section-now-{side}.png', dpi=130, bbox_inches='tight')
