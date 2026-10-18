#!/usr/bin/env python3
"""Renders of the release bundle route against the left-rear route, at head roll -25 / 0 / +25 deg (MJCF range), with
guide/content/render.py (vtk, light background, guide part colours). Writes renders/<route>_roll<deg>_<view>.png and
composite grids. Run in the CAD venv through the bounded runner."""
import sys, json, os
os.environ['EXT19_IA_CACHE'] = '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache'
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/scripts')
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content')
import numpy as np, trimesh
import ext_lib as E
import render as GR
from nr_lib import FK, body_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(HERE), 'renders'); os.makedirs(OUT, exist_ok=True)
G = E.ia_lib.load_guide(); COLOR = {p['key']: p['color'] for p in G['parts']}
hexc = lambda h: [int(h[i:i + 2], 16) for i in (1, 3, 5)]
ROUTES = json.load(open(os.path.join(HERE, 'routes_candidates.json')))
EXTRA = {'amplifier': 'jaw_soft', 'speaker': 'jaw_soft', 'speaker_retainer': 'jaw_soft', 'speaker_tape': 'jaw_soft', 'clip_head': 'jaw_soft',
         'clip_cap': 'jaw_soft', 'clip_torso': 'trunk_base', 'clip_bracket': 'neck_pitch', 'rear_frame': 'trunk_base', 'rear_lid': 'trunk_base',
         'xl4015_top': 'trunk_base', 'xl4015_mid': 'trunk_base', 'pd5991': 'trunk_base'}
AUDIO = json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/route-v19.json'))['audioWires']['polylines']
ROUTE_COLOR = {'designed': [200, 30, 30], 'leftrear': [20, 140, 60], 'hybrid': [30, 60, 200]}

def tube(pts, r=1.7, seg=14):
    pts = np.asarray(pts, float); keep = [0]
    for i in range(1, len(pts)):
        if np.linalg.norm(pts[i] - pts[keep[-1]]) > 0.05: keep.append(i)
    pts = pts[keep]
    # densify so the tube follows corners
    d = [pts[0]]
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(2, int(np.ceil(np.linalg.norm(b - a) / 2.0)))
        d += list(np.linspace(a, b, n + 1)[1:])
    pts = np.array(d)
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

def main():
    fk = FK(); man = E.ia_lib.manifest()
    solids = {}
    for k in man:
        b = body_of(k) or EXTRA.get(k)
        if b is None: continue
        v, f = E.ia_lib.load_solid(k)
        if v[:, 2].max() < 20: continue
        solids[k] = (v, f, b, man[k].get('module', 'x'))
    def cam(target, direction, dist, up=(0, 0, 1)):
        d = np.asarray(direction, float); d /= np.linalg.norm(d); t = np.asarray(target, float)
        return [list(t + dist * d), list(t), list(up)]
    VIEWS = {'rearleft': cam([20, 0, 100], (-1.0, 0.85, 0.55), 300), 'top': cam([22, 0, 120], (0.02, 0.0, 1.0), 290, up=(1, 0, 0)),
             'right': cam([22, 0, 100], (0.25, -1.0, 0.3), 300)}
    files = {}
    for rname in ('designed', 'leftrear'):
        r = ROUTES[rname]; excl = set(r.get('exclude', []))
        pts = np.array([p[:3] for p in r['points']], float); bodies = [p[3] for p in r['points']]
        for roll in (-25.0, 0.0, 25.0):
            q = {'head_roll': np.radians(roll), 'jaw': 0.0}
            T = fk.part_T(q)
            sc = {}
            for k, (v, f, b, mod) in solids.items():
                if k in excl: continue
                vv = v @ T[b][:3, :3].T + T[b][:3, 3]
                col = hexc(COLOR.get(k, '#b0b0b0'))
                if k.startswith('clip_'): col = [240, 120, 20]
                sc[k] = part(vv, f, col, mod)
            W = np.array([T[b][:3, :3] @ p + T[b][:3, 3] for p, b in zip(pts, bodies)])
            v, f = tube(W); sc['route'] = part(v, f, ROUTE_COLOR[rname], 'route')
            for nm, pl in AUDIO.items():
                Pw = np.array(pl, float) @ T['jaw_soft'][:3, :3].T + T['jaw_soft'][:3, 3]
                v, f = tube(Pw, r=0.65, seg=8); sc[f'audio_{nm}'] = part(v, f, [120, 40, 160], 'route')
            ghost = {'head_cap', 'speaker_retainer', 'speaker', 'speaker_tape', 'shell_left', 'shell_right', 'face_panel', 'eye_trim'}
            for vname, view in VIEWS.items():
                hide = {'face_panel', 'eye_trim', 'camera_board'} if vname == 'top' else set()
                if vname == 'top': hide |= {'head_cap', 'speaker_retainer', 'speaker', 'speaker_tape', 'rear_lid'}
                out = os.path.join(OUT, f'{rname}_roll{int(roll):+d}_{vname}.png')
                fn = GR.render(sc, [view], out, size=(1000, 900), ghost=ghost, hide=hide)[0]
                os.replace(fn, out); files[f'{rname}_roll{int(roll):+d}_{vname}'] = out; print(out, flush=True)
    # composites: per view, rows = route, cols = roll
    from PIL import Image, ImageDraw
    for vname in VIEWS:
        tiles = [[Image.open(files[f'{rn}_roll{rl:+d}_{vname}']) for rl in (-25, 0, 25)] for rn in ('designed', 'leftrear')]
        w, h = tiles[0][0].size; pad = 36
        grid = Image.new('RGB', (3 * w, 2 * h + pad), (245, 245, 242)); dr = ImageDraw.Draw(grid)
        for i, rn in enumerate(('designed', 'leftrear')):
            for j, rl in enumerate((-25, 0, 25)):
                grid.paste(tiles[i][j], (j * w, pad + i * h))
                dr.text((j * w + 12, pad + i * h + 10), f'{"release route (V1.9 clips)" if rn == "designed" else "left-rear route (no lower clips)"}   head roll {rl:+d} deg', fill=(20, 20, 20))
        dr.text((12, 10), f'view: {vname}. red tube = release route, green tube = left-rear route (1.7 mm group radius); amplifier/speaker jumpers purple; clips orange; cap/speaker ghosted', fill=(20, 20, 20))
        gp = os.path.join(OUT, f'compare_{vname}.png'); grid.save(gp); print(gp, flush=True)

if __name__ == '__main__':
    main()
