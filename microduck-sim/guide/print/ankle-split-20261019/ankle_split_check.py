"""Split ankle (2026-10-07 design, released 2026-10-19): fit of the six parts against the current guide world.

The 10/07 digital prototype (build-pack-20260913/redesign-20260913/ankle-redesign-20261007/, DESIGN-NOTES.md) splits each
orange ankle into a base (on the motor horn, carrying the foot block) and a removable side ("cheek", two M2 x 8 TAP from
above, two register tongues) and replaces the black sleeve (OD 14.6, bore 10.4, 2.8 wide). Its world STLs are in the guide
world frame. This script checks them against the audit solids of the current robot (interference-audit cache: lower-leg
link, XL330, washer, the 2026-10-19 slip-fit foot) and writes:

  ankle-split-check.json             the evidence bound by the V1.22 manifest
  guide/print/world/ankle_*.stl      the guide/gate copies of the six parts (vertices merged)

Checks, per leg: seated overlaps; the base plus side stay inside the stock bracket's envelope where the foot sits; the
foot seats on the new base as it did on the stock bracket (zero overlap, contact on a 0.05 mm drop, sideways play); the
foot slides on and off past the side; with the side off, the lower-link/motor/washer/sleeve package lifts straight out of
the base; with the foot off, the side slides outward off the sleeve; with the foot on, the side is captured; the two side
screws pass the side's clearance holes and engage only the base pilots; the sleeve runs free on the link boss.

    /tmp/microduck-cad-venv/bin/python ankle_split_check.py      (about 10 s; run under the bounded runner)
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[1]
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
import ia_lib as L                      # noqa: E402
import manifold3d as m3                 # noqa: E402

AR = GUIDE.parents[0] / 'build-pack-20260913/redesign-20260913/ankle-redesign-20261007/STL'
WORLD = GUIDE / 'print' / 'world'
SIDES = dict(left=dict(ankle='ankle', lower='lower', ring='smallring', motor='motor6', washer='washer6', foot='foot'),
             right=dict(ankle='right_ankle', lower='right_lower', ring='right_smallring', motor='motor1', washer='washer1', foot='right_foot'))
GUIDE_NAMES = dict(base='ankle_base_{side}.stl', cheek='ankle_cheek_{side}.stl', sleeve='ankle_sleeve_{side}.stl')
TOL = 0.01          # mm3; the audit's zero
UP = np.array([0, 0, 1.0])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def world_mesh(name):
    m = trimesh.load(AR / f'{name}-world.stl', force='mesh', process=True)
    m.merge_vertices()
    assert m.is_watertight and m.is_winding_consistent, name
    man = L.to_manifold(np.asarray(m.vertices), np.asarray(m.faces))
    assert L.manifold_ok(man), name
    return man, m


def vol(man):
    return round(float(man.volume()), 4)


def first_contact(moving, fixed, d, step=0.02, limit=1.0):
    t = 0.0
    while t < limit:
        t += step
        if (moving.translate((np.asarray(d) * t).tolist()) ^ fixed).volume() > TOL:
            return round(t - step, 2)
    return limit


def path(moving, fixed, d, stop, step):
    prof = []
    for t in np.arange(0, stop + 1e-9, step):
        prof.append([round(float(t), 2), vol(moving.translate((np.asarray(d) * t).tolist()) ^ fixed)])
    return prof


def ring_dims(v, axis):
    """bore, OD and width of a ring whose axis is a world axis index."""
    c = v.mean(0)
    rad = np.linalg.norm(np.delete(v - c, axis, axis=1), axis=1)
    return dict(boreMm=round(float(2 * rad.min()), 2), odMm=round(float(2 * rad.max()), 2),
                widthMm=round(float(v[:, axis].max() - v[:, axis].min()), 2))


def main():
    out = dict(sourceDir=str(AR), designNotes=str(AR.parent / 'DESIGN-NOTES.md'), toleranceMm3=TOL, sides={})
    for side, K in SIDES.items():
        S = {k: L.to_manifold(*L.load_solid(key)) for k, key in K.items()}
        V = {k: L.load_solid(key)[0] for k, key in K.items()}
        new = {}; meshes = {}
        for part in ('base', 'cheek', 'sleeve'):
            new[part], meshes[part] = world_mesh(f'{side}-{part}')
        screws = {f'screw{i}': world_mesh(f'{side}-cheek-screw{i}')[0] for i in (1, 2)}
        r = dict(files={})
        for part, m in meshes.items():
            dst = WORLD / GUIDE_NAMES[part].format(side=side)
            m.export(dst)
            r['files'][part] = dict(world=str(AR / f'{side}-{part}-world.stl'), worldSha256=sha(AR / f'{side}-{part}-world.stl'),
                                    local=str(AR / f'{side}-{part}-local.stl'), localSha256=sha(AR / f'{side}-{part}-local.stl'),
                                    guide=str(dst), volumeMm3=vol(new[part]))
        r['stockVolumesMm3'] = dict(ankle=vol(S['ankle']), sleeve=vol(S['ring']))
        bv = np.asarray(meshes['base'].vertices); cv = np.asarray(meshes['cheek'].vertices)
        r['boundsWorld'] = dict(stockAnkle=[V['ankle'].min(0).round(2).tolist(), V['ankle'].max(0).round(2).tolist()],
                                baseAndCheek=[np.vstack([bv, cv]).min(0).round(2).tolist(), np.vstack([bv, cv]).max(0).round(2).tolist()])
        # 1. seated overlaps
        robot = dict(lower=S['lower'], motor=S['motor'], washer=S['washer'], foot=S['foot'])
        pairs = {}
        allnew = dict(new, **screws)
        names = list(allnew)
        for i, a in enumerate(names):
            for b, B in robot.items():
                pairs[f'{a}-{b}'] = vol(allnew[a] ^ B)
            for b in names[i + 1:]:
                pairs[f'{a}-{b}'] = vol(allnew[a] ^ allnew[b])
        r['seatedPairsMm3'] = pairs
        r['sleeveOnLinkBoss'] = dict(newSleeve=pairs['sleeve-lower'], stockSleeve=vol(S['ring'] ^ S['lower']))
        # 2. envelope where the foot sits: new material inside the stock bracket's envelope up to 3 mm above the foot top
        fb = V['foot'].min(0), V['foot'].max(0)
        lo = np.minimum(V['ankle'].min(0), np.vstack([bv, cv]).min(0)) - 1; hi = np.maximum(V['ankle'].max(0), np.vstack([bv, cv]).max(0)) + 1
        hi[2] = fb[1][2] + 3
        box = m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())
        zs = S['ankle'] ^ box; zn = (new['base'] + new['cheek']) ^ box
        r['footZone'] = dict(topZ=round(float(hi[2]), 2), newOutsideStockMm3=vol(zn - zs), stockNotInNewMm3=vol(zs - zn), stockMm3=vol(zs))
        # 3. foot seat on base + cheek
        bc = new['base'] + new['cheek']
        d = (-UP * 0.05).tolist()
        r['footSeat'] = dict(seatedMm3=vol(bc ^ S['foot']), drop005ContactMm3=vol(bc.translate(d) ^ S['foot']),
                             stockDrop005ContactMm3=vol(S['ankle'].translate(d) ^ S['foot']),
                             playMm={n: first_contact(bc, S['foot'], dd) for n, dd in (('toe+x', [1, 0, 0]), ('heel-x', [-1, 0, 0]), ('+y', [0, 1, 0]), ('-y', [0, -1, 0]))},
                             stockPlayMm={n: first_contact(S['ankle'], S['foot'], dd) for n, dd in (('toe+x', [1, 0, 0]), ('heel-x', [-1, 0, 0]), ('+y', [0, 1, 0]), ('-y', [0, -1, 0]))})
        # 4. foot slides on/off past the side (straight down 15 mm from seated)
        fixed = bc + new['sleeve'] + screws['screw1'] + screws['screw2']
        p = path(S['foot'], fixed, -UP, 15, 0.5)
        r['footPath'] = dict(maxMm3=max(x[1] for x in p), profile=p)
        # 5. side off: the package lifts straight out of the base
        pkg = S['lower'] + S['motor'] + S['washer'] + new['sleeve']
        p = path(pkg, new['base'], UP, 30, 1.0)
        r['packageLiftSideOff'] = dict(maxMm3=max(x[1] for x in p), seatedMm3=p[0][1], profile=p,
                                       note='the right leg keeps the source mating-face slab of the stock parts (0.137 mm3, 0.001 mm thick: assembly-path-investigation.md)')
        # 6. side closes along the shaft, foot off; with the foot on it is captured
        outward = np.array([0, -1.0 if cv.mean(0)[1] < bv.mean(0)[1] else 1.0, 0])
        p = path(new['cheek'], new['base'] + pkg, outward, 12, 0.5)
        pf = path(new['cheek'], S['foot'], outward, 12, 0.5)
        r['sidePath'] = dict(outwardWorld=outward.tolist(), maxMm3FootOff=max(x[1] for x in p), profileFootOff=p,
                             maxMm3AgainstFoot=max(x[1] for x in pf), footCapturesSide=max(x[1] for x in pf) > TOL)
        # 7. side screws: lifted out along +z they leave the base pilots and never touch the side's clearance holes
        sp = {}
        for n, sc in screws.items():
            pb = path(sc, new['base'], UP, 10, 0.5); pc = path(sc, new['cheek'], UP, 10, 0.5)
            sp[n] = dict(engagedInBaseMm3=pb[0][1], maxInSideMm3=max(x[1] for x in pc), clearOfBaseAtMm=next((x[0] for x in pb if x[1] <= TOL), None))
        r['sideScrews'] = sp
        # 8. sleeve dimensions (axis = world y)
        r['sleeveDims'] = dict(new=ring_dims(np.asarray(meshes['sleeve'].vertices), 1), stock=ring_dims(V['ring'], 1))
        out['sides'][side] = r
        print(side, json.dumps({k: v for k, v in r.items() if k not in ('files',)})[:1500])
    (HERE / 'ankle-split-check.json').write_text(json.dumps(out, indent=1))
    print('wrote', HERE / 'ankle-split-check.json')


if __name__ == '__main__':
    main()
