"""Support extrusion near the notched-cap edit box (+3 mm), mapped to the robot frame and the notch local frame (s outward, u tangent, v up the wall).
Pass criterion: no support inside either zip-tie slot or inside the 6.7 mm cable-passage core; other notch/hood supports are open and reachable."""
import sys, json, re, numpy as np, trimesh; sys.dont_write_bytecode = True; sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.6/scripts')
import release_pipeline as r
from pathlib import Path
R = Path('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.6')
def check(machine, B, color='Orange'):
    rep = json.load(open(R / 'evidence/cap-notch-report-snapshot.json'))
    L = rep['localFrame']; n, u, b, o = (np.array(L[k]) for k in ('n_outwardWallNormal', 't_wallTangent', 'b_upAlongWall', 'originWorld'))
    prep = r.read(R / 'run/preparation.json'); row = next(x for x in prep['rows'] if x['color'] == color and x['machine'] == machine)
    t = np.array(next(p['translation'] for p in row['placements'] if p['key'] == 'head_cap')); part = next(p for p in prep['parts'] if p['key'] == 'head_cap')
    g, cfg, _ = r.native_payload(R / f'run/native/{color}_{machine}/sliced.3mf'); off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if machine == 'Bambu' else [0., 0.]
    xyz = [0., 0., 0.]; kind = ''; pts = []
    for line in g.decode().splitlines():
        if line.startswith(('; FEATURE:', ';TYPE:')): kind = line.split(':', 1)[1].strip().lower()
        if not re.match(r'^G[0123] ', line): continue
        v = {k: float(q) for k, q in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', line.split(';')[0])}
        end = [v.get(k, xyz[i]) for i, k in enumerate('XYZ')]
        if v.get('E', 0) > 0 and 'support' in kind:
            for f in np.linspace(0, 1, 6):
                p = [xyz[0] + f * (end[0] - xyz[0]) + off[0], xyz[1] + f * (end[1] - xyz[1]) + off[1], end[2]]
                if all(B[0][i] - 3 <= p[i] <= B[1][i] + 3 for i in range(3)): pts.append(p)
        xyz = end
    if not pts: return dict(machine=machine, supportPointsNearEditBox=0, inTieSlots=0, inCablePassageCore=0, passed=True)
    P = np.array(pts); W = np.array(rep['worldToPrint']['matrix4x4'])
    Pw = (np.linalg.inv(W) @ np.c_[P - t - [0, 0, part['dropToBedMm']], np.ones(len(P))].T).T[:, :3]
    loc = np.c_[(Pw - o) @ n, (Pw - o) @ u, (Pw - o) @ b]
    slots = sum(int(((abs(loc[:, 1] - cu) <= 2.0) & (loc[:, 0] >= 0.8) & (loc[:, 0] <= 4.2) & (Pw[:, 2] > 119.0) & (Pw[:, 2] < 123.5)).sum()) for cu in (-4.4, 4.4))
    core = int(((loc[:, 0] > -6) & (loc[:, 0] < 5.6) & (np.abs(loc[:, 1] + 1.0) < 3.4) & (np.abs(loc[:, 2] - 0.5) < 3.4)).sum())
    return dict(machine=machine, supportPointsNearEditBox=len(P), worldBounds=[Pw.min(0).round(2).tolist(), Pw.max(0).round(2).tolist()],
                outwardRangeMm=[round(float(loc[:, 0].min()), 1), round(float(loc[:, 0].max()), 1)], inTieSlots=slots, inCablePassageCore=core, passed=slots == 0 and core == 0)
