"""Check the V1.38 rear converter box cap (D-034): the four screw columns bear on the boards and the cap rim stays clear of
the frame, so the columns, not the rim, locate the cap and carry the screw load. Reads the layout-F world STLs (real
world, mm) and layout_f.json; writes checks.json and build/rear_lid-world.stl (the contract input).

- column fronts: gap from each column front to the board face under it, measured on the real board meshes by rays
  parallel to x on the column annulus (clearance hole r 1.15 to column r 2.8); zero or a few hundredths means touching
  (the XL4015 pad is 0.05 proud of its PCB, so the top fronts sit on the pad and within 0.06 of the PCB beyond it).
- other board parts: nearest real board vertex (any body) to each column outside its front 0.1 mm, i.e. nothing else on
  the board is touched by the longer column.
- frame: minimum cap-frame distance and where it occurs (cap vertices to the frame surface).

    /tmp/microduck-cad-venv/bin/python check_lid_columns.py"""
import json, shutil
from pathlib import Path
import numpy as np, trimesh

HERE = Path(__file__).resolve().parent
LF = HERE.parent / 'layout-F'
L = json.loads((LF / 'layout_f.json').read_text())
load = lambda n: trimesh.load(str(LF / n), force='mesh')
cap, frame = load('rear_lid-world.stl'), load('rear_frame-world.stl')
boards = {'pd5991': load('pd5991_F-world.stl'), 'xl4015_top_7V': load('xl4015_top_7V-world.stl')}
R_COL, R_CLR = 2.8, 1.15
cols = [('pd5991_plus_y', L['capScrew'], 'pd5991'), ('pd5991_minus_y', L['capScrew2'], 'pd5991')]
cols += [('top_%s_y' % ('plus' if a[0] > 0 else 'minus'), dict(L['capTopScrews'], axisYZ=a), 'xl4015_top_7V') for a in L['capTopScrews']['axesYZ']]

out = dict(columns={})
for name, c, bk in cols:
    (Y, Z), front = c['axisYZ'], c['columnX'][1]
    b = boards[bk]
    pts = np.array([[front - 5.0, Y + r * np.cos(a), Z + r * np.sin(a)] for r in np.linspace(R_CLR + 0.15, R_COL - 0.05, 4)
                    for a in np.linspace(0, 2 * np.pi, 24, endpoint=False)])
    # keep only rays that start inside the cap column (the +y low column is flattened above the USB-C socket)
    inside = cap.contains(pts + [5.0 - 0.05, 0, 0])
    loc, ri, _ = b.ray.intersects_location(pts[inside], np.tile([1.0, 0, 0], (int(inside.sum()), 1)))
    first = {}
    for p, i in zip(loc, ri):
        first[i] = min(first.get(i, 1e9), p[0])
    face = np.array(list(first.values()))
    # every other board vertex near the column: radial distance and x, outside the 0.1 mm at the front
    v = np.vstack([m.vertices for m in boards.values()])
    rad = np.hypot(v[:, 1] - Y, v[:, 2] - Z); near = (v[:, 0] < front - 0.1) & (v[:, 0] > c['columnX'][0])
    out['columns'][name] = dict(
        frontX=front, raysOnBoard=int(len(face)), raysTotal=int(inside.sum()),
        gapToBoardMm=dict(min=round(float(face.min() - front), 3), median=round(float(np.median(face - front)), 3), max=round(float(face.max() - front), 3),
                          fractionWithin006=round(float(np.mean(face - front <= 0.06)), 3)) if len(face) else None,
        nearestOtherBoardVertexRadialMm=round(float(rad[near].min()), 2) if near.any() else None)
q = trimesh.proximity.ProximityQuery(frame)
d = -q.signed_distance(cap.vertices)            # positive outside the frame
i = int(np.argmin(d))
cap_x = cap.vertices[:, 0]
outer = (np.abs(cap.vertices[:, 1]) > 31.9) | (cap.vertices[:, 2] > 42.9)     # the cap's outer side and top walls
out['frame'] = dict(minGapMm=round(float(d.min()), 3), at=np.round(cap.vertices[i], 2).tolist(),
                    capRimX=round(float(cap_x[outer].max()), 3),
                    frameRimX=L['box']['frameRimX'])
ok_cols = all(r['gapToBoardMm'] and r['gapToBoardMm']['median'] <= 0.05 and r['gapToBoardMm']['min'] >= -0.01
              and r['gapToBoardMm']['fractionWithin006'] >= 0.9 and r['raysOnBoard'] >= 0.8 * r['raysTotal'] for r in out['columns'].values())
out['ok'] = dict(columnsBearOnBoards=ok_cols, frameClearMm=out['frame']['minGapMm'] >= 0.2,
                 rimGapMm=round(out['frame']['frameRimX'] - out['frame']['capRimX'], 3),
                 nothingElseTouched=all((r['nearestOtherBoardVertexRadialMm'] or 99) > 3.0 for r in out['columns'].values()))
(HERE / 'build').mkdir(exist_ok=True)
shutil.copyfile(LF / 'rear_lid-world.stl', HERE / 'build/rear_lid-world.stl')
(HERE / 'checks.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
