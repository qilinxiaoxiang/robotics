"""Duct concept sketch for the back-to-back head (proposal, no CAD change): a top-down section through the fan and a view of
the left cheek, with the proposed shroud, baffles and slot windows drawn over the real meshes. Writes
renders/duct-concept.png."""
import sys

import matplotlib
import numpy as np
import trimesh
from matplotlib.patches import FancyArrowPatch, Polygon, Rectangle

import build_b2b as B

sys.path.insert(0, str(B.GUIDE / 'content' / 'interference-audit'))
from ia_lib import load_solid  # noqa: E402

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams['font.family'] = 'PingFang SC'
Z_CUT = 125.0
PARTS = B.HERE / 'parts'
# proposal geometry (robot frame, mm)
SHROUD_X = (48.5, 49.7)          # plate behind clip_head (x 52.6) and 1.6 mm in front of jaw_support (x 46.9): 6.8 mm plenum
SHROUD_Y = (-41.0, 4.0)          # from the fan edge to the right cheek wall
FAN_SIDE_WALL_Y = 4.0            # wall from the plate to x 54.0, keeps the plenum off the fan inlet
FAN_SIDE_WALL_X1 = 54.0          # 2.5 mm short of the fins: the board unit is lowered 2 mm behind its place
BAFFLE_L = ((55.5, 35.0), (55.5, 41.0))   # left end: past the fan lead loop to the cheek wall
EXHAUST = dict(x=(57.5, 67.5), z=(117.0, 135.0))
INTAKE = dict(x=(36.0, 47.0), z=(115.0, 131.0))
SLOT_W, RIB = 1.6, 1.2


def solid(k):
    v, f = load_solid(k)
    return trimesh.Trimesh(v, f, process=False)


def section(ax, m, z, **kw):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return
    for line in s.discrete:
        ax.plot(line[:, 0], line[:, 1], **kw)


def fill_section(ax, m, z, color, alpha=1.0, label=None):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return
    first = True
    for line in s.discrete:
        ax.add_patch(Polygon(line[:, :2], closed=True, fc=color, ec='k', lw=0.4, alpha=alpha,
                             label=label if first else None))
        first = False


def slots(x0, x1):
    xs, x = [], x0
    while x + SLOT_W <= x1 + 1e-6:
        xs.append(x); x += SLOT_W + RIB
    return xs


def main():
    cap = trimesh.load(B.HERE / 'head_cap_b2b-world.stl')
    hs = trimesh.load(PARTS / 'heatsink_6530b.stl'); pcb = trimesh.load(PARTS / 'a7z_pcb.stl')
    fan = trimesh.load(PARTS / 'fan_inlet_zone.stl')
    fixed = {k: solid(k) for k in ('jaw_support', 'motor15', 'clip_head', 'face_panel', 'camera_board', 'eye_trim')}
    fixed['camera_board'] = B.guide_parts()['camera_board']
    gd = {p['key']: p for p in __import__('json').loads((B.GUIDE / 'data/guide-data.json').read_text())['parts']}

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(17, 8.6), gridspec_kw=dict(width_ratios=[1.05, 1]))
    # (1) top-down section at z 125
    section(a1, cap, Z_CUT, color='#555', lw=1.4)
    for k, c in (('jaw_support', '#cfcfcf'), ('motor15', '#bdbdbd'), ('clip_head', '#d7ccc8'), ('camera_board', '#2ca02c'),
                 ('face_panel', '#eeeeee'), ('eye_trim', '#eeeeee')):
        fill_section(a1, fixed[k], Z_CUT, c)
    fill_section(a1, hs, Z_CUT, '#3a3a3a', label='6530B 散热片')
    fill_section(a1, pcb, Z_CUT, '#2e7d32', label='A7Z 板')
    fill_section(a1, fan, Z_CUT, '#90caf9', 0.7, label='风扇进风区')
    a1.text(50.6, -27, 'clip_head', fontsize=7.5, color='#5d4037')
    a1.add_patch(Rectangle((SHROUD_X[0], SHROUD_Y[0]), SHROUD_X[1] - SHROUD_X[0], SHROUD_Y[1] - SHROUD_Y[0],
                           fc='#e74c3c', ec='#e74c3c', label='新增：导风罩板（头盖的一部分）'))
    a1.add_patch(Rectangle((SHROUD_X[0], FAN_SIDE_WALL_Y - 1.2), FAN_SIDE_WALL_X1 - SHROUD_X[0], 1.2, fc='#e74c3c', ec='#e74c3c'))
    a1.add_patch(Rectangle((BAFFLE_L[0][0] - 0.6, BAFFLE_L[0][1]), 1.2, BAFFLE_L[1][1] - BAFFLE_L[0][1], fc='#e74c3c',
                           ec='#e74c3c'))
    for sgn in (1, -1):
        for x in slots(*EXHAUST['x']):
            a1.add_patch(Rectangle((x, sgn * 41.0 - 1.5), SLOT_W, 3.0, fc='#ff9800', ec='none'))
        for x in slots(*INTAKE['x']):
            a1.add_patch(Rectangle((x, sgn * 40.5 - 1.5), SLOT_W, 3.0, fc='#03a9f4', ec='none'))
    arrows = [((30, 15), (50, 15), '#03a9f4'), ((41, 46), (41, 33), '#03a9f4'), ((41, -46), (41, -33), '#03a9f4'),
              ((50, 15), (55.5, 15), '#03a9f4'),
              ((52.5, -2), (52.5, -33), '#e53935'), ((62, -34), (62, -48), '#e53935'), ((62, 34), (62, 48), '#e53935')]
    for p0, p1, c in arrows:
        a1.add_patch(FancyArrowPatch(p0, p1, arrowstyle='-|>', mutation_scale=18, lw=2.2, color=c))
    a1.text(24, 17.5, '冷空气（脖子 + 两侧进风窗）', color='#0277bd', fontsize=10)
    a1.text(51.5, -12, '热风沿导风罩\n流向右侧', color='#c62828', fontsize=9, ha='right')
    a1.text(58, -51, '右侧出风窗', color='#e65100', fontsize=10)
    a1.text(58, 49.5, '左侧出风窗', color='#e65100', fontsize=10)
    a1.text(33, -51, '右侧进风窗', color='#0277bd', fontsize=10)
    a1.text(33, 49.5, '左侧进风窗', color='#0277bd', fontsize=10)
    a1.set_xlim(14, 96); a1.set_ylim(-55, 55); a1.set_aspect('equal'); a1.grid(alpha=0.25)
    a1.set_xlabel('x（向前）mm'); a1.set_ylabel('y（向左）mm')
    a1.set_title(f'俯视剖面 z = {Z_CUT:.0f}（穿过风扇）', fontsize=12)
    a1.legend(loc='upper left', fontsize=8.5, framealpha=0.9)

    # (2) left cheek seen from +y: cap silhouette, pads, ears, windows
    v = cap.vertices[cap.vertices[:, 1] > 0]
    from scipy.spatial import ConvexHull
    h = ConvexHull(v[:, [0, 2]])
    a2.add_patch(Polygon(v[h.vertices][:, [0, 2]], closed=True, fc='#f4f2ec', ec='#777', lw=1.2))
    for k, c, nm in (('touch_pad_l1', '#c58b3a', 'L1'), ('touch_pad_l2', '#c58b3a', 'L2'), ('touch_pad_m', '#c58b3a', 'M'),
                     ('touch_xiao', '#7e57c2', 'XIAO（不动）'), ('antenna', '#999', '天线')):
        (x0, _, z0), (x1, _, z1) = gd[k]['bounds']
        a2.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc=c, ec='k', lw=0.5, alpha=0.75))
        a2.text((x0 + x1) / 2, (z0 + z1) / 2, nm, ha='center', va='center', fontsize=9, color='w' if c != '#999' else 'k')
    (x0, _, z0), (x1, _, z1) = hs.bounds
    a2.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc='none', ec='#3a3a3a', lw=1.2, ls='--'))
    a2.text(x0 + 0.5, z1 + 0.8, '散热片（墙内）', fontsize=8.5, color='#3a3a3a')
    for x in slots(*EXHAUST['x']):
        a2.add_patch(Rectangle((x, EXHAUST['z'][0]), SLOT_W, EXHAUST['z'][1] - EXHAUST['z'][0], fc='#ff9800', ec='none'))
    for x in slots(*INTAKE['x']):
        a2.add_patch(Rectangle((x, INTAKE['z'][0]), SLOT_W, INTAKE['z'][1] - INTAKE['z'][0], fc='#03a9f4', ec='none'))
    a2.text(np.mean(EXHAUST['x']), EXHAUST['z'][0] - 2.5, '出风窗', ha='center', fontsize=10, color='#e65100')
    a2.text(np.mean(INTAKE['x']), INTAKE['z'][0] - 2.5, '进风窗', ha='center', fontsize=10, color='#0277bd')
    a2.set_xlim(-34, 96); a2.set_ylim(104, 162); a2.set_aspect('equal'); a2.grid(alpha=0.25)
    a2.set_xlabel('x（向前）mm'); a2.set_ylabel('z（向上）mm')
    ne, ni = len(slots(*EXHAUST['x'])), len(slots(*INTAKE['x']))
    ae = ne * SLOT_W * (EXHAUST['z'][1] - EXHAUST['z'][0]); ai = ni * SLOT_W * (INTAKE['z'][1] - INTAKE['z'][0])
    a2.set_title(f'左脸颊外观（右侧对称）：出风 {ne} 条槽 {ae:.0f} mm²，进风 {ni} 条槽 {ai:.0f} mm²', fontsize=12)
    fig.suptitle('风道方案（示意，未改 CAD）：后面冷、前面热，风扇抽冷风吹过散热片，热风从两颊排出', fontsize=14)
    fig.tight_layout()
    out = B.HERE / 'renders' / 'duct-concept.png'
    fig.savefig(out, dpi=130)
    print(out, 'exhaust per side', round(ae), 'intake per side', round(ai))


if __name__ == '__main__':
    main()
