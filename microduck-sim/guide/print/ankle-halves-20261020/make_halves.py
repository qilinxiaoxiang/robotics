"""Two-half ankle (Shawn 2026-10-20): the stock one-piece orange ankle bracket cut in half at mid shaft, each half held
by the foot. Replaces the V1.22 split ankle (base + side on two posts with two M2 x 8 TAP), which looked fragile, needed
careful support removal, and whose posts caught the servo wire; Shawn never fitted those two screws and the ankle worked.

  outer half  the stock bracket for local z < CUT: the plate on the servo horn (four M2 x 4 as before) and half the foot block
  inner half  the stock bracket for local z > CUT: the plate whose pocket runs on the 10.4 mm V1.22 sleeve, and the other
              half of the foot block; its sleeve lip raised to 1.2 mm as in V1.22 (LIP_*). The d15 pocket and the d14 lip bore
              stay round (Shawn 2026-10-20 on the printed V1.24 teardrop: round bore, support in the hole); the print pose
              stands the half on its toe or heel end so the support lands on the side of the bore, never on its weight side

Local frame (the ankle-redesign-20261007 frame): local z is the motor shaft, local y is up, the foot is below. CUT = -16.0
is the axis of the stock toe screw hole (x 17.5, z -16.0), so the toe M2 x 6 TAP sits on the cut and its countersunk head
bears on both halves. Nothing joins the halves except the foot: its socket wraps both foot-block halves and its two end
walls keep them from moving apart; the toe screw holds both down. No new screw, post, tab or slot. The outer envelope is
the stock bracket's (plus the lip), so the V1.22 slip-fit feet and the V1.22 black sleeves are reused unchanged.
Each cut face is set back CUT_GAP from the cut so two slightly oversize printed halves still fit the foot socket.

Checks, both legs, against the audit solids of the current guide world (lower link, XL330, washer, slip-fit foot) and the
V1.22 sleeve; written to halves-check.json:
  seated overlaps; envelope (new material = the lip only); foot seat, drop contact, sideways play and slide path against
  the stock bracket's; foot capture (each half moved 1 mm apart hits a foot wall); inner half off along the shaft with the
  foot off; package lift out of the outer half with the inner half off; inner half held on the sleeve (lift); the toe
  screw countersink shared by both halves; the release wall check on each half.

    /tmp/microduck-cad-venv/bin/python make_halves.py      (about 1 min; run under the bounded runner)

Writes STL/{side}-{outer,inner}-{local,world}.stl (gitignored), guide/print/world/ankle_{outer,inner}_{side}.stl for the
guide and the print gate, and halves-check.json.
"""
import base64, hashlib, json, sys
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[1]; SIM = GUIDE.parent
AR = SIM / 'build-pack-20260913/redesign-20260913/ankle-redesign-20261007'
DATA = SIM / 'build-pack-20260913/redesign-20260913/leg-guide-20261006/full-build-data.json'
WORLD = GUIDE / 'print' / 'world'
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import ia_lib as L        # noqa: E402
import wall_check as W    # noqa: E402

CUT = -16.0          # local z of the cut: the stock toe screw axis
CUT_GAP = 0.1        # each cut face set back this far (0.2 mm between the halves)
# V1.22 lip (ankle-redesign-20261007/generate_candidate.py): the stock sleeve lip is 0.25-0.5 mm thick; raised to z 2.7
# over r 7.05-9.15 wherever the inner half exists; its lower face, the sleeve's axial stop at z 1.5, does not move.
LIP_R_IN, LIP_R_OUT, LIP_Z0, LIP_TOP = 7.05, 9.15, 1.5, 2.7
TOE = (17.5, CUT)    # toe screw axis (x, z) of the left ankle, vertical (local y); the right frame mirrors local x
SIDES = dict(left=dict(sign=1, ankle='ankle', lower='lower', motor='motor6', washer='washer6', foot='foot'),
             right=dict(sign=-1, ankle='right_ankle', lower='right_lower', motor='motor1', washer='washer1', foot='right_foot'))
TOL = 0.01


def frame(sign):
    T = np.eye(4); T[:3, :3] = [[sign, 0, 0], [0, 0, -sign], [0, 1, 0]]; T[:3, 3] = [-31.7771, sign * 33.8, -81.5]; return T


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def man(v, f):
    a = mf.Manifold(mf.Mesh(np.asarray(v, dtype=np.float32), np.asarray(f, dtype=np.uint32))); assert a.status() == mf.Error.NoError; return a


def tm(a):
    m = a.to_mesh(); return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=True)


def stock_local(key, T):
    p = {q['key']: q for q in json.loads(DATA.read_text())['parts']}[key]
    m = trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']), dtype='<f4').reshape(-1, 3),
                        np.frombuffer(base64.b64decode(p['indexB64']), dtype='<u4').reshape(-1, 3), process=True).apply_transform(np.linalg.inv(T))
    return man(m.vertices, m.faces)


def audit_local(key, T):
    v, f = L.load_solid(key); v = trimesh.transform_points(np.asarray(v, float), np.linalg.inv(T)); return L.to_manifold(v, f)


def box_z(z0, z1):
    return mf.Manifold.cube([200, 200, z1 - z0]).translate([-100, -100, z0])


def cyl(r, z0, z1):
    return mf.Manifold.cylinder(z1 - z0, r, r, 96).translate([0, 0, z0])


def single(a, key):
    cs = [c for c in a.decompose() if c.volume() > 1e-5]; assert len(cs) == 1, (key, [c.volume() for c in a.decompose()]); return cs[0]


def vol(a):
    return round(float(a.volume()), 3)


def clear_until(moving, fixed, d, stop, step=0.25):
    """Largest travel along d (mm) before the overlap exceeds its seated value by TOL, up to stop."""
    t = 0.0; base = vol(moving ^ fixed)
    while t < stop:
        if vol(moving.translate((np.asarray(d) * (t + step)).tolist()) ^ fixed) > base + TOL:
            return round(t, 2)
        t += step
    return stop


def first_contact(moving, fixed, d, step=0.01, limit=1.0):
    t = 0.0
    while t < limit:
        t += step
        if vol(moving.translate((np.asarray(d) * t).tolist()) ^ fixed) > TOL:
            return round(t - step, 2)
    return limit


def toe_seat(m, x, z):
    """Up-facing area within 1.9 mm of the toe screw axis: the countersink this half gives the screw head."""
    c = m.triangles_center; n = m.face_normals
    sel = (np.hypot(c[:, 0] - x, c[:, 2] - z) <= 1.9) & (n[:, 1] > 0.3)
    return round(float(m.area_faces[sel].sum()), 2)


def main():
    out = dict(cut=dict(localZ=CUT, gapPerFaceMm=CUT_GAP, toeScrewAxisLocalXZ=list(TOE)), lip=dict(rIn=LIP_R_IN, rOut=LIP_R_OUT, z0=LIP_Z0, top=LIP_TOP),
               sleeve=str(AR / 'STL' / '{side}-sleeve-local.stl'), toleranceMm3=TOL, sides={})
    for side, K in SIDES.items():
        T = frame(K['sign']); old = stock_local(K['ankle'], T)
        outer = single(old ^ box_z(-100, CUT - CUT_GAP), f'{side}-outer')
        inner = old ^ box_z(CUT + CUT_GAP, 100)
        lip = (cyl(LIP_R_OUT, LIP_Z0, LIP_TOP) - cyl(LIP_R_IN, LIP_Z0 - 1, LIP_TOP + 1)) ^ inner.project().extrude(LIP_TOP - LIP_Z0).translate([0, 0, LIP_Z0])
        inner = single((inner + lip).simplify(1e-4), f'{side}-inner')
        halves = dict(outer=outer, inner=inner); r = dict(files={})
        for name, a in halves.items():
            m = tm(a); assert m.is_watertight and m.is_winding_consistent and (m.area_faces > 1e-9).all(), (side, name)
            lp = HERE / 'STL' / f'{side}-{name}-local.stl'; m.export(lp)
            wm = m.copy().apply_transform(T); wp = HERE / 'STL' / f'{side}-{name}-world.stl'; wm.export(wp)
            gp = WORLD / f'ankle_{name}_{side}.stl'; wm.export(gp)
            r['files'][name] = dict(local=str(lp), localSha256=sha(lp), world=str(wp), worldSha256=sha(wp), guide=str(gp), volumeMm3=vol(a))
        sleeve_m = trimesh.load(AR / 'STL' / f'{side}-sleeve-local.stl', force='mesh', process=True); sleeve = man(sleeve_m.vertices, sleeve_m.faces)
        S = {k: audit_local(K[k], T) for k in ('lower', 'motor', 'washer', 'foot')}; S['sleeve'] = sleeve
        pkg = S['lower'] + S['motor'] + S['washer'] + sleeve; foot = S['foot']; both = outer + inner
        r['stockVolumeMm3'] = vol(old)
        r['seated'] = {f'{h}-{k}': vol(H ^ o) for h, H in halves.items() for k, o in S.items()}
        r['seatedNote'] = 'the right outer half keeps the 0.137 mm3, 0.001 mm thick source mating-face slab against the servo that the stock bracket has'
        r['envelope'] = dict(newMaterialOutsideStockMm3=vol(both - old), lipRingMm3=vol(lip - old), stockRemovedMm3=vol(old - both))
        # foot seat against the stock bracket
        seat = {}
        for nm, b in (('halves', both), ('stock', old)):
            seat[nm] = dict(overlap=vol(foot ^ b), dropContact005=vol(foot.translate([0, 0.05, 0]) ^ b),
                            play={k: first_contact(foot, b, d) for k, d in (('+x', [1, 0, 0]), ('-x', [-1, 0, 0]), ('+z', [0, 0, 1]), ('-z', [0, 0, -1]))})
        r['footSeat'] = seat
        r['footPathDownClearMm'] = clear_until(foot, both, [0, -1, 0], 15.0)
        r['footCapture'] = dict(innerApart1mm=vol(inner.translate([0, 0, 1]) ^ foot), outerApart1mm=vol(outer.translate([0, 0, -1]) ^ foot),
                                innerFreeTravelMm=first_contact(inner, foot, [0, 0, 1]), outerFreeTravelMm=first_contact(outer, foot, [0, 0, -1]))
        r['innerOffAlongShaftClearMm'] = clear_until(inner, pkg, [0, 0, 1], 24.0)
        r['innerLiftOnSleeveMm'] = first_contact(inner, pkg, [0, 1, 0])
        r['packageLiftOutOfOuterClearMm'] = clear_until(pkg, outer, [0, 1, 0], 30.0)
        r['packageLiftOutOfOuterAt0Mm3'] = vol(pkg ^ outer)
        r['toeScrewSeatMm2'] = {h: toe_seat(tm(H), K['sign'] * TOE[0], TOE[1]) for h, H in halves.items()}
        r['wall'] = {}
        for h, H in halves.items():
            w = W.check(tm(H), key=f'{side}-{h}'); w.pop('failures')
            r['wall'][h] = dict(passed=w['passed'], minSmoothedMm=w['minSmoothedMm'], regions=w['regions'], smallThinPatches=w['smallThinPatches'])
        out['sides'][side] = r
        print(side, json.dumps({k: v for k, v in r.items() if k not in ('files', 'wall')}), {h: (w['passed'], w['minSmoothedMm'], len(w['regions'])) for h, w in r['wall'].items()}, flush=True)
    s = out['sides']
    ok = all(all(v <= TOL for k, v in r['seated'].items() if not (sd == 'right' and k == 'outer-motor' and v <= 0.14))
             and r['footSeat']['halves']['overlap'] <= TOL and r['footPathDownClearMm'] >= 15 and r['innerOffAlongShaftClearMm'] >= 24
             and r['footCapture']['innerApart1mm'] > 1 and r['footCapture']['outerApart1mm'] > 1 and min(r['toeScrewSeatMm2'].values()) > 0.5
             and all(w['passed'] for w in r['wall'].values()) for sd, r in s.items())
    out['passed'] = bool(ok)
    (HERE / 'halves-check.json').write_text(json.dumps(out, indent=1) + '\n')
    print('PASSED', ok)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
