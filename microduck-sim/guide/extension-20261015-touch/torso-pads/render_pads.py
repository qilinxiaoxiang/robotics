"""Inner-face view of each torso shell with the proposed pad, its lead and the nearest parts (reads results.json)."""
import json, sys
from pathlib import Path
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'content' / 'interference-audit'))
from ia_lib import load_solid, load_guide   # noqa: E402

res = json.loads((HERE / 'results.json').read_text())
G = {c['id']: c for c in load_guide()['cables']}
screws = load_guide()['screws']
PARTS = {'shell_left': ['motor10', 'rear_pack', 'rear_frame', 'xl4015_top', 'xl4015_mid', 'openrb_board', 'imu_board', 'motor12'],
         'shell_right': ['motor5', 'rear_pack', 'rear_frame', 'xl4015_top', 'xl4015_mid', 'openrb_board', 'imu_board', 'idler12', 'clip_torso']}
COL = {'motor10': '#555b62', 'motor5': '#555b62', 'rear_pack': '#e08a2c', 'rear_frame': '#c9a46b', 'xl4015_top': '#2e7d32',
       'xl4015_mid': '#66a86a', 'openrb_board': '#2d6fb5', 'imu_board': '#277d4a', 'motor12': '#8d4fbf', 'idler12': '#8d4fbf',
       'clip_torso': '#e99436'}
for side, info in res['shells'].items():
    sgn = 1 if side == 'shell_left' else -1
    sh = trimesh.Trimesh(*load_solid(side), process=False)
    fig, ax = plt.subplots(figsize=(13, 7.2))
    # shell silhouette and wall seen from inside: points of the shell's side wall
    p, _ = trimesh.sample.sample_surface_even(sh, 40000, seed=0)
    w = sgn * p[:, 1] > 15
    ax.scatter(p[w, 0], p[w, 2], s=0.4, color='#d9d6cc', zorder=0)
    yin = np.mean(info['pad']['inner_face_y'])
    for k in PARTS[side]:
        v, f = load_solid(k)
        m = trimesh.Trimesh(v, f, process=False)
        q, _ = trimesh.sample.sample_surface_even(m, 15000, seed=1)
        q = q[sgn * q[:, 1] > 0]                                # the half of the robot on this side
        if not len(q):
            continue
        ax.scatter(q[:, 0], q[:, 2], s=0.3, color=COL.get(k, '#888'), alpha=0.35, zorder=1)
        d = next((n['mm'] for n in info['nearest'] if n['part'] == k), None)
        lx, lz = np.median(q[:, 0]), np.max(q[:, 2]) + 1.5
        ax.text(lx, min(lz, 45), k + (f'\n{d} mm from pad' if d is not None else ''), fontsize=7.5, color=COL.get(k, '#444'), ha='center', zorder=5)
    for cid in ['dxl-n12', 'dxl-l10', 'dxl-r5', 'pi-lead', 'imu', 'uart']:
        pts = np.array(G[cid]['path'], float)
        pts = pts[(pts[:, 2] > -3) & (pts[:, 2] < 48) & (pts[:, 0] > -50) & (pts[:, 0] < 38)]
        if len(pts) > 1:
            ax.plot(pts[:, 0], pts[:, 2], '-', lw=1, color='#7b5ea7' if cid.startswith('dxl') else '#b0b0b0', zorder=2)
    for s in screws:
        c = np.array(s['center']); a = np.array(s['axis'])
        if sgn * c[1] > 8 and -50 < c[0] < 36 and -2 < c[2] < 45:
            e = c + a * s['lengthMm']
            ax.plot([c[0], e[0]], [c[2], e[2]], '-', color='#333', lw=2, zorder=3)
            d = next((n['mm'] for n in info['nearest'] if n['part'].startswith('screw:' + s['id'] + ' ')), None)
            if d is not None and d < 6:
                ax.text(e[0], e[2] - 2.5, f'{s["spec"]} screw {d} mm', fontsize=7, color='#111', ha='center', zorder=6)
    x0, x1 = info['pad']['x']; z0, z1 = info['pad']['z']
    for i in range(4):                                         # four 5 mm strips, about 0.7 mm overlap, run front to back
        zs = z0 + i * (18 - 5) / 3
        ax.add_patch(Rectangle((x0, zs), x1 - x0, 5, fc='#d98c1f', ec='#8a5200', alpha=0.55, lw=0.8, zorder=4))
    ax.text((x0 + x1) / 2, (z0 + z1) / 2, f'pad 18 x 18\nwall {info["wall_thickness"]["median"]} mm\n'
            f'air behind {info["free_space_behind_wall"]["min"]:.0f}-{info["free_space_behind_wall"]["median"]:.0f} mm',
            ha='center', va='center', fontsize=8.5, weight='bold', zorder=6)
    r = res['routes'][side]
    tpth = np.array(r['torso_path'])
    ax.plot(tpth[:, 0], tpth[:, 2], '-', color='#c87533', lw=2.2, zorder=6)
    ax.plot(*np.array(r['join_point'])[[0, 2]], 'o', color='#c87533', ms=7, zorder=7)
    ax.annotate(f'joins the neck bundle here, then {r["bundle_mm_cap_plug_to_join"]:.0f} mm to the cap plug\n'
                f'and {r["head_mm_xiao_to_cap_plug"]:.0f} mm to XIAO {r["xiao_pin"]}; total {r["total_mm"]:.0f} mm',
                xy=np.array(r['join_point'])[[0, 2]], xytext=(-6, 47), fontsize=8, color='#8a4a1c',
                arrowprops=dict(arrowstyle='->', color='#8a4a1c'), zorder=7)
    near = [n for n in info['nearest'] if n['class'] != 'cable'][:5]
    ax.text(-49, -6.5, 'Nearest to the pad: ' + '; '.join(f'{n["part"].replace("screw:", "screw ")} {n["mm"]} mm' for n in near),
            fontsize=7.5, color='#333')
    ax.text(-49, -9.5, f'Moving parts: ID12 neck group swept {res["neck_pitch_collision_free_deg"]} deg, {info["by_class_min"]["moving"]} mm; '
            f'limits: moving >= 4 mm, metal and boards >= 3 mm. Mid-flank (x -21..-3): {info["mid_flank_window_x_-21_-3_z_12_30"][0]["part"]} '
            f'{info["mid_flank_window_x_-21_-3_z_12_30"][0]["mm"]} mm (too close).', fontsize=7.5, color='#333')
    ax.set_xlim(-50, 38); ax.set_ylim(-11, 52); ax.set_aspect('equal'); ax.grid(alpha=0.25)
    ax.set_xlabel('x (mm, forward)'); ax.set_ylabel('z (mm, up)')
    name = 'Left' if sgn > 0 else 'Right'
    ax.set_title(f'{name} torso shell, inner face seen from the robot centre line (parts on this half projected onto x-z; distances are 3D, pad to part)')
    plt.tight_layout(); plt.savefig(HERE / f'pad_{side}.png', dpi=130)
    print('wrote', HERE / f'pad_{side}.png')
