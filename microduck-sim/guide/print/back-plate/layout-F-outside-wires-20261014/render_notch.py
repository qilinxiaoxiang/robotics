"""Renders for the outside-wire draft with guide/content/render.py (vtk, light background, guide part colours).
renders/frame_noP1_*.png       frame (hidden-screw option, P1 filled) from the front, against the same frame with P1 open
renders/back_*.png             robot from behind with the eight outside wires (7V orange, 5V yellow, 15V + red, 15V - black)
renders/entry_*.png            close-up where the 7 V pair enters the pack through the head notch; existing cables grey
python render_outside.py  (CAD venv, bounded runner)."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; BP = HERE.parent; OUT = HERE / 'renders'; OUT.mkdir(exist_ok=True)
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content'); import render as GR
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit'); import ia_lib
from cables import spline_samples
OPT = BP / 'layout-F-ear-20261014' / 'options'; LF = BP / 'layout-F'
G = ia_lib.load_guide(); COLOR = {p['key']: p['color'] for p in G['parts']}
hexc = lambda h: [int(h[i:i + 2], 16) for i in (1, 3, 5)]
NETC = {'7V': [255, 128, 0], '5V': [240, 205, 0], 'p': [215, 20, 20], 'q': [25, 25, 25]}
W = json.loads((HERE / 'wires_F.json').read_text())


def tube(pts, r=0.9, seg=12):
    pts = np.asarray(pts, float); keep = [0]
    for i in range(1, len(pts)):
        if np.linalg.norm(pts[i] - pts[keep[-1]]) > 0.05:
            keep.append(i)
    pts = pts[keep]; ring = []
    t = np.gradient(pts, axis=0); t /= np.linalg.norm(t, axis=1)[:, None]
    n = np.cross(t[0], [0, 0, 1.0]) if abs(t[0][2]) < 0.9 else np.cross(t[0], [1.0, 0, 0]); n /= np.linalg.norm(n)
    V = []
    for i, p in enumerate(pts):
        n = n - (n @ t[i]) * t[i]; n /= np.linalg.norm(n); b = np.cross(t[i], n)
        for k in range(seg):
            a = 2 * np.pi * k / seg; V.append(p + r * (np.cos(a) * n + np.sin(a) * b))
    F = []
    for i in range(len(pts) - 1):
        for k in range(seg):
            a0, a1 = i * seg + k, i * seg + (k + 1) % seg; b0, b1 = a0 + seg, a1 + seg
            F += [[a0, b0, a1], [a1, b0, b1]]
    return np.array(V), np.array(F)


def part(v, f, color, module='x'):
    return dict(v=np.asarray(v, np.float32), f=np.asarray(f, np.int64), color=color, module=module)


def stl(path, color, module='box'):
    m = trimesh.load(str(path), force='mesh'); return part(m.vertices, m.faces, color, module)


def robot_scene(cables=False):
    sc = {}
    man = ia_lib.manifest()
    for k in man:
        if k in ('rear_frame', 'rear_lid'):
            continue
        v, f = ia_lib.load_solid(k); sc[k] = part(v, f, hexc(COLOR.get(k, '#b0b0b0')), man[k].get('module', 'x'))
    sc['frame'] = stl(HERE / 'frame_hidden_noP1_notch-world.stl', [237, 128, 26])
    sc['lid'] = stl(OPT / 'lid_hidden-world.stl', [250, 163, 64])
    sc['screw'] = stl(OPT / 'screw_hidden-world.stl', [90, 90, 95])
    for k, w in W.items():
        v, f = tube(w['points']); sc[f'wire_{k}'] = part(v, f, NETC[w['net']], 'wires')
    if cables:
        for c in G['cables']:
            if c['id'] in ('dxl-r5', 'dxl-l10', 'dxl-n12', 'uart', 'imu', 'bundle_neck'):
                x, _ = spline_samples(c['path']); v, f = tube(x[::4], float(c.get('radius') or 0.9), 10)
                sc[f'cable_{c["id"]}'] = part(v, f, [150, 150, 150], 'cables')
    return sc


def cam(target, direction, dist, up=(0, 0, 1)):
    d = np.asarray(direction, float); d /= np.linalg.norm(d); t = np.asarray(target, float)
    return [list(t + dist * d), list(t), list(up)]


if __name__ == '__main__':
    out = []
    # 1. frame with the two notches, seen from the front-top (the side the shells cover) and from behind-above
    sc = {'frame': stl(HERE / 'frame_hidden_noP1_notch-world.stl', [237, 128, 26])}
    out += GR.render(sc, [cam([-48, 7, 36], (1, 0.6, 0.9), 80), cam([-50, 0, 4], (1, 0.35, 0.25), 190)], str(OUT / 'frame_notch.png'), size=(900, 900))
    # 2. robot from behind, shells opaque (is the drop hidden?) and the same views with the shells see-through
    sc = robot_scene()
    cams = [cam([-40, 0, 10], (-1, 0.75, 0.55), 330), cam([-40, 0, 20], (-0.55, 0.25, 1.0), 300), cam([-40, 0, 10], (-1, -0.6, 0.45), 330)]
    out += GR.render(sc, cams, str(OUT / 'notch_back_opaque.png'), size=(1100, 1000))
    out += GR.render(sc, cams, str(OUT / 'notch_back_ghost.png'), size=(1100, 1000), ghost={'shell_left', 'shell_right'})
    # 3. close-up: the four wires over the box top, down through notch A and under the shell lip through notch B
    sc = robot_scene(cables=True)
    only = {k for k, p in sc.items() if p['module'] in ('wires', 'cables', 'box') or k in ('rear_pack', 'openrb_board', 'shell_left', 'shell_right', 'torso_base')}
    out += GR.render(sc, [cam([-47, 8, 38], (0.85, 0.75, 0.9), 70), cam([-47, 8, 36], (-0.3, 1.0, 0.6), 60), cam([-40, 6, 32], (0.4, 1.0, 0.25), 75)],
                     str(OUT / 'notch_entry.png'), size=(1000, 900), ghost={'shell_left', 'shell_right'}, only=only)
    print(json.dumps(out, indent=1))
