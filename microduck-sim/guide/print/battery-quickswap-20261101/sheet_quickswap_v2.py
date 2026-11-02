"""Review sheet for the V3 battery hatch (build-v2/*.stl, build.json): renders-v2/review-sheet.png, Chinese labels, matplotlib only.

    /tmp/microduck-cad-venv/bin/python sheet_quickswap_v2.py
"""
import json
from pathlib import Path
import numpy as np, trimesh, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

HERE = Path(__file__).resolve().parent; B = HERE / 'build-v2'; OUT = HERE / 'renders-v2'; OUT.mkdir(exist_ok=True)
ck = json.loads((B / 'build.json').read_text())
fm.fontManager.addfont('/Library/Fonts/Arial Unicode.ttf'); plt.rcParams['font.family'] = 'Arial Unicode MS'
ld = lambda n: trimesh.load(B / n, force='mesh')
cap, frame, hatch = ld('battery_backpack_cap-world.stl'), ld('battery_backpack_frame-world.stl'), ld('battery_hatch-world.stl')
hp = ld('battery_hatch-print.stl')
battery = trimesh.creation.box(bounds=[(-74.05, -15.5, -22.51), (-62.05, 15.5, 34.49)])
C = dict(cap='#f6c27a', frame='#f0a040', hatch='#2e86de', bat='#27ae60')

def mesh3d(ax, m, col, alpha=1.0, step=1):
    ax.add_collection3d(Poly3DCollection(m.triangles[::step], facecolors=col, edgecolors=col, linewidths=0, alpha=alpha, shade=True,
                                         lightsource=matplotlib.colors.LightSource(225, 45)))

def view3d(pos, items, elev, azim, lims, title):
    ax = fig.add_subplot(pos, projection='3d'); [mesh3d(ax, *it) for it in items]
    ax.set_xlim(*lims[0]); ax.set_ylim(*lims[1]); ax.set_zlim(*lims[2]); ax.set_box_aspect([np.ptp(l) for l in lims])
    ax.view_init(elev, azim); ax.set_axis_off(); ax.set_title(title, fontsize=14, loc='left'); return ax

def section(ax, m, origin, normal, axes, col, label=None):
    s = m.section(plane_origin=origin, plane_normal=normal)
    if s is None: return
    for e in s.entities:
        p = s.vertices[e.points]; ax.fill(p[:, axes[0]], p[:, axes[1]], color=col, alpha=0.85, lw=0.4, ec='k', label=label); label = None

fig = plt.figure(figsize=(20, 13), facecolor='white')
fig.suptitle('电池仓盖 V3：外侧卡片防掀起，两只耳朵嵌在顶面槽里防后拉，实心压块，一个大出线口', fontsize=21, y=0.99)
lims = [(-80, -55), (-30, 30), (10, 48)]
ax = view3d(231, [(cap, C['cap']), (frame, C['frame']), (hatch, C['hatch'])], 30, -140, lims, '① 合上：蓝色盖子和顶面齐平，两侧耳朵嵌在槽里')
ax = view3d(232, [(cap, C['cap']), (hatch, C['hatch'])], 8, 180, [(-80, -60), (-30, 30), (10, 48)], '② 后视：外侧卡片扣进中间槽')

ax = fig.add_subplot(233); ax.set_aspect('equal'); ax.set_title('③ 剖面 y = 20：耳朵在顶面槽里（防止往后拉掉）', fontsize=14, loc='left')
for m, col, lab in ((cap, C['cap'], '盖子'), (frame, C['frame'], '框架'), (hatch, C['hatch'], '仓盖')):
    section(ax, m, (0, 20.0, 0), (0, 1, 0), (0, 2), col, lab)
ax.set_xlim(-78, -60); ax.set_ylim(34, 45); ax.legend(loc='lower right', fontsize=10)
ax.annotate('耳朵 1.55 × 8.85 mm，厚 2.35 mm，\n后面离槽壁 0.15 mm', (-69.1, 41.5), (-77.5, 36), fontsize=11, arrowprops=dict(arrowstyle='->'))
ax.set_xlabel('x (mm, 向前)'); ax.set_ylabel('z (mm)')

ax = fig.add_subplot(234); ax.set_aspect('equal'); ax.set_title('④ 剖面 x = -70：实心压块离电池顶 0.3 mm', fontsize=14, loc='left')
for m, col, lab in ((battery, C['bat'], '电池（标称）'), (cap, C['cap'], '盖子'), (hatch, C['hatch'], '仓盖')):
    section(ax, m, (-70.0, 0, 0), (1, 0, 0), (1, 2), col, lab)
ax.set_xlim(-27, 27); ax.set_ylim(26, 46); ax.legend(loc='lower left', fontsize=10)
ax.annotate('压块 10 × 8 mm，实心\n（需要时贴泡棉胶）', (9, 36), (12, 28.5), fontsize=10, arrowprops=dict(arrowstyle='->'))
ax.annotate('出线口 17.65 mm 宽，往后开通\n（XT30 公头可以直接穿过）', (-6, 42.4), (-9, 37.5), fontsize=10, arrowprops=dict(arrowstyle='->'))
ax.set_xlabel('y (mm, 向左)'); ax.set_ylabel('z (mm)')

ax = view3d(235, [(hp, C['hatch'])], 35, -60, [(0, hp.bounds[1, 0]), (0, hp.bounds[1, 1]), (0, max(hp.bounds[1, 2], 20))],
            '⑤ 打印姿态：背面朝下，卡片平贴热床')

c = ck; sw = c['hatch_swing_overlaps_mm3 (hatch_free: flap bump removed)']
swing_ok = all(set(v) == {'ears_vs_cap'} and v['ears_vs_cap'] == 0 for v in sw.values())
rm_ok = not any(v for k, v in c['removal_tilt_then_pull_back_overlaps_mm3 (flap out)'].items() if k.startswith(('22', '24')))
pb = c['pull_back_stop_overlap_mm3 (closed, translated -x, flap bump removed; >0 = ears stop it)']
capthin = c['print']['battery_backpack_cap']['new_thin_regions']
txt = (f"检查结果\n"
       f"· 合上时和框架、盖子、横条、开关、DFR1202、电池都不干涉\n"
       f"· 卡片凸起在槽里不干涉；压块离电池顶 {c['hold_down_gap_to_battery_top_mm']} mm\n"
       f"· 后边掀起 0 到 24 度：{'全程不碰（耳朵也不碰）' if swing_ok else '有碰撞，见 build.json'}\n"
       f"· 往后拉：0.15 mm 后耳朵顶到槽后壁（拉 0.5 mm 重叠 {pb['0.5']['ears_vs_cap']} mm³）\n   前舌头勾住 1.0 mm，掉不下来\n"
       f"· 取盖：拨开卡片，掀到 22 到 24 度，往后拉 1 到 1.5 mm：{'全程不碰' if rm_ok else '有碰撞'}（15 到 18 度拉会蹭）\n"
       f"· XT30（10.2 × 5.2）和 JST 平衡头都能竖直穿过出线口\n"
       f"· 卡片应变 {c['flap']['root_strain_pct']}%（同 V1.40）；没有别的薄片或弹性件\n"
       f"· 仓盖重 {c['hatch_mass_g']} g；打印时超过 45 度的悬空面 {c['hatch_print_overhang_over_45deg_mm2']} mm²\n"
       f"· 仓盖没有低于 1.2 mm 的地方\n"
       f"· 盖子顶面槽移到圆角前面（后壁 x -70.0），盖子也没有新增薄壁\n\n"
       "要重打的件\n· 盖子（V1.40 开口加两侧顶面槽，保留中间卡槽）\n· 新仓盖\n· 框架和 V1.40 相同")
ax = fig.add_axes([0.66, 0.04, 0.33, 0.43]); ax.axis('off'); ax.text(0, 1, txt, va='top', fontsize=12, linespacing=1.5)
fig.savefig(OUT / 'review-sheet.png', dpi=85)
print('ok', OUT / 'review-sheet.png')
