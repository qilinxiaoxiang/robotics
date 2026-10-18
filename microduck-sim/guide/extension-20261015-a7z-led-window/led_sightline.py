"""Where the Radxa Cubie A7Z power LED (LED2) sits in the MicroDuck head, and whether a face-panel hole can see it.

Read-only analysis for the next head revision: loads the current robot-frame meshes, writes led_sightline.json and
led-window-front.png next to this file, changes no print file. Runs in a few seconds with the CAD venv:
    /tmp/microduck-cad-venv/bin/python -I led_sightline.py

LED2 board position (s from the pin-1 end, d from the header edge, mm) is measured on Radxa's component placement map
V1.11 (top side) and cross-checked on Radxa's top photo; see NOTE.md.
"""
import json
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
G = HERE.parent / 'print'
ROUTES = HERE.parent / 'content' / 'routes.json'
fr = json.loads((G / 'a7z-head/checks.json').read_text())['frame']
O, ES, ED, N = (np.array(fr[k]) for k in ('origin', 'es', 'ed', 'n'))
T = 1.6
LED_S, LED_D, LED_H = 47.9, 28.1, 0.6          # centre on the board; LED top about 0.6 mm above the PCB (0603/0805 chip, catalogue)
HOLE = np.array([81.4, -20.0, 143.0])           # proposed hole centre on the face front (x 81.4)
HOLE_D = 3.0


def w(s, d, h):
    return O + s * ES + d * ED + h * N


LED = w(LED_S, LED_D, T + LED_H)
MESHES = {
    'head_cap': 'world/head_cap.stl', 'face_panel': 'world/face_panel.stl', 'eye_trim': 'face-a7z/eye_trim_a7z.stl',
    'camera_13m214': 'face-a7z/camera_13m214.stl', 'clip_cap': 'world/clip_cap.stl', 'head_bottom': 'world/head_bottom.stl',
    'amplifier': 'world/amplifier.stl', 'antenna_ac019': 'a7z-head/a7z_parts/antenna_ac019.stl',
    'antenna_coax': 'a7z-head/a7z_parts/antenna_coax.stl', 'usb_c_otg_dp': 'a7z-head/a7z_parts/usb_c_otg_dp.stl',
    'usb_c_power': 'a7z-head/a7z_parts/usb_c_power.stl', 'touch_pad_r1': 'world/touch_pad_r1.stl',
    'touch_pad_m': 'world/touch_pad_m.stl',
}


def main():
    M = {k: trimesh.load(G / v, force='mesh') for k, v in MESHES.items()}
    res = {'led_world_mm': LED.round(2).tolist(), 'led_axis_world': N.round(4).tolist(), 'closest_mm': {}}
    for k, m in M.items():
        c, dist, _ = trimesh.proximity.closest_point(m, LED[None])
        res['closest_mm'][k] = {'dist': round(float(dist[0]), 2), 'point': c[0].round(1).tolist()}
    # sight line LED -> hole: clearance of its axis to parts (from 3 mm in front of the LED, above the USB-C shells)
    u = (HOLE - LED) / np.linalg.norm(HOLE - LED)
    t = np.linspace(0, (79.6 - LED[0]) / u[0], 200)
    P = LED + t[:, None] * u
    P = P[np.dot(P - LED, N) > 3.0]
    res['sightline'] = {'hole_centre': HOLE.tolist(), 'hole_diameter': HOLE_D, 'length_mm': round(float(np.linalg.norm(HOLE - LED)), 1),
                        'off_led_axis_deg': round(float(np.degrees(np.arccos(u @ N))), 1),
                        'view_direction_from_hole': u.round(3).tolist(),
                        'view_cone_half_angle_deg': round(float(np.degrees(np.arctan((HOLE_D / 2 + 0.5) / np.linalg.norm(HOLE - LED)))), 1),
                        'axis_clearance_mm': {}}
    for k in ('camera_13m214', 'usb_c_power', 'usb_c_otg_dp', 'head_cap', 'clip_cap', 'amplifier'):
        res['sightline']['axis_clearance_mm'][k] = round(float(trimesh.proximity.closest_point(M[k], P)[1].min()), 2)
    # rays through the hole rim: only the face panel may be hit, nothing beyond it
    rim = {}
    for a in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        q = HOLE + HOLE_D / 2 * np.array([0, np.cos(a), np.sin(a)])
        d = (q - LED) / np.linalg.norm(q - LED)
        hits = sorted({k for k, m in M.items() if k != 'face_panel' and len(m.ray.intersects_location([LED], [d])[0])})
        rim[f'{np.degrees(a):.0f}'] = hits
    res['sightline']['rim_ray_hits_other_than_face'] = rim
    # wires (guide route centrelines) near the sight line
    routes = json.loads(ROUTES.read_text())['routes']
    near = []
    AB = HOLE - LED
    for k, v in routes.items():
        pts = v.get('points') if isinstance(v, dict) else v
        try:
            Pp = np.array(pts, float)
        except (TypeError, ValueError):
            continue
        if Pp.ndim != 2 or Pp.shape[1] != 3 or len(Pp) < 2:
            continue
        Q = np.vstack([np.linspace(a, b, 40) for a, b in zip(Pp[:-1], Pp[1:])])
        tt = np.clip(((Q - LED) @ AB) / (AB @ AB), 0, 1)
        dd = np.linalg.norm(Q - (LED + tt[:, None] * AB), axis=1)
        i = int(dd.argmin())
        if dd[i] < 6:
            near.append({'route': k, 'axis_dist_mm': round(float(dd[i]), 1), 'at': Q[i].round(1).tolist()})
    res['sightline']['wire_routes_within_6mm'] = sorted(near, key=lambda r: r['axis_dist_mm'])
    # hole margins on the face front
    res['hole_margins_mm'] = {
        'eye_trim_outer_r15': round(float(np.hypot(HOLE[1] + 0.09, HOLE[2] - 131.11) - 15 - HOLE_D / 2), 1),
        'camera_boss_y-14.09_z145.11_r2.4': round(float(np.hypot(HOLE[1] + 14.09, HOLE[2] - 145.11) - 2.4 - HOLE_D / 2), 1),
        'head_cap_nearest': round(float(trimesh.proximity.closest_point(M['head_cap'], [HOLE])[1][0] - HOLE_D / 2), 1),
    }
    (HERE / 'led_sightline.json').write_text(json.dumps(res, indent=1))
    figure(M)
    print(json.dumps(res, indent=1))


def figure(M):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    cols = {'head_cap': '#dddddd', 'face_panel': '#f4f4f4', 'eye_trim': '#333333', 'camera_13m214': '#3a7d44',
            'usb_c_otg_dp': '#999999', 'usb_c_power': '#999999'}
    pcb = trimesh.load(G / 'a7z-head/a7z_parts/a7z_pcb.stl', force='mesh')
    fig, axs = plt.subplots(1, 2, figsize=(13, 6.2))
    views = [(79.9, ('head_cap', 'face_panel', 'eye_trim'), 'Front of the face: proposed 3 mm hole (blue), LED behind it (red)'),
             (55.0, ('camera_13m214', 'usb_c_otg_dp', 'usb_c_power', 'pcb'), 'Behind the face (face, trim and cap hidden): A7Z, camera board')]
    for ax, (xmin, keys, title) in zip(axs, views):
        polys, fc, depth = [], [], []
        for k in keys:
            m = pcb if k == 'pcb' else M[k]
            c = '#2e8b57' if k == 'pcb' else cols[k]
            tri = m.triangles[m.triangles[:, :, 0].max(1) > xmin]
            for t_ in tri:
                polys.append(t_[:, [1, 2]]); fc.append(c); depth.append(t_[:, 0].mean())
        o = np.argsort(depth)
        ax.add_collection(PolyCollection([polys[i] for i in o], facecolors=[fc[i] for i in o], edgecolors='#00000010', linewidths=0.1))
        ax.plot(LED[1], LED[2], 'r*', ms=14)
        ax.add_patch(plt.Circle((HOLE[1], HOLE[2]), HOLE_D / 2, fill=False, color='b', lw=2))
        ax.set_xlim(-50, 50); ax.set_ylim(105, 160); ax.set_aspect('equal'); ax.grid(alpha=.3)
        ax.set_xlabel("world y (mm); seen from the front, the duck's right (-y) is on the left"); ax.set_ylabel('z (mm)')
        ax.set_title(title, fontsize=9)
    fig.tight_layout(); fig.savefig(HERE / 'led-window-front.png', dpi=110)


if __name__ == '__main__':
    main()
