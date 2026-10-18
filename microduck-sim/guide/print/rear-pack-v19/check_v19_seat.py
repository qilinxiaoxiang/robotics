"""Checks for the V1.9 shell seat (proposal 2: grown T-head and shoulder bars) against the printed V1.8 side shells.
Writes check_v19_seat.json. Run under the bounded CAD runner.

1. gaps: exact manifold overlap and min_gap between the pack body and each shell, for V1.9 and (baseline) V1.8, globally and per
   region of the pack (plate top edge, bar top edge, ear/bar underside over the shell ribs, ear tip, plate side beside the ribs),
   with the closest point located on a 0.1 mm surface sample;
2. shells step (guide step 'shells', approach left [0, 40, 0], right [0, -40, 0]): each shell swept from its approach to its seat in
   0.5 mm steps, extended outwards until its box clears the pack box (steps_audit lead-in rule), against the V1.9 and V1.8 pack
   bodies; a hit is an overlap above the seated overlap by more than 0.5 mm3. Only the pack changed since the guide audit
   (steps_audit 2026-10-13: 0 path collisions), so the pack is the only obstacle swept here;
3. pack-in from the rear with both shells already on (the guide fits the shells later; this is the swap-in-place case): the pack
   (V1.9 with the BNO085 and its two M2 x 4 pre-mounted; V1.8 as baseline) moved backwards along -x from its seat until its box
   clears both shells, first and last colliding offset per shell;
4. screwdriver reach with the shells on: straight shafts to the two upper hip-yaw case screws (S10-case-072, S05-case-076, driven
   down) and the two lower ones (driven up), dia 3 and 5;
5. BNO085 bench screws: straight shafts along the screw axis (+y from the head top) at dia 6, 5, 4, 3 against the V1.9 pack body
   and the board model, nothing else present (the board is screwed on the bench before pack-in).
"""
import sys, json, time
from pathlib import Path
import numpy as np
import trimesh
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P  # noqa: E402
import ia_lib  # noqa: E402

t0 = time.time()
G = HERE.parent.parent
data = json.load(open(G / 'data' / 'guide-data.json'))
steps = {s['id']: s for s in data['steps']}
man = ia_lib.manifest()
V19m = P.load_stl(HERE / 'rear_pack-world.stl'); V19 = P.mesh_to_m(V19m)
V18m = P.load_stl(HERE.parent / 'rear-pack' / 'rear_pack-world.stl'); V18 = P.mesh_to_m(V18m)
SH = {k: (P.solid_mesh(k), P.solid_m(k)) for k in ('shell_left', 'shell_right')}
res = {'packV19': str(HERE / 'rear_pack-world.stl'), 'packV18': str(HERE.parent / 'rear-pack' / 'rear_pack-world.stl'),
       'shells': 'audit solid cache shell_left / shell_right (full-build source mesh = the printed 10/1 shells)'}

# ---------------------------------------------------------------- 1 gaps
REG = {  # pack sub-regions (boxes); the min_gap of pack ^ box is a per-region value (cut faces lie inside the pack)
    'plateTopEdge': ((-21.0, -30.0, 34.0), (-19.0, 30.0, 41.0)),
    'barTopEdge': ((-24.5, -30.0, 34.0), (-21.0, 30.0, 41.0)),
    'underside_over_ribs': ((-24.5, -28.0, 31.0), (-19.0, 28.0, 32.6)),
    'earTip': ((-24.5, -28.0, 31.0), (-19.0, 28.0, 36.0)),
    'plateSide_beside_ribs': ((-21.0, -21.6, 15.0), (-19.0, 21.6, 31.0)),
}


def side_box(lo, hi, s):
    lo = np.array(lo, float); hi = np.array(hi, float)
    if s > 0:
        lo[1] = max(lo[1], 0.0)
    else:
        hi[1] = min(hi[1], 0.0)
    return P.box(lo, hi)


def gaps(body, mesh, tag):
    out = {}
    c = mesh.triangles_center
    sub = mesh.submesh([np.flatnonzero((c[:, 0] > -25.5) & (c[:, 0] < -18.0) & (c[:, 2] > 14.0) & (np.abs(c[:, 1]) > 10.0))], append=True)
    sample, _ = trimesh.sample.sample_surface_even(sub, int(sub.area * 40), radius=0.1, seed=1)
    for k, (sm, S) in SH.items():
        s = 1 if k == 'shell_left' else -1
        row = dict(overlapMm3=round(float((body ^ S).volume()), 4), minGapMm=round(float(body.min_gap(S, 4.0)), 3))
        pts = sample[np.sign(sample[:, 1]) == s]
        cp, d, _ = trimesh.proximity.closest_point(sm, pts)
        j = int(np.argmin(d))
        row['closestSampledPackPoint'] = np.round(pts[j], 2).tolist(); row['closestShellPoint'] = np.round(cp[j], 2).tolist()
        row['sampledMinMm'] = round(float(d[j]), 3)
        row['regions'] = {}
        for rn, (lo, hi) in REG.items():
            part = body ^ side_box(lo, hi, s)
            if part.is_empty():
                row['regions'][rn] = None; continue
            sel = np.all((pts >= np.array(lo)) & (pts <= np.array(hi)), axis=1) & (np.sign(pts[:, 1]) == s)
            r = dict(minGapMm=round(float(part.min_gap(S, 4.0)), 3))
            if sel.any():
                jj = np.flatnonzero(sel)[int(np.argmin(d[sel]))]
                r['at'] = np.round(pts[jj], 2).tolist()
            row['regions'][rn] = r
        out[k] = row
    print(tag, json.dumps(out), flush=True)
    return out


res['gaps'] = {'V1.9': gaps(V19, V19m, 'V1.9'), 'V1.8': gaps(V18, V18m, 'V1.8')}


# ---------------------------------------------------------------- sweep helper
def sweep(mover, mbox, u, obst, start_t, stop_when_clear=True, step=0.5, t_max=200.0):
    """Offsets t*u for t from 0 (seat) up; collision = overlap above the seated overlap by > 0.5 mm3."""
    seated = {k: float((mover ^ S).volume()) for k, S, _ in obst}
    hits = {}; t = 0.0; clear_at = None; worst = {}
    while t <= t_max:
        off = u * t; lo = mbox[0] + off; hi = mbox[1] + off
        near = [(k, S) for k, S, b in obst if np.all(lo <= b[1]) and np.all(hi >= b[0])]
        if not near and t >= start_t:
            clear_at = t; break
        mv = mover.translate(off.tolist())
        for k, S in near:
            v = float((mv ^ S).volume()) - seated[k]
            if v > 0.5:
                hits.setdefault(k, []).append(round(t, 1)); worst[k] = max(worst.get(k, 0.0), round(v, 2))
        t += step
    return dict(seatedOverlapMm3={k: round(v, 4) for k, v in seated.items()}, clearAtMm=clear_at,
                hits={k: dict(firstMm=v[0], lastMm=v[-1], steps=len(v), worstExcessMm3=worst[k]) for k, v in hits.items()},
                collisionSteps=int(sum(len(v) for v in hits.values())), stepMm=step)


def bounds(mesh):
    return (np.array(mesh.bounds[0]), np.array(mesh.bounds[1]))


# ---------------------------------------------------------------- 2 shells step against the pack
appr = steps['shells']['approach']
res['shellsStep'] = {}
for tag, body, bm in (('V1.9', V19, V19m), ('V1.8', V18, V18m)):
    for k, (sm, S) in SH.items():
        a = np.array(appr[k], float); u = a / np.linalg.norm(a)
        r = sweep(S, bounds(sm), u, [('rear_pack', body, bounds(bm))], np.linalg.norm(a))
        r['approach'] = a.tolist()
        res['shellsStep'][f'{tag}:{k}'] = r
        print('shells step', tag, k, r, flush=True)

# ---------------------------------------------------------------- 3 pack-in from the rear with the shells on
imu_mesh = P.imu_mesh(); IMU = P.mesh_to_m(imu_mesh)
SCR = P.union([P.cyl_y(2.0, -0.695, 0.805, x, z) + P.cyl_y(1.0, -4.695, -0.695, x, z) for (x, z) in ((-15.46, 8.04), (-15.46, 28.36))])
res['packInShellsOn'] = {}
for tag, mover, mb in (('V1.9+BNO085', V19 + IMU + SCR, None), ('V1.8', V18, None)):
    bb = np.array(mover.bounding_box()).reshape(2, 3)
    obst = [(k, S, bounds(sm)) for k, (sm, S) in SH.items()]
    r = sweep(mover, (bb[0], bb[1]), np.array([-1.0, 0.0, 0.0]), obst, 30.0, t_max=120.0)
    res['packInShellsOn'][tag] = r
    print('pack-in shells on', tag, r, flush=True)

# ---------------------------------------------------------------- 4 hip-yaw case screws with the shells on
fast = {f['id']: f for f in json.load(open(G / 'content' / 'fasteners.json'))['screws']}
res['caseScrewDriverShellsOn'] = {}
for sid in ('S10-case-072', 'S05-case-076', 'S10-case-069', 'S05-case-074'):
    f = fast[sid]; c = np.array(f['center'], float); a = np.array(f['axis'], float)
    top = c - a * f['headHeightMm']                      # head top (driver tip)
    row = {}
    for dia in (3.0, 5.0):
        z0, z1 = sorted([top[2], top[2] - a[2] * 70.0])
        shaft = P.cyl_z(dia / 2, z0, z1, c[0], c[1])
        row[f'dia{dia:g}'] = {k: dict(overlapMm3=round(float((shaft ^ S).volume()), 3), gapMm=round(float(shaft.min_gap(S, 3.0)), 3))
                              for k, (sm, S) in SH.items()}
    row['headTop'] = np.round(top, 3).tolist(); row['driveDirection'] = a.tolist()
    res['caseScrewDriverShellsOn'][sid] = row
    print('case screw', sid, row, flush=True)

# ---------------------------------------------------------------- 5 BNO085 bench screws
res['imuBenchDriver'] = {}
for (x, z) in ((-15.46, 8.04), (-15.46, 28.36)):
    row = {}
    for dia in (6.0, 5.0, 4.0, 3.0):
        shaft = P.cyl_y(dia / 2, 0.805, 70.0, x, z)
        row[f'dia{dia:g}'] = dict(packOverlapMm3=round(float((shaft ^ V19).volume()), 3), packGapMm=round(float(shaft.min_gap(V19, 3.0)), 3),
                                  boardOverlapMm3=round(float((shaft ^ IMU).volume()), 3), boardGapMm=round(float(shaft.min_gap(IMU, 3.0)), 3))
    res['imuBenchDriver'][f'x{x}_z{z}'] = row
    print('imu bench driver', x, z, row, flush=True)

res['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(res, HERE / 'check_v19_seat.json')
print('DONE', res['elapsed_s'])
