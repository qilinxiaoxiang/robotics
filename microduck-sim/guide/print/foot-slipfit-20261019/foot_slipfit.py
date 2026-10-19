"""Slip-fit MicroDuck feet: the printed community feet with the ankle-bracket socket opened so the foot slides on by hand.

Problem (Shawn 2026-10-19): the orange ankle bracket and the yellow foot are a press fit so tight that they cannot be
taken apart, and every fitting loads the ankle servo. The community foot (community-44 left, community-46 right) holds
the bracket's lower block in a socket with zero lateral clearance in CAD, plus two snap tongues with about 0.3 mm
hooks at the heel and toe ends; the bracket also overlaps the foot by about 0.1 mm over the contact faces. Printed
parts add their own oversize, so the joint ends far tighter than intended. One M2 x 6 TAP through the bracket's toe
flange into the foot boss is the designed retainer.

Fix, done on the foot only (the bracket is screwed to the servo horn and stays):
  seat     the bracket's pose in the real foot is fitted (point-to-plane ICP of the bracket's lower faces onto the foot
           socket). The printed foot is not the guide's source foot: its socket is rolled about 4.8 deg about the
           front-back axis, and that roll is kept.
  sweep    the region the bracket passes through when it moves straight down its own axis into that pose, as a height
           field in the bracket frame: everything above the bracket's lowest surface (so the hooks go).
  clear    that region grown sideways by CLEAR mm (a disk minimum filter on the height field); seats facing up keep
           zero vertical clearance, so the bracket rests exactly where it rests now.
  foot     the foot minus the region. Below Z_KEEP (the sole and the hot-glue cast zone) nothing changes, so the V1.21
           molds still fit.
The M2 x 6 at the toe then holds the foot: drop the foot on, drive the screw, done; take the screw out to remove it.

Outputs (STL, gitignored): foot-left-slipfit.stl / foot-right-slipfit.stl in the community print frame (flat bottom at
z = 0, same frame as community-44/46), guide/print/world/foot_left.stl / foot_right.stl in the robot frame for the
guide and the print gate; slipfit-check.json with the measured checks.

    /tmp/microduck-cad-venv/bin/python foot_slipfit.py
"""
import json
import sys
from pathlib import Path

import manifold3d as m3
import numpy as np
import trimesh
from scipy import ndimage
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[1]
SIM = GUIDE.parent
PARTS = SIM / 'build-pack-20260913/assembly/print-parts'
WORLD = GUIDE / 'print/world'
sys.path.insert(0, str(GUIDE / 'content/interference-audit'))
sys.dont_write_bytecode = True
import ia_lib  # noqa: E402

SIDES = {'left': dict(foot='community-44.stl', bracket='community-66.stl', guide_foot='foot', guide_bracket='ankle', world='foot_left.stl'),
         'right': dict(foot='community-46.stl', bracket='community-64.stl', guide_foot='right_foot', guide_bracket='right_ankle', world='foot_right.stl')}
CLEAR = 0.20      # mm lateral clearance socket -> bracket (CAD), so the printed pair slides by hand
STEP = 0.05       # mm height-field grid in the bracket frame
Z_KEEP = 4.0      # mm: the foot below this height (sole, rounded edge, hot-glue cast zone up to 3.0) must not change
SCREW = (-14.278307, 49.797471, -89.619001)   # robot frame, left; guide full-build fastener left-foot-retainer (axis +z)
UP = np.array([0.0, 1.0, 0.0])   # bracket print frame: +y is the robot's up (guide sourceTransformWorld)
R_BRACKET = np.array([[1.0, 0, 0], [0, 0, -1.0], [0, 1.0, 0]])   # bracket print frame -> robot frame (guide source transform)


def load(path):
    return trimesh.load(path, force='mesh', process=True)


def man(t):
    return m3.Manifold(m3.Mesh(np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)))


def tri(mf):
    mm = mf.to_mesh()
    return trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts), process=False)


def apply(T, t):
    t = t.copy(); t.apply_transform(T); return t


def icp_translation(src, dst, R, iters=30):
    """Translation that fits src (rotated by R) onto dst, nearest-point ICP on surface samples."""
    ps = trimesh.sample.sample_surface_even(src, 20000, seed=1)[0] @ R.T
    pd = trimesh.sample.sample_surface_even(dst, 20000, seed=1)[0]
    tree = cKDTree(pd); t = pd.mean(0) - ps.mean(0)
    for _ in range(iters):
        _, i = tree.query(ps + t); t += (pd[i] - (ps + t)).mean(0)
    d, _ = tree.query(ps + t)
    return t, float(np.percentile(d, 95))


def seat(foot, bracket_in_foot):
    """6-DOF point-to-plane ICP of the bracket's lower part onto the foot surface; returns the 4x4 correction."""
    fp, ff = trimesh.sample.sample_surface_even(foot, 400000, seed=3); fn = foot.face_normals[ff]; tree = cKDTree(fp)
    pts = trimesh.sample.sample_surface_even(bracket_in_foot, 80000, seed=2)[0]
    pts = pts[pts[:, 2] < foot.bounds[1, 2] - 1.0]
    c = pts.mean(0); x = np.zeros(6)
    for _ in range(40):
        R = Rot.from_rotvec(x[:3]).as_matrix(); q = (pts - c) @ R.T + c + x[3:]
        d, i = tree.query(q); near = d < 1.0
        n = fn[i[near]]; r = ((q[near] - fp[i[near]]) * n).sum(1)
        J = np.hstack([np.cross(q[near] - c, n), n]); dx = np.linalg.lstsq(J, -r, rcond=None)[0]
        x[:3] = (Rot.from_rotvec(dx[:3]) * Rot.from_rotvec(x[:3])).as_rotvec(); x[3:] += dx[3:]
    R = Rot.from_rotvec(x[:3]).as_matrix(); T = np.eye(4); T[:3, :3] = R; T[:3, 3] = c - R @ c + x[3:]
    q = (pts - c) @ R.T + c + x[3:]; d, i = tree.query(q); near = d < 1.0
    rms = float(np.sqrt((((q[near] - fp[i[near]]) * fn[i[near]]).sum(1) ** 2).mean()))
    return T, dict(rollPitchYawDeg=np.degrees(Rot.from_rotvec(x[:3]).as_euler('xyz')).round(3).tolist(),
                   translationMm=x[3:].round(4).tolist(), fitRmsMm=round(rms, 4), fitPoints=int(near.sum()))


def lower_envelope(bracket):
    """Lowest y of the bracket over an (x, z) grid in its print frame (inf where the bracket is absent)."""
    lo, hi = bracket.bounds
    xs = np.arange(lo[0] - 1.0, hi[0] + 1.0 + 1e-9, STEP); zs = np.arange(lo[2] - 1.0, hi[2] + 1.0 + 1e-9, STEP)
    low = np.full((len(xs), len(zs)), np.inf)
    for t in bracket.triangles:
        a, b, c = t[:, [0, 2]]; ya, yb, yc = t[:, 1]
        ix = np.where((xs >= t[:, 0].min() - 1e-9) & (xs <= t[:, 0].max() + 1e-9))[0]
        iz = np.where((zs >= t[:, 2].min() - 1e-9) & (zs <= t[:, 2].max() + 1e-9))[0]
        if not len(ix) or not len(iz):
            continue
        v0 = b - a; v1 = c - a; det = v0[0] * v1[1] - v0[1] * v1[0]
        if abs(det) < 1e-12:   # face parallel to the axis: its edges are covered by the neighbouring faces
            continue
        X, Z = np.meshgrid(xs[ix], zs[iz], indexing='ij'); px = X - a[0]; pz = Z - a[1]
        u = (px * v1[1] - pz * v1[0]) / det; w = (v0[0] * pz - v0[1] * px) / det
        ins = (u >= -1e-6) & (w >= -1e-6) & (u + w <= 1 + 1e-6)
        y = ya + u * (yb - ya) + w * (yc - ya)
        sub = low[np.ix_(ix, iz)]; sub[ins] = np.minimum(sub[ins], y[ins]); low[np.ix_(ix, iz)] = sub
    return xs, zs, low


def cutter_mesh(xs, zs, bottom, ytop):
    """Closed solid between the height field bottom(x, z) and the plane y = ytop, in the bracket frame."""
    nx, nz = bottom.shape
    X, Z = np.meshgrid(xs, zs, indexing='ij')
    vb = np.stack([X, bottom, Z], -1).reshape(-1, 3); vt = np.stack([X, np.full_like(X, ytop), Z], -1).reshape(-1, 3)
    V = np.vstack([vb, vt]); off = nx * nz
    idx = np.arange(nx * nz).reshape(nx, nz)
    a = idx[:-1, :-1].ravel(); b = idx[1:, :-1].ravel(); c = idx[1:, 1:].ravel(); d = idx[:-1, 1:].ravel()
    F = [np.stack([a, b, d], 1), np.stack([b, c, d], 1),                       # bottom, normal -y
         np.stack([a, d, b], 1) + off, np.stack([b, d, c], 1) + off]           # top, normal +y
    per = list(idx[:, 0]) + list(idx[-1, 1:]) + list(idx[-2::-1, -1]) + list(idx[0, -2:0:-1])
    per = np.array(per); p1 = np.roll(per, -1)
    F += [np.stack([per, p1 + off, p1], 1), np.stack([per, per + off, p1 + off], 1)]
    m = trimesh.Trimesh(V, np.vstack(F), process=True)
    if m.volume < 0:
        m.invert()
    return m


def build(side):
    s = SIDES[side]
    foot = load(PARTS / s['foot']); bracket = load(PARTS / s['bracket'])
    g = ia_lib.load_guide(); P = {p['key']: p for p in (g['parts'] if isinstance(g['parts'], list) else g['parts'].values())}
    gb = trimesh.Trimesh(*ia_lib.decode_guide_part(P[s['guide_bracket']]), process=True)
    gf = trimesh.Trimesh(*ia_lib.decode_guide_part(P[s['guide_foot']]), process=True)
    tb, eb = icp_translation(bracket, gb, R_BRACKET); tf, ef = icp_translation(foot, gf, np.eye(3))
    assert eb < 0.05, (side, 'bracket STL does not match the guide bracket', eb)
    W_b = np.eye(4); W_b[:3, :3] = R_BRACKET; W_b[:3, 3] = tb            # bracket print -> robot
    F0 = np.eye(4); F0[:3, 3] = -tf                                      # robot -> foot print (first guess)
    T_fb0 = F0 @ W_b
    C, fit = seat(foot, apply(T_fb0, bracket))
    T_fb = C @ T_fb0                                                     # bracket print -> foot print, seated
    W_f = W_b @ np.linalg.inv(T_fb)                                      # foot print -> robot

    xs, zs, low = lower_envelope(bracket)
    r = int(round(CLEAR / STEP)); yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    lowc = ndimage.minimum_filter(low, footprint=(xx ** 2 + yy ** 2) <= r * r, mode='constant', cval=np.inf)
    ytop = bracket.bounds[1, 1] + 2.0
    bottom = np.where(np.isfinite(lowc), lowc, ytop - 1.0)
    cut = apply(T_fb, cutter_mesh(xs, zs, bottom, ytop))
    mf, mc = man(foot), man(cut).simplify(0.005)   # merge the cutter's height-field facets (within 5 um); the foot stays exact
    assert mc.status() == m3.Error.NoError, (side, mc.status())
    new = mf - mc
    newt = tri(new)

    # checks ---------------------------------------------------------------------------------------------------------
    seated = man(apply(T_fb, bracket))
    inter_before = (mf ^ seated).volume(); inter_after = (new ^ seated).volume()
    axis = T_fb[:3, :3] @ UP
    path = []
    for d in np.arange(0.0, 15.01, 0.5):
        T = np.eye(4); T[:3, 3] = axis * d
        path.append(round((new ^ man(apply(T @ T_fb, bracket))).volume(), 4))
    drop = []
    for d in (0.05, 0.1, 0.2):
        T = np.eye(4); T[:3, 3] = -axis * d
        drop.append(round((new ^ man(apply(T @ T_fb, bracket))).volume(), 3))
    lateral = {}
    # sideways in the bracket frame (x = toe/heel, z = across the foot); +y is up, where the foot lifts off freely
    for name, v in (('toe', [1, 0, 0]), ('heel', [-1, 0, 0]), ('across_+z', [0, 0, 1]), ('across_-z', [0, 0, -1]), ('up', [0, 1, 0])):
        hit = None
        for d in np.arange(0.02, 0.6, 0.02):
            T = np.eye(4); T[:3, 3] = T_fb[:3, :3] @ np.array(v, float) * d
            if (new ^ man(apply(T @ T_fb, bracket))).volume() > 1e-3:
                hit = round(float(d), 2); break
        lateral[name] = hit
    keep = m3.Manifold.cube([200, 200, Z_KEEP]).translate([-100, -100, 0])
    below_change = (mf ^ keep).volume() - (new ^ keep).volume()
    # toe retainer M2 x 6 TAP (guide fastener left-foot-retainer / right-foot-retainer): the foot boss around its axis must stay
    sc = np.linalg.inv(W_f) @ np.array([SCREW[0], SCREW[1] * (1 if side == 'left' else -1), SCREW[2], 1.0])
    boss = m3.Manifold.cylinder(sc[2] - 1.0, 2.6, 2.6, 48).translate([sc[0], sc[1], 1.0])
    boss_change = (mf ^ boss).volume() - (new ^ boss).volume()
    out_print = HERE / f'foot-{side}-slipfit.stl'; newt.export(out_print)
    WORLD.mkdir(exist_ok=True); apply(W_f, newt).export(WORLD / s['world'])
    return dict(
        side=side, foot=s['foot'], bracket=s['bracket'], clearanceMm=CLEAR,
        bracketToGuideP95Mm=round(eb, 4), footToGuideFootP95Mm=round(ef, 3),
        seat=fit, bracketPrintToFootPrint=np.round(T_fb, 6).tolist(), footPrintToRobot=np.round(W_f, 6).tolist(),
        footVolumeMm3=dict(before=round(mf.volume(), 2), after=round(new.volume(), 2), removed=round(mf.volume() - new.volume(), 2)),
        seatedInterferenceMm3=dict(before=round(inter_before, 3), after=round(inter_after, 4)),
        insertionPathInterferenceMm3=dict(stepMm=0.5, upToMm=15.0, max=max(path)),
        restsAtSeat=dict(dropMm=[0.05, 0.1, 0.2], interferenceMm3=drop),
        lateralPlayMm=lateral,
        changeBelowZMm=dict(z=Z_KEEP, volumeMm3=round(below_change, 4)),
        cutMinZMm=round(float(cut.bounds[0, 2]), 3),
        toeScrewBoss=dict(axisInFootMm=np.round(sc[:3], 2).tolist(), radiusMm=2.6, volumeChangeMm3=round(boss_change, 4)),
        outputs=[str(out_print), str(WORLD / s['world'])])


if __name__ == '__main__':
    res = [build(s) for s in SIDES]
    (HERE / 'slipfit-check.json').write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(res, indent=1))
