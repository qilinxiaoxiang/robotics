"""What the cap could become once no wire lies in the rear lane: rerun build_f.search_radii with the board and 5991 limits
only (no wire points), and the rearmost body point that sets the cap depth. Writes probe/cap_no_wires.json. Study only;
nothing is built."""
import sys, json, copy
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; D = HERE.parent
sys.argv = [sys.argv[0], 'F']; sys.path.insert(0, str(D)); import build_f as B
meshes = B.board_meshes()
out = {}
for tag, wp in (('withInsideWires (V1.11)', B.wires()), ('noWires', {})):
    pts, clr, tags = B.body_points(meshes, wp)
    ol = B.outline(); res = B.search_radii(ol, pts, clr, tags)
    out[tag] = {k: dict(radius=v['radius'], limitedBy=v['limitedBy']) for k, v in res.items()}
# rearmost body points (cap depth): XL meshes and 5991 boxes, outside the window bands
allp = np.vstack([m.vertices for m in meshes.values()])
i = int(np.argmin(allp[:, 0])); out['rearmostXL'] = dict(x=round(float(allp[i, 0]), 3), at=np.round(B.real_pts(allp[i]), 2).tolist())
pdx = min(float(lo[0]) for lo, hi in B.pd_boxes().values()); out['rearmost5991'] = round(pdx, 3)
out['capInnerFaceNow'] = B.X_LI; out['laneWirePlaneNow'] = round(B.X_W, 3)
out['capInnerFaceMinWith0p3'] = round(min(out['rearmostXL']['x'], pdx) - 0.3, 3)
(HERE / 'cap_no_wires.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
