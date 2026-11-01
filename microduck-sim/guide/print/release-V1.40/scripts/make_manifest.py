"""Write the V1.40 incremental release manifest (Shawn 2026-11-01: tool-free battery swap, "明白了，试试吧 ... 其实都用橙色打"):
one Orange plate with the three parts of battery-quickswap-20261101/: the battery backpack frame and cap of the battery-on-cap
redesign (D-037, qilinxiaoxiang/microduck_rl 8bce48af) with the roof opening and rear-corner cut, plus the new battery hatch.
Frame and cap keep the print poses of the V1.20 rows (frame rim down, cap back face down); the hatch prints back flap down.

Thin regions found by the wall check are accepted only where the printed redesign part (the team repo STL, built and on the
robot) has the same region in the same pose (bbox within 1 mm). Profiles, baseline stock and the delivery contract come from
manifest-V1.39.json; the frame and cap row templates from manifest-V1.20.json.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import copy, hashlib, json, sys
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
V139 = PRINT / 'release-V1.39/manifest-V1.39.json'
V120 = PRINT / 'release-V1.20/manifest-V1.20.json'
QS = PRINT / 'battery-quickswap-20261101'
TEAM = SIM / 'microduck_rl/cmu/hardware/battery-backpack/stl'
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


def printed(path, T):
    m = trimesh.load(path, force='mesh', process=False)
    v, inv = np.unique(m.vertices, axis=0, return_inverse=True)
    m = trimesh.Trimesh(v, inv.reshape(-1)[m.faces], process=False); m.apply_transform(np.array(T, float))
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    return m


def contact(m): return float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
def thin(m, key): return [g for g in wall_check.check(m.copy(), (), key)['regions'] if g['status'] == 'FAIL']


# The only material build_quickswap.py removes from the team parts (robot frame, mm): the roof opening, the cap's rear corner
# and the snap slot. diff_confined() proves the parts differ nowhere else, so a thin region more than NEAR mm from these boxes
# is geometry the printed part already has (the wall check's region outlines shift with the remeshed surface).
CUTS = [((-74.35, -16.0, 34.59), (-61.75, 16.0, 44.0)), ((-76.55, -16.0, 37.0), (-74.34, 16.0, 44.0)), ((-75.6, -6.3, 18.8), (-74.3, 6.3, 21.6))]
NEAR = 3.0


def manifold(p):
    import manifold3d as m3
    t = trimesh.load(p, force='mesh'); return m3.Manifold(m3.Mesh(np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)))


def diff_confined(old, new, tol=0.3):
    """The new part is the old part minus material inside CUTS: nothing added, and no removed volume outside the cut boxes.
    (Measured by volume: the removed pieces keep coplanar wall vertices in their meshes, so vertex bounds overstate them.)"""
    import manifold3d as m3
    a, b = manifold(old), manifold(new)
    assert (b - a).volume() < 0.01, ('material added', new)
    keep = a - b
    for lo, hi in CUTS:
        keep = keep - m3.Manifold.cube(tuple(np.subtract(hi, lo) + 2 * tol)).translate(tuple(np.subtract(lo, tol)))
    assert keep.volume() < 0.01, ('material removed outside the cuts', new, round(keep.volume(), 3))


def cuts_in_print(world, T):
    """CUTS through sourceToPrint and the same drop to the bed as printed()."""
    T = np.array(T, float); m = trimesh.load(world, force='mesh'); m.apply_transform(T); dz = float(m.bounds[0, 2]); out = []
    for lo, hi in CUTS:
        c = np.array([[x, y, z, 1.0] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]) @ T.T
        out.append((c[:, :3].min(0) - [0, 0, dz], c[:, :3].max(0) - [0, 0, dz]))
    return out


def allowances(key, new, old, cuts):
    olds = thin(old, key); allow = []
    for g in thin(new, key):
        lo, hi = np.array(g['bbox'])
        was = [o for o in olds if (lo > np.array(o['bbox'][0]) - 1.0).all() and (hi < np.array(o['bbox'][1]) + 1.0).all()]
        near = any(((lo <= c_hi + NEAR) & (hi >= c_lo - NEAR)).all() for c_lo, c_hi in cuts)
        assert was or not near, ('new thin region beside a cut', key, g['minMm'], g['areaMm2'], g['bbox'])
        allow.append(dict(bbox=[[c - .05 for c in g['bbox'][0]], [c + .05 for c in g['bbox'][1]]], minMm=round(max(g['minMm'] - .005, 0.01), 3),
                          reason=('present in the battery-on-cap redesign part (team repo 8bce48af), which printed and is on the robot'
                                  + ('' if was else f'; more than {NEAR} mm from every cut, where the part is unchanged (diff_confined)'))))
    return allow


def main():
    m = json.loads(V139.read_text()); v120 = {p['key']: p for p in json.loads(V120.read_text())['parts']}
    b = json.loads((QS / 'build/build.json').read_text())
    assert b['closed_overlap_mm3'] and all(v <= 0.01 for v in b['closed_overlap_mm3'].values()), b['closed_overlap_mm3']
    rows, sizes, los = [], {}, {}
    why = ('Shawn 2026-11-01: changing the battery means unscrewing the cap and both bars; he asked for a snap or Dual Lock swap '
           '("平时稳定，但是要拆卸的时候也不麻烦") and approved the CAD revision ("明白了，试试吧", all Orange). ')
    spec = {
        'battery_backpack_frame': (v120['battery_backpack_frame'], 'rim down as the V1.20 frame (robot x -68.15, the cap seam, on the bed)',
                                   'the battery-on-cap redesign frame with the roof opened over the battery (x -68.15..-61.75, |y| <= 16, z 34.59 up). '
                                   'The switch and the DFR1202 move over from the frame on the robot.'),
        'battery_backpack_cap': (v120['battery_backpack_cap'], 'back face down as the V1.20 cap (robot x -75.55 on the bed)',
                                 'the battery-on-cap redesign cap with the roof and the rounded rear-top corner opened over the battery '
                                 '(back wall cut to z 37) and a 12.6 x 2.8 mm slot through the back wall at z 18.8..21.6 for the hatch snap.'),
        'battery_hatch': (v120['battery_backpack_cap'], 'back flap down (robot x -76.75 on the bed); the 1.2 mm flap bends within its layers',
                          'new part: the hatch restores the roof and the rounded corner flush, hooks two front tabs under the frame roof '
                          'edge, snaps a 1.2 mm bump on its back flap into the cap slot (root strain 0.77 % at the 1.3 mm release pull) and '
                          'holds the battery down 0.3 mm above its top.'),
    }
    for key, (tmpl, pose, change) in spec.items():
        row = copy.deepcopy(tmpl)
        world = QS / f'build/{key}-world.stl'; T = b['print'][key]['source_to_print']
        k = printed(world, T); area = contact(k); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
        assert area >= 0.9 * b['print'][key]['bed_contact_mm2'] - 1, area
        old = TEAM / f'{key}-world.stl'
        if old.exists():
            diff_confined(old, world); allow = allowances(key, k, printed(old, T), cuts_in_print(world, T))
        else:
            allow = []
            assert not thin(k, key), (key, thin(k, key))
        row.update(key=key, color='Orange', quantity=1, path=ref(world)['path'], sha256=sha(world), sourceToPrint=T,
                   flatContact={'minimumAreaMm2': int(0.9 * area), 'reason': '90 % of the measured contact in this pose (build_quickswap.py).'},
                   poseOrigin=f'{pose}; x\' = y, y\' = z, z\' = x; {area:.1f} mm2 bed contact, {size[2]:.1f} mm tall',
                   changeReason=why + change, thinWallAllowances=allow,
                   poseCheck=dict(printStl=ref(QS / f'build/{key}-print.stl'), bedContactMm2=round(area, 2), printSizeMm=size),
                   incrementalEvidence=ref(QS / 'build/build.json'),
                   evidenceAlso=[ref(QS / 'build_quickswap.py'), ref(QS / 'DESIGN-CONTRACT.json')] + ([ref(old)] if old.exists() else []),
                   supportBlockers=[])
        row['decision'] = 'addition'; row['replacesStockIds'] = []
        row['supersedes'] = f'{key} of the battery-on-cap redesign (printed, on the robot)' if old.exists() else ''
        if not row['supersedes']: row.pop('supersedes')
        rows.append(row); sizes[key] = size; los[key] = k.bounds[0]
    # frame, cap and hatch side by side along print x, centred on the 256 mm bed
    gap = 10.0; total = sum(sizes[r['key']][0] for r in rows) + gap * (len(rows) - 1); x = 128.0 - total / 2; pl = []
    for r in rows:
        s, lo = sizes[r['key']], los[r['key']]
        pl.append(dict(key=r['key'], copy=1, translation=[round(x - float(lo[0]), 4), round(128.0 - s[1] / 2 - float(lo[1]), 4), 0.0]))
        x += s[0] + gap
    m.update(version='V1.40', parts=rows, placements={'Orange': pl}, processOverrides={},
             processOverrideReason='No process overrides: the Orange profile; the frame carries tree support under its front plate as V1.20.',
             retiredParts=[dict(part='battery_backpack_frame (battery-on-cap redesign)', printed='team print 2026-10-31 (Orange)',
                                reason='replaced by the V1.40 frame with the roof opening; move the switch and the DFR1202 over first'),
                           dict(part='battery_backpack_cap (battery-on-cap redesign)', printed='team print 2026-10-31 (Orange)',
                                reason='replaced by the V1.40 cap with the roof and corner opening and the snap slot')],
             prototypeScope='V1.40: tool-free battery swap, one Orange plate: backpack frame, backpack cap, battery hatch.',
             knownFitBoundary=('Battery size from the product page (12 x 31 x 57 mm), not measured. The hatch snap (1.2 mm bump, 0.77 % '
                               'strain) and the front tab lips (0.8 mm under the roof edge) are untested on a print. Bars, switch, DFR1202 '
                               'and battery are reused unchanged.'))
    m.pop('deferred', None)
    m['deliveryContract'] = dict(m['deliveryContract'], colors=['Orange'], filesPerColor=2, fileCount=2, baseline='printed releases through V1.39',
                                 status='INCREMENTAL_REPRINT', supersedes=['battery_backpack_frame and battery_backpack_cap of the battery-on-cap redesign'])
    (REL / 'manifest-V1.40.json').write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(sizes=sizes, placements=pl, allowances={r['key']: len(r['thinWallAllowances']) for r in rows})))


if __name__ == '__main__':
    main()
