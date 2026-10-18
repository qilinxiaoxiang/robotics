"""Exact gap between the box front and the rear edge of the torso shells at the shell top (where a wire from outside
the box would have to drop into the pack). Writes probe/shell_gap.json."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; D = HERE.parent
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit'); import ia_lib
fr = trimesh.load(str(D / 'frame_hidden_noP1-world.stl'), force='mesh')
out = {}
for k in ('shell_left', 'shell_right'):
    m = trimesh.Trimesh(*ia_lib.load_solid(k), process=False)
    p, _ = trimesh.sample.sample_surface(m, 400000, seed=2); p = np.vstack([p, m.vertices])
    s = np.sign(np.mean(m.vertices[:, 1]))
    sel = (p[:, 0] < -43) & (p[:, 2] > 29.0)
    q = p[sel]
    rows = {}
    for y0 in range(0, 32, 2):
        b = q[(s * q[:, 1] >= y0) & (s * q[:, 1] < y0 + 2)]
        if len(b):
            i = np.argmin(b[:, 0]); rows[f'|y| {y0}..{y0+2}'] = dict(shellRearX=round(float(b[i, 0]), 2), atZ=round(float(b[i, 2]), 2),
                                                                   gapToBoxFrontX_m46p5=round(float(b[i, 0] + 46.5), 2))
    # lip underside above the cover plate top (z 29.5) for |y| < 17
    lip = q[(q[:, 0] > -47) & (q[:, 0] < -44.5) & (np.abs(q[:, 1]) < 17)]
    # exact distance shell -> frame in the top region
    cp, d, _ = trimesh.proximity.closest_point(fr, q[::5]); i = int(np.argmin(d))
    out[k] = dict(rearEdgeByY=rows, lipUndersideMinZ_xm47_to_m44p5=round(float(lip[:, 2].min()), 2) if len(lip) else None,
                  minDistToFrameAboveZ29=round(float(d[i]), 2), at=np.round(q[::5][i], 2).tolist(), frameAt=np.round(cp[i], 2).tolist())
(HERE / 'shell_gap.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
