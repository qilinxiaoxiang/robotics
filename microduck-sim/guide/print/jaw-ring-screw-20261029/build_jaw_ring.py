#!/usr/bin/env python3
"""Cup ring for the right (-Y) jaw pivot, held by one M2 x 10 from outside (Shawn 2026-10-29, DESIGN-CONTRACT.json).

The old mouth sliding ring (ID 10.5, OD 14, flange dia 16.4 x 0.3) slips over the dia 10.0 boss on the inside of the
-Y jaw arm with 0.25 mm per side and nothing holds it; it fell off. Without a ring the boss rattles 2.3 mm per side in
the r 7.3 seat. The first cup (2.1 mm tall: a 1.5 mm plate under a 0.6 mm lip, on a boss cut back 2 mm) kept to the old
ring's envelope so the jaw could spring in as before, and failed to print three times. The seat formed by the lower
shell (yellow) and the jaw support (black) is about 10 mm long along the axis: bore r 7.3 at y -39.5..-37.5 and
-36.0..-35.5, r 8.4 between and beyond, so a dia 14 cup can run to y -33.5.
This part: the OD 14 sleeve over the whole uncut boss (y -39.6 to the boss end at -37.0, 0.2 mm clearance to -36.8),
then a solid 3.3 mm bottom to y -33.5 with a dia 1.6 pilot; 6.1 mm overall. The arm hole is drilled to 2.5 by hand and
one M2 x 10 from outside the arm (head on the arm outer face, through the 4.8 mm arm and boss) threads 2.7 mm into the
bottom. Because the cup reaches past the old ring end, it is fitted after the jaw is sprung into the lower shell: dropped
into the open lower half-seat beside the boss end and slid outboard onto the boss, before the jaw support goes on.

Outputs (robot frame mm unless said): build/jaw_ring_capped-world.stl, build/jaw_ring_capped-print.stl (closed end on
the bed, sleeve up), build/jaw_frame_drilled-world.stl (the printed jaw with the 2.5 drill: guide model of the as-built
jaw, not a print), checks.json.
    /tmp/microduck-cad-venv/bin/python build_jaw_ring.py
"""
import json, base64
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
BUILD = HERE / 'build'
PRINT = HERE.parent
GUIDE = PRINT.parent
SIM = GUIDE.parent
WORLD = PRINT / 'world'
OLD_RING = SIM / 'build-pack-20260913/redesign-20260913/workflow-review-20261009/central-cad/fusion-C-meshes/mouth_sliding_ring.stl'
JAW = WORLD / 'jaw_frame-v18.stl'          # the printed jaw (copy of the V1.8 world/jaw_frame.stl)

AX = np.array([26.1, 118.62])              # jaw axis (x, z); the axis runs along +Y (steps.py jaw_pose)
R_OUT, R_IN, R_PILOT = 7.0, 5.25, 0.8      # sleeve OD 14 and ID 10.5 as the old ring; pilot dia 1.6 for M2 TAP
# The arm face has a 0.3 mm shoulder round the boss root out to r 6.0 (face y -39.7, -40.0 beyond); the old ring's
# flange stepped over it, the sleeve starts where the old sleeve did, 0.1 mm off the shoulder.
Y_ARM_SIDE, Y_BOSS_END, Y_BORE, Y_END = -39.6, -37.0, -36.8, -33.5   # sleeve start; printed boss end; bore floor; cup end
DRILL_R = 1.25                             # arm hole drilled from dia 2.0 to 2.5
SCREW_L, HEAD_D, LEAD_IN = 10.0, 3.8, 0.3  # M2 x 10 TAP from stock (even lengths only)
SLIDE_MM = Y_BORE - Y_BOSS_END + (Y_BOSS_END - Y_ARM_SIDE)   # the cup slides this far outboard onto the boss when fitted (2.8)
ROLL_AXIS = (0.0, 115.6)                   # head roll axis along x through (y, z) = roll ring centres (guide data)
ROLL_TRAINED = 0.31                        # rad, trained head-roll delta (D-015)


def cyl(r, y0, y1, sections=96):
    c = trimesh.creation.cylinder(radius=r, height=y1 - y0, sections=sections)
    c.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0]))   # z axis -> +y
    c.apply_translation([AX[0], (y0 + y1) / 2, AX[1]])
    return c


def guide_mesh(key):
    d = json.loads((GUIDE / 'data/guide-data.json').read_text())
    P = {p['key']: p for p in d['parts']} if isinstance(d['parts'], list) else d['parts']
    v = np.frombuffer(base64.b64decode(P[key]['positionB64']), dtype='<f4').reshape(-1, 3)
    f = np.frombuffer(base64.b64decode(P[key]['indexB64']), dtype='<u4').reshape(-1, 3)
    return trimesh.Trimesh(v, f, process=False)


def first_hits(mesh, origin, direction):
    loc, _, _ = mesh.ray.intersects_location([origin], [direction])
    return np.sort((loc.reshape(-1, 3) - origin) @ np.asarray(direction, float)) + np.dot(origin, direction)


def min_dist(mesh, pts):
    return round(float(np.abs(trimesh.proximity.signed_distance(mesh, pts)).min()), 2)


def main():
    BUILD.mkdir(exist_ok=True)
    ring = cyl(R_OUT, Y_ARM_SIDE, Y_END).difference(cyl(R_IN, Y_ARM_SIDE - 1, Y_BORE))
    ring = ring.difference(cyl(R_PILOT, Y_ARM_SIDE - 1, Y_END + 1))
    assert ring.is_watertight and ring.is_volume
    ring.export(BUILD / 'jaw_ring_capped-world.stl')
    # print pose: closed end (y -33.5) on the bed, sleeve up: x' = x - 26.1, y' = z - 118.62, z' = -y - 33.5
    T = np.array([[1, 0, 0, -AX[0]], [0, 0, 1, -AX[1]], [0, -1, 0, -abs(Y_END)], [0, 0, 0, 1]], float)
    pr = ring.copy(); pr.apply_transform(T)
    pr.apply_translation([0, 0, -pr.bounds[0, 2]])
    pr.export(BUILD / 'jaw_ring_capped-print.stl')

    jaw0 = trimesh.load(JAW)
    jaw = jaw0.difference(cyl(DRILL_R, -50.0, Y_BOSS_END + 0.5))
    assert jaw.is_watertight
    jaw.export(BUILD / 'jaw_frame_drilled-world.stl')
    boss_end = -float(first_hits(jaw, np.array([AX[0] + 3.0, -30.0, AX[1]]), [0, -1, 0])[0])   # inboard end of the boss at r 3 (first hit, projection is -y)

    old = trimesh.load(OLD_RING)
    shell = trimesh.load(WORLD / 'head_bottom.stl'); sup = trimesh.load(WORLD / 'jaw_support.stl')
    m13 = guide_mesh('motor13')

    surf = ring.sample(6000)
    pts = trimesh.sample.volume_mesh(ring, 15000)
    into_jaw = np.zeros(len(pts), bool)
    for i in range(0, len(pts), 1500):                    # ray-based contains in chunks keeps the job under its memory budget
        into_jaw[i:i + 1500] = jaw.contains(pts[i:i + 1500])
    clear = {'jaw_frame_drilled': dict(ringSamplesInsideJaw=int(into_jaw.sum()), bossEndY=round(boss_end, 2),
                                       bossEndToBoreFloorMm=round(Y_BORE - boss_end, 2), sleeveToShoulderMm=round(Y_ARM_SIDE - (-39.7), 2))}
    for name, m in (('head_bottom', shell), ('jaw_support', sup), ('motor13', m13)):
        clear[name] = dict(insideCount=int(m.contains(surf).sum()) if m.is_watertight else None, minDistanceMm=min_dist(m, surf[::10]))

    # fit path after the jaw is sprung in (jaw support not yet on): the cup comes down from above into the lower half-seat
    # beside the boss end, shifted SLIDE_MM inboard, then slides outboard onto the boss. Sampled against the lower shell and the jaw.
    path = []
    for dz in (12.0, 8.0, 4.0, 2.0, 0.0):
        p = surf[::6] + [0.0, SLIDE_MM, dz]
        path.append(dict(stage='drop', dyMm=SLIDE_MM, dzMm=dz, shellInside=int(shell.contains(p).sum()), jawInside=int(jaw.contains(p).sum())))
    for dy in np.linspace(SLIDE_MM, 0.0, 8):
        p = surf[::6] + [0.0, dy, 0.0]
        path.append(dict(stage='slide', dyMm=round(float(dy), 2), dzMm=0.0, shellInside=int(shell.contains(p).sum()), jawInside=int(jaw.contains(p).sum()),
                         shellMinMm=min_dist(shell, p[::8])))
    path_ok = all(s['shellInside'] == 0 and s['jawInside'] == 0 for s in path)

    # screw stack along the axis from outside
    o = np.array([AX[0], -60.0, AX[1]])
    seat = []                                            # outer arm face under the head (r 1.95, outside the 2.5 hole)
    for a in np.radians(np.arange(0, 360, 30)):
        oo = o + [1.95 * np.cos(a), 0, 1.95 * np.sin(a)]
        seat.append(float(first_hits(jaw, oo, [0, 1, 0])[0]))
    head_seat = max(seat)
    tip = head_seat + SCREW_L
    in_bottom = min(tip, Y_END) - Y_BORE - (LEAD_IN if tip < Y_END else 0.0)
    hole_r = []
    for y in (-43.0, -41.0, -39.5, -37.5):
        oc = np.array([AX[0], y, AX[1]])
        dirs = [np.array([np.cos(a), 0, np.sin(a)]) for a in np.radians(range(0, 360, 15))]
        hole_r.append(round(min(float(first_hits(jaw, oc, d)[0] - oc @ d) for d in dirs), 3))
    # screw tip and ring against ID13 over the trained head roll (ID13 is on the fork side of the roll joint)
    def roll(p, th):
        y, z = p[..., 1] - ROLL_AXIS[0], p[..., 2] - ROLL_AXIS[1]
        q = p.copy(); q[..., 1] = ROLL_AXIS[0] + y * np.cos(th) - z * np.sin(th); q[..., 2] = ROLL_AXIS[1] + y * np.sin(th) + z * np.cos(th)
        return q
    tip_pts = np.array([[AX[0] + dx, tip, AX[1] + dz] for dx in (-1, 0, 1) for dz in (-1, 0, 1)])
    roll_clear = {}
    for th in (-ROLL_TRAINED, 0.0, ROLL_TRAINED):
        p = np.vstack([roll(surf[::20], -th), roll(tip_pts, -th)])   # head rolls by th relative to the fork = fork by -th relative to the head
        roll_clear[f'{th:+.2f}'] = min_dist(m13, p)

    walls = dict(sleeveWallMm=R_OUT - R_IN, bottomMm=round(Y_END - Y_BORE, 2), pilotToBoreMm=R_IN - R_PILOT, sleeveHeightMm=round(Y_BORE - Y_ARM_SIDE, 2))
    checks = dict(
        part=dict(outerDiameterMm=2 * R_OUT, boreMm=2 * R_IN, pilotMm=2 * R_PILOT, lengthMm=round(Y_END - Y_ARM_SIDE, 2),
                  printSizeMm=(pr.bounds[1] - pr.bounds[0]).round(2).tolist(), volumeMm3=round(float(ring.volume), 1),
                  bedContactMm2=round(float(pr.area_faces[np.abs(pr.triangles[:, :, 2]).max(1) < 1e-3].sum()), 1)),
        walls=walls, wallsOk=min(walls.values()) >= 1.2,
        seat=dict(ringY=[Y_ARM_SIDE, Y_END], oldRingYmax=round(float(old.bounds[1, 1]), 2), bossEndY=round(boss_end, 2), bossCut=False,
                  lowerShellBoreRadiusMm={'-39.5..-37.5': 7.3, '-36.0..-35.5': 7.3, 'between and beyond': 8.4}, playWithoutRingPerSideMm=2.3,
                  radialPlayWithRingPerSideMm=dict(bossInBore=R_IN - 5.0, ringInSeat=round(7.3 - R_OUT, 2))),
        fitPath=dict(ok=path_ok, slideMm=round(SLIDE_MM, 2), stages=path,
                     note='cup dropped into the open lower half-seat beside the boss end (jaw support off), then slid outboard onto the boss'),
        clearances=clear,
        screw=dict(spec='M2 × 10 TAP', headSeatY=round(head_seat, 2), tipY=round(tip, 2), threadInBottomMm=round(in_bottom, 2),
                   tipToCupEndMm=round(Y_END - tip, 2), drilledHoleRadiusMm=hole_r, originalHoleDiameterMm=2.0, rollClearanceToID13Mm=roll_clear),
        sources={'oldRing': str(OLD_RING), 'jaw': str(JAW)})
    (HERE / 'checks.json').write_text(json.dumps(checks, indent=1, ensure_ascii=False))
    print(json.dumps(checks, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
