"""Write the V1.41 incremental release manifest: the battery hatch latch redo after the V1.40 bench test. One Orange plate with
two parts of battery-quickswap-20261101/build-v2/: the new hatch (solid ears in two roof pockets against pull-back, V1.40 flap against lift, solid hold-down block, one plug-size lead window open to the rear)
and the cap with two ear pockets in the roof. The V1.40 frame stays on the robot and is not on this plate.
Cap and hatch keep the V1.40 print poses (cap back face down, hatch back down) unless build-v2/build.json gives a new transform.

Thin regions found by the wall check on the cap are accepted only where the printed V1.40 cap (battery-quickswap-20261101/build/,
the bytes of the V1.40 release) has the same region in the same pose (bbox within 1 mm), or, when build-v2/build.json lists the
cap cuts (`cap_cuts_mm`), more than NEAR mm from every cut with the change confined to those cuts. The hatch is new: no thin region.
Profiles, baseline stock, the delivery contract and the row templates come from manifest-V1.40.json.

The release slices the guide-world copies (guide/print/world/<key>.stl, the bytes the guide draws and the print gate checks).
GUIDE_WORLD is the V1.41 guide-world.json when it exists, else the V1.40 one; either way its `files` entries must name the
build-v2 bytes as their source, so the CAD update must regenerate the guide world before this runs.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import copy, hashlib, json, sys
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
V140 = PRINT / 'release-V1.40/manifest-V1.40.json'
QS = PRINT / 'battery-quickswap-20261101'
BUILD = QS / 'build-v2'                      # V1.41 STL source
OLD = QS / 'build'                           # V1.40 build (the printed cap and hatch), unshifted robot frame
GUIDE_WORLD = next(p for p in (PRINT / 'back-plate/battery-backpack-v141/guide-world.json',
                               PRINT / 'back-plate/battery-backpack-v140/guide-world.json') if p.exists())
KEYS = ('battery_backpack_cap', 'battery_hatch')
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


NEAR = 3.0


def manifold(p):
    import manifold3d as m3
    t = trimesh.load(p, force='mesh'); return m3.Manifold(m3.Mesh(np.asarray(t.vertices, np.float32), np.asarray(t.faces, np.uint32)))


def diff_confined(old, new, cuts, tol=0.3):
    """The new part is the old part minus material inside `cuts` (robot frame boxes): nothing added, nothing removed elsewhere."""
    import manifold3d as m3
    a, b = manifold(old), manifold(new)
    assert (b - a).volume() < 0.01, ('material added', new)
    keep = a - b
    for lo, hi in cuts:
        keep = keep - m3.Manifold.cube(tuple(np.subtract(hi, lo) + 2 * tol)).translate(tuple(np.subtract(lo, tol)))
    assert keep.volume() < 0.01, ('material removed outside the cuts', new, round(keep.volume(), 3))


def cuts_in_print(world, T, cuts):
    """Cut boxes through sourceToPrint and the same drop to the bed as printed()."""
    T = np.array(T, float); m = trimesh.load(world, force='mesh'); m.apply_transform(T); dz = float(m.bounds[0, 2]); out = []
    for lo, hi in cuts:
        c = np.array([[x, y, z, 1.0] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]) @ T.T
        out.append((c[:, :3].min(0) - [0, 0, dz], c[:, :3].max(0) - [0, 0, dz]))
    return out


def allowances(key, new, old, cuts):
    """cuts: print-frame boxes, or None when build.json lists no cuts (then only regions the V1.40 part already had pass)."""
    olds = thin(old, key); allow = []
    for g in thin(new, key):
        lo, hi = np.array(g['bbox'])
        was = [o for o in olds if (lo > np.array(o['bbox'][0]) - 1.0).all() and (hi < np.array(o['bbox'][1]) + 1.0).all()]
        if not was:
            assert cuts is not None, ('new thin region and no cap_cuts_mm in build-v2/build.json', key, g['minMm'], g['areaMm2'], g['bbox'])
            near = any(((lo <= c_hi + NEAR) & (hi >= c_lo - NEAR)).all() for c_lo, c_hi in cuts)
            assert not near, ('new thin region beside a cut', key, g['minMm'], g['areaMm2'], g['bbox'])
        allow.append(dict(bbox=[[c - .05 for c in g['bbox'][0]], [c + .05 for c in g['bbox'][1]]], minMm=round(max(g['minMm'] - .005, 0.01), 3),
                          reason=('present in the V1.40 cap, which printed and was bench-tested'
                                  + ('' if was else f'; more than {NEAR} mm from every cut, where the part is unchanged (diff_confined)'))))
    return allow


def main():
    m = json.loads(V140.read_text()); v140 = {p['key']: p for p in m['parts']}
    b = json.loads((BUILD / 'build.json').read_text())
    ov = b.get('closed_overlap_mm3')
    assert ov and all(v <= 0.01 for v in ov.values()), ov
    rows, sizes, los = [], {}, {}
    why = ('V1.40 bench test (Shawn 2026-11-01): the hatch latch did not work as built; V1.41 redoes the hatch and the cap openings '
           'it latches into. ')
    spec = {
        'battery_backpack_cap': ('back face down as the V1.40 cap (robot x -75.55 + guide shift on the bed)',
                                 'the V1.40 cap with the battery opening widened and two slots for the hatch hooks.'),
        'battery_hatch': ('back down as the V1.40 hatch',
                          'new hatch: two solid ears in roof pockets that stop it pulling back, a solid block 0.3 mm over the battery (foam tape if needed), and one lead window '
                          'the size of a plug.'),
    }
    gw = json.loads(GUIDE_WORLD.read_text())['files']
    for key, (pose, change) in spec.items():
        row = copy.deepcopy(v140[key])
        built = BUILD / f'{key}-world.stl'
        T = (b.get('print', {}).get(key) or {}).get('source_to_print') or v140[key]['sourceToPrint']
        world = PRINT / f'world/{key}.stl'; g = gw[f'{key}.stl']
        assert g['sourceSha256'] == sha(built) and g['sha256'] == sha(world), (key, 'guide world is not the build-v2 part', str(GUIDE_WORLD))
        k = printed(world, T); area = contact(k); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
        kb = printed(built, T); assert np.abs(k.bounds - kb.bounds).max() < 0.01 and abs(contact(kb) - area) < 1.0, key
        want = (b.get('print', {}).get(key) or {}).get('bed_contact_mm2')
        if want: assert area >= 0.9 * want - 1, (key, area, want)
        old = OLD / f'{key}-world.stl'
        if key == 'battery_backpack_cap':
            cuts = b.get('cap_cuts_mm')
            if cuts: diff_confined(old, built, cuts)
            allow = allowances(key, k, printed(old, T), cuts_in_print(built, T, cuts) if cuts else None)
        else:
            allow = []
            assert not thin(k, key), (key, thin(k, key))
        pstl = BUILD / f'{key}-print.stl'
        row.update(key=key, color='Orange', quantity=1, path=ref(world)['path'], sha256=sha(world), sourceToPrint=T,
                   flatContact={'minimumAreaMm2': int(0.9 * area), 'reason': '90 % of the measured contact in this pose.'},
                   poseOrigin=f'{pose}; {area:.1f} mm2 bed contact, {size[2]:.1f} mm tall',
                   changeReason=why + change, thinWallAllowances=allow,
                   poseCheck=dict(bedContactMm2=round(area, 2), printSizeMm=size, **({'printStl': ref(pstl)} if pstl.exists() else {})),
                   incrementalEvidence=ref(BUILD / 'build.json'),
                   evidenceAlso=[ref(built), ref(old), ref(QS / 'DESIGN-CONTRACT.json'), ref(GUIDE_WORLD)]
                                + [ref(p) for p in sorted(QS.glob('build_quickswap*.py'))],
                   supportBlockers=[])
        row['decision'] = 'addition'; row['replacesStockIds'] = []
        row['supersedes'] = f'{key} of V1.40 (printed, bench-tested 2026-11-01)'
        rows.append(row); sizes[key] = size; los[key] = k.bounds[0]
    # cap and hatch side by side along print x, centred on the 256 mm bed, 10 mm apart
    gap = 10.0; total = sum(sizes[r['key']][0] for r in rows) + gap * (len(rows) - 1); x = 128.0 - total / 2; pl = []
    assert total <= 236 and max(s[1] for s in sizes.values()) <= 236, ('plate too small', sizes)
    for r in rows:
        s, lo = sizes[r['key']], los[r['key']]
        pl.append(dict(key=r['key'], copy=1, translation=[round(x - float(lo[0]), 4), round(128.0 - s[1] / 2 - float(lo[1]), 4), 0.0]))
        x += s[0] + gap
    m.update(version='V1.41', parts=rows, placements={'Orange': pl}, processOverrides={},
             processOverrideReason='No process overrides: the Orange profile, as V1.40.',
             retiredParts=[dict(part='battery_backpack_cap (V1.40)', printed='V1.40 print 2026-11-01 (Orange)',
                                reason='replaced by the V1.41 cap with two ear pockets in the roof'),
                           dict(part='battery_hatch (V1.40)', printed='V1.40 print 2026-11-01 (Orange)',
                                reason='replaced by the V1.41 hatch (solid ears in two roof pockets against pull-back, V1.40 flap against lift, solid hold-down block, one plug-size lead window open to the rear)')],
             prototypeScope=('V1.41: battery hatch latch redo after the V1.40 bench test: new hatch (inside hooks, leaf-spring hold-down, '
                             'one plug-size lead window) and the cap with two ear pockets in the roof. Frame unchanged '
                             '(V1.40 frame stays). One Orange plate: battery_backpack_cap, battery_hatch.'),
             knownFitBoundary=('Battery length from the listing (57 mm), not measured. The ear pockets and the block are untested on a '
                               'print. Frame, bars, switch, DFR1202 and battery are reused unchanged.'))
    m.pop('deferred', None)
    m['deliveryContract'] = dict(m['deliveryContract'], colors=['Orange'], filesPerColor=2, fileCount=2, baseline='printed releases through V1.40',
                                 status='INCREMENTAL_REPRINT', supersedes=['battery_backpack_cap and battery_hatch of V1.40'])
    # Profiles are bound by hash at prepare time; the Bambu projects changed to the Textured PEI Plate on 2026-11-01
    # (the X1C refused the Cool Plate file), so the hashes come from the files, not from the V1.40 manifest.
    for prof in m['profiles'].values():
        if Path(prof['path']).is_file(): prof['sha256'] = sha(prof['path'])
    (REL / 'manifest-V1.41.json').write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(guideWorld=str(GUIDE_WORLD), sizes=sizes, placements=pl,
                          allowances={r['key']: len(r['thinWallAllowances']) for r in rows})))


if __name__ == '__main__':
    main()
