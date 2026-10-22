"""One-piece lower-leg link: the stock link (community-30 left, community-32 right) with the V1.22 ankle sleeve grown onto
its 10 mm boss, both legs.

In the ankle local frame of make_halves.py (shaft = local z) the V1.22 sleeve is OD 14.6, z -1.4..1.4, on the boss
(OD 10, top z 1.3) with 0.2 mm radial play, 0.3 mm above the link's boss flange. The new link adds
  ring   r SCREW_R..SLEEVE_R over the sleeve's z span (the sleeve envelope itself, bore play filled),
  neck   r SCREW_R..NECK_R from the link plate up to the sleeve (fills the 0.3-0.8 mm gap under the sleeve),
so the rotating face is the sleeve's 14.6 mm outer face in the inner half's 15 mm pocket, as now; nothing grows outside the
old link + sleeve envelope. Writes STL/{side}-link-print.stl (the 10/1 print frame of the stock link) and
STL/{side}-link-local.stl, and link-check.json: seated overlaps and the make_halves assembly paths for the new package
(link + servo + washer) next to the same numbers for the stock package (link + sleeve + servo + washer).

    /tmp/microduck-cad-venv/bin/python make_link.py
"""
import json, sys
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; GUIDE = HERE.parents[1]; SIM = GUIDE.parent
sys.path.insert(0, str(GUIDE / 'print' / 'ankle-halves-20261020'))
import make_halves as H  # noqa: E402

STOCK = dict(left='community-30', right='community-32')
SLEEVE_R, SLEEVE_Z = 7.3, (-1.4, 1.4)
NECK_R, NECK_Z0 = 7.3, -2.2      # full sleeve diameter down into the link plate top (local z -2.1): no 0.5 mm slot under the sleeve rim
SCREW_R = 2.75                   # the stock 5.5 mm through bore of the boss


def register(side):
    """Print-frame STL -> world, by ICP of the stock print STL onto the guide's audit solid (fit < 0.01 mm)."""
    key = H.SIDES[side]['lower']; v, f = H.L.load_solid(key); w = trimesh.Trimesh(v, f, process=True)
    p = trimesh.load(SIM / f'build-pack-20260913/assembly/print-parts/{STOCK[side]}.stl', process=True)
    np.random.seed(0)                                              # mesh_other samples points at random
    M, _ = trimesh.registration.mesh_other(p, w, samples=3000, scale=False, icp_first=20, icp_final=100)
    d = trimesh.proximity.closest_point(w, p.copy().apply_transform(M).vertices[::5])[1]
    assert d.max() < 0.01, d.max()
    return p, M, float(d.max())


def ring(r0, r1, z0, z1):
    return H.cyl(r1, z0, z1) - H.cyl(r0, z0 - 1, z1 + 1)


def main():
    (HERE / 'STL').mkdir(exist_ok=True); out = dict(sleeve=dict(r=SLEEVE_R, z=SLEEVE_Z), neck=dict(r=NECK_R, z0=NECK_Z0), screwR=SCREW_R, sides={})
    for side, K in H.SIDES.items():
        T = H.frame(K['sign']); p, M, fit = register(side)
        P2L = np.linalg.inv(T) @ M                                     # print frame -> ankle local
        lk = p.copy().apply_transform(P2L); link = H.man(lk.vertices, lk.faces)
        add = ring(SCREW_R, SLEEVE_R, *SLEEVE_Z) + ring(SCREW_R, NECK_R, NECK_Z0, SLEEVE_Z[0])
        new = H.single((link + add).simplify(1e-4), f'{side}-link')
        sl = trimesh.load(H.AR / 'STL' / f'{side}-sleeve-local.stl', force='mesh', process=True); sleeve = H.man(sl.vertices, sl.faces)
        S = {k: H.audit_local(K[k], T) for k in ('motor', 'washer', 'foot')}
        halves = {h: (lambda m: H.man(m.vertices, m.faces))(trimesh.load(H.HERE / 'STL' / f'{side}-{h}-local.stl', process=True)) for h in ('outer', 'inner')}
        grown = new - (link + sleeve)                                  # material outside the old link + sleeve envelope
        r = dict(icpFitMaxMm=round(fit, 4), volumeMm3=dict(stockLink=H.vol(link), sleeve=H.vol(sleeve), newLink=H.vol(new)),
                 outsideOldEnvelopeMm3=H.vol(grown),
                 seated={n: H.vol(new ^ o) for n, o in dict(S, **halves).items()},
                 seatedStock={n: H.vol((link + sleeve) ^ o) for n, o in dict(S, **halves).items()})
        for name, pkg in (('new', new + S['motor'] + S['washer']), ('stock', link + sleeve + S['motor'] + S['washer'])):
            r[name + 'Paths'] = dict(innerLiftOnSleeveMm=H.first_contact(halves['inner'], pkg, [0, 1, 0]),
                                     innerOffAlongShaftClearMm=H.clear_until(halves['inner'], pkg, [0, 0, 1], 20),
                                     packageLiftOutOfOuterClearMm=H.clear_until(pkg, halves['outer'], [0, 1, 0], 30))
        lp = HERE / 'STL' / f'{side}-link-local.stl'; H.tm(new).export(lp)
        pm = H.tm(new).apply_transform(np.linalg.inv(P2L)); pp = HERE / 'STL' / f'{side}-link-print.stl'; pm.export(pp)
        r['printBoundsMm'] = pm.bounds.round(3).tolist(); r['files'] = dict(local=str(lp), localSha256=H.sha(lp), print=str(pp), printSha256=H.sha(pp))
        r['printToLocal'] = P2L.round(6).tolist()
        out['sides'][side] = r
    (HERE / 'link-check.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
