"""Geometry facts for the cap-settle study.

1. Which CAD header row is nearer the PCB edge (real Pi: the even row, pins 2/4, runs along the board edge).
2. Obstacle profile: per used pin column, the smallest x of each fixed part within the column's y band and the
   z range swept by the connector during cap-on (final z .. final z + 40).
3. x-z sections through the pin columns (PNG) with V1.6 / V1.7 seats and a 14 mm sleeve.
Writes ../inspect-geometry.json and ../png/section-*.png.
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

out = {}
keys = FIXED + ['pi', 'head_pi_zero_w_header_base', 'head_pi_zero_w_gpio_solder_tails'] + \
       [f'head_pi_zero_w_header_pin_{i:02d}' for i in (1, 2)]
S, prov = solids(keys)
out['solidProvenance'] = prov
src = load_npz('source')

# 1. PCB edge vs rows, in local (s, y, t) coordinates
def loc(V):
    return np.column_stack([V @ A, V[:, 1], V @ CT])
pcb = loc(src['pi'][0])
near = pcb[(np.abs(pcb[:, 1]) < 20)]
p1 = loc(src['head_pi_zero_w_header_pin_01'][0]); p2 = loc(src['head_pi_zero_w_header_pin_02'][0])
base = loc(src['head_pi_zero_w_header_base'][0])
edge_t = float(near[:, 2].min())
out['rows'] = {'pcbHeaderEdgeT': round(edge_t, 3), 'pcbFrontS': round(float(np.percentile(near[:, 0], 99)), 3),
               'pcbS': [round(float(near[:, 0].min()), 3), round(float(near[:, 0].max()), 3)],
               'pin01CentreT': round(float(p1[:, 2].mean()), 3), 'pin02CentreT': round(float(p2[:, 2].mean()), 3),
               'pin01FromEdgeMm': round(float(p1[:, 2].mean()) - edge_t, 3), 'pin02FromEdgeMm': round(float(p2[:, 2].mean()) - edge_t, 3),
               'headerBaseS': [round(float(base[:, 0].min()), 3), round(float(base[:, 0].max()), 3)],
               'headerBaseT': [round(float(base[:, 2].min()), 3), round(float(base[:, 2].max()), 3)],
               'pin01S': [round(float(p1[:, 0].min()), 3), round(float(p1[:, 0].max()), 3)],
               'pin01Y': [round(float(p1[:, 1].min()), 3), round(float(p1[:, 1].max()), 3)]}

# 2. obstacle profile per column: min x inside the column band, z within the swept range of a 14 mm sleeve
prof = {}
for pin in USED_PINS:
    y0, y1 = col_y(pin)
    for dx, label in [(0.0, 'V1.6'), (4.6, 'V1.7')]:
        t = row_t(pin)
        sl = local_hull((S_BASE_TOP, S_BASE_TOP + 14.0), (y0, y1), t, d=[-dx, 0, 0])
        b = bbox(sl)
        zlo, zhi = b[0, 2], b[1, 2] + 40
        row = {}
        for k in FIXED:
            O = S[k] ^ box([b[0, 0] - 1, y0, zlo], [b[1, 0] + 25, y1, zhi])
            if not O.is_empty() and O.volume() > 1e-6:
                ob = bbox(O)
                row[k] = {'minX': round(float(ob[0, 0]), 3), 'zRange': [round(float(ob[0, 2]), 2), round(float(ob[1, 2]), 2)]}
        prof.setdefault(str(pin), {})[label] = {'columnY': [y0, y1], 'sleeve14MaxX': round(float(b[1, 0]), 3),
                                               'sweptZ': [round(float(zlo), 2), round(float(zhi), 2)],
                                               'obstacles': dict(sorted(row.items(), key=lambda kv: kv[1]['minX']))}
out['obstacleProfile'] = prof

# 3. sections
os.makedirs(OUT / 'png', exist_ok=True)
caps = {'V1.6': load_cap(CAP_V16, CAP_V16_SHA), 'V1.7': load_cap(CAP_V17, CAP_V17_SHA)}
colors = {'camera_board': '#3d7268', 'camera_retainer': '#222222', 'face_panel': '#b0aa98', 'eye_trim': '#8c6d46',
          'camera_clamp_screw_1': '#c0392b', 'camera_clamp_screw_2': '#c0392b', 'camera_clamp_screw_3': '#c0392b',
          'head_bottom': '#7f8c8d', 'jaw_support': '#5d6d7e', 'jaw_frame': '#95a5a6', 'motor15': '#34495e',
          'lower_pad': '#aab7b8', 'upper_pad': '#aab7b8', 'mouth_sliding_ring': '#7f8c8d'}
def draw(ax, M, y, color, lw=0.8, fill=False):
    m = mf_to_tm(M)
    sec = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return
    for ent in sec.discrete:
        ax.plot(ent[:, 0], ent[:, 2], color=color, lw=lw)
for y, tag in [(19.05, 'pins05-06'), (16.51, 'pins07-08'), (8.89, 'pins13-14'), (-19.05, 'pins35-36'), (24.13, 'pins01-02')]:
    fig, axs = plt.subplots(1, 2, figsize=(14, 6.5))
    for ax, (label, dx) in zip(axs, [('V1.6', 0.0), ('V1.7', 4.6)]):
        for k in FIXED:
            draw(ax, S[k], y, colors.get(k, '#999999'))
        draw(ax, caps[label], y, '#e99436', lw=1.0)
        for k in ['pi', 'head_pi_zero_w_header_base', 'head_pi_zero_w_gpio_solder_tails']:
            draw(ax, tr(S[k], [-dx, 0, 0]), y, '#1e8449', lw=1.0)
        for t in (T_LOW, T_HIGH):
            sl = local_hull((S_BASE_TOP, S_BASE_TOP + 14.0), (y - 1.27, y + 1.27), t, d=[-dx, 0, 0])
            draw(ax, sl, y, '#2e86c1', lw=1.2)
            draw(ax, tr(sl, APPROACH), y, '#85c1e9', lw=0.8)
        ax.set_xlim(45, 90); ax.set_ylim(105, 162); ax.set_aspect('equal'); ax.grid(alpha=0.3)
        ax.set_title(f'{label} seat (Pi shift {dx} mm), section y = {y}: 14 mm sleeves final (blue) and +40 mm (light)')
        ax.set_xlabel('x (forward), mm'); ax.set_ylabel('z (up), mm')
    fig.tight_layout(); fig.savefig(OUT / 'png' / f'section-{tag}.png', dpi=110); plt.close(fig)
json.dump(out, open(OUT / 'inspect-geometry.json', 'w'), indent=1)
print(json.dumps(out['rows'], indent=1))
for pin, v in prof.items():
    for label, r in v.items():
        print(pin, label, r['sleeve14MaxX'], {k: o['minX'] for k, o in list(r['obstacles'].items())[:4]})
