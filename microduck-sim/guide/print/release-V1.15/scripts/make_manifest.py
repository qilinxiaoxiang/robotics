"""Write the V1.15 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.15 is the single print-now package (Shawn 2026-10-14: one package). Orange plate: the layout F box regenerated with the hidden cap screw and no P1 (orange_parts()); White plate as V1.14. V1.14 had been re-sliced after the
Bambu fix (filament_self_index per variant row and --min-save) so the X1C files open in Bambu Studio on Preview without an error.
V1.14 was the first single package (V1.11 plus V1.12). It carries the V1.11 Orange
plate unchanged in geometry and pose (rear_frame, rear_lid; brim by the pipeline v2 R1 default instead of a plate-wide
override) and the V1.12 White plate unchanged. Neither V1.11 nor V1.12 was printed; both are superseded.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.15.json]

One White plate (colour scheme C, Shawn 2026-10-14): the V2.0 side shells (screwed to the V1.9 pack, which Shawn confirmed is on
the robot), the stock thighs community-74 and community-72 reprinted in white, and the V1.9 head cap reprinted
in white (unchanged geometry: the head stays on ROBOTIS M2.6 screws, Shawn 2026-10-14). Rows come from rows.json;
each row names its pose in pose-sources.json (scripts/pose_sources.py). The script pins every source sha256, measures each
pose's bed contact with the pipeline rule (triangles within 0.01 mm of the bed after the drop) and checks it against the row's
flatContactMinimumMm2, copies objectSettings (per-object brim, pipeline v2) and colourOnlyReprint, takes the baseline stock and
the donor profiles from V1.11, and writes the White support overrides from PLAN-V1.12.md section C4.

The V2.0 head cap, lower head shell and jaw frame (v20-source) are not in V1.12: Shawn deferred them until the head is next
opened and kept the whole head on M2.6.
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
REL = HERE.parent
PRINT = REL.parent
V111 = json.loads((PRINT / 'release-V1.11/manifest-V1.11.json').read_text())
# The V1.11 Orange plate as it was sliced and released (arrange() result in release-V1.11/run/preparation.json).
V111_ORANGE_PLACEMENTS = next(r['placements'] for r in json.loads((PRINT / 'release-V1.11/run/preparation.json').read_text())['rows'] if r['color'] == 'Orange')
PINNED = {  # print/v20-source/README.md and the stock copy-manifest
    'shell_left_v20': '4e55338ec1eb24ad5d70daccd4a7f36bdc29251b32f478339fed7a8f3dc35410',
    'shell_right_v20': 'a718e9279c97254fe335d7064c90aa6a18d2e72065860ffad058334d1ced63a7',
    'head_cap_v19_white': 'da655c657979c9290a1aa12d813901062baea2c38c0da31db085c986277976c2',
    'thigh_left': '5b21f2cc1e90c4a48bf977814a20a4f20f41231424832b81ed947b4f4925b710',
    'thigh_right': '2eda6338c20e99940f23b2d71f5103d8119ead44e4e32fb28228afaa00ed1a4d',
}
# PLAN-V1.12.md C4: carry the V1.9 Orange support interface onto the White plate (the White donors print 2 interface layers
# at 0.5 mm spacing and 80 mm/s), and iron the support interface under the cap crown. The White Elegoo donor uses
# tree_hybrid; the V1.9 cap crown was measured with support_style default, so the Elegoo plate uses default too.
SUPPORT = {'support_interface_top_layers': '3', 'support_interface_spacing': '0.15', 'support_top_z_distance': '0.2',
           'support_interface_speed': ['40', '40'], 'bridge_speed': ['30', '30'], 'enable_support_ironing': '1'}
# One White plate (release_pipeline_v2.arrange fills its 196 mm square in one row order and refuses this set). Placement
# targets the lower-left corner of each print-frame bounding box (mm on the bed); 12 mm between parts, 16 mm beside the cap
# for its 4.1 mm brim. Row 1: cap, left shell. Row 2: right shell, left thigh, right thigh. Extent x 33.8..222.2, y 34..222.1.
PLATE = [('head_cap_v19_white', 33.8, 34.0), ('shell_left_v20', 176.3, 34.0),
         ('shell_right_v20', 33.8, 141.6), ('thigh_left', 88.2, 141.6), ('thigh_right', 161.2, 141.6)]
# First layer 0.2 mm as on the V1.9 cap print and every other colour's donor (the White donors alone use 0.28). At 0.28 the
# slicer cuts the crown strip at z 0.14 (586 mm2, a 12 mm2 concave end) instead of z 0.1 (464 mm2), and the first native
# White slice put 2.6 mm2 of the cap brim into that concave end on the visible crown (brim_review limit 2.0 mm2).
FIRST_LAYER = {'initial_layer_print_height': '0.2'}
PROCESS_OVERRIDES = {'White_Bambu': dict(SUPPORT, **FIRST_LAYER),
                     'White_Elegoo': dict(SUPPORT, support_ironing='1', support_style='default', **FIRST_LAYER)}
PROCESS_OVERRIDE_REASON = (
    'PLAN-V1.12.md section C (the rough crown Shawn sanded on the V1.9 cap is its outer dome printed on support interface). '
    'The cap keeps the V1.9 roof-down pose, so the crown band still prints on single-material support (the club X1C has an AMS '
    'but no support material, Shawn 2026-10-14). The White donor profiles print that interface coarser than the V1.9 Orange '
    'files: 2 interface layers at 0.5 mm spacing and 80 mm/s, bridges at 50 mm/s. These overrides carry the V1.9 Orange values '
    '(3 layers, 0.15 mm spacing, top z gap 0.2 mm, interface 40 mm/s, bridges 30 mm/s) and turn on support ironing at the '
    'donor default flow (10 %) and spacing (0.15 mm), which reprints the top interface layer smooth. Elegoo: support_ironing is '
    'set next to enable_support_ironing, and support_style default replaces the donor tree_hybrid to match the V1.9 slice the '
    'crown was measured on. First layer 0.2 mm (White donors 0.28) as on the V1.9 cap and the other colours: at 0.28 the cap brim '
    'filled 2.6 mm2 of the concave end of the crown strip in the first White slice. Brim: per object (rows.json objectSettings), not plate-wide.')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p); assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def contact(path, T):
    m = trimesh.load(path, force='mesh', process=False)
    v, inv = np.unique(m.vertices, axis=0, return_inverse=True)
    m = trimesh.Trimesh(v, inv.reshape(-1)[m.faces], process=False); m.apply_transform(np.array(T, float))
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    return float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum()), (m.bounds[1] - m.bounds[0]).round(2).tolist()


LAYOUT_F = PRINT / 'back-plate/layout-F'
ORANGE_ROWS = {r['key']: r for r in json.loads((HERE / 'rows-orange.json').read_text())}
ORANGE_CHANGE = {
    'rear_frame': ('V1.15 rear converter box frame, layout F regenerated from build_f.py (back-plate/layout-F/README.md): the V1.11 frame with the two '
                   'cap-screw ear bosses and their webs removed and the front passage P1 filled (solid front plate), plus a 1.1 x 1.2 mm notch in the '
                   'top edge of the 5991 terminal window (-y wall) for the cap hook. Shawn 2026-10-14: every box wire runs outside the box through the '
                   'side windows or over the box top (the slot made assembly hard and left a seam between the boards), and the +y ear tail was ugly. Everything else is the '
                   'V1.11 frame: cover outline, four cover holes and lip, wide and narrow tiers, side windows, USB-C slot, eight XL4015 bosses, four 5991 '
                   'bosses, two tooth slots, driver lanes. Added 2026-10-14 (Shawn: wires drop in over the top of the side shell, not through the plate): '
                   'wire notch A, the top-wall front edge cut back from x -47.0 to -49.8 over y 3.2..12.4 (rear corners r 1.0), and notch B, the '
                   'cover-plate top edge lowered from z 29.5 to 28.5 over the same band (floor corners r 0.5, cover lip untouched); the 7 V and 5 V '
                   'pairs climb the outside of the +y wall, cross the box top, drop through notch A into the box front cavity and pass under the '
                   'shell lip through notch B onto the cover lip into the pack. Volume 10253.3 mm3, watertight, one body (layout-F/checks.json, post_build.json).'),
    'rear_lid': ('V1.15 cap: the V1.11 rounded cap without its two screw ears. It is held by the two top tongues (teeth in the frame top-wall slots), '
                 'one M2 x 10 driven from a dia 4.4 hole in the cap back down a dia 5.6 column (floor x -56.1..-55.1, dia 2.3 clearance) on the axis '
                 '(y +11.367, z -16.667) through the 5991 upper +y mounting hole into its existing boss (3.9 mm of thread; that 5991 corner keeps its '
                 'position from the screw shank), and a hook tab (x -60.3..-57.4) with a 1 mm tooth in the top edge of the 5991 terminal window on -y, '
                 'engaged by the same 1.2 mm lift. Nothing outside the box outline (layout-F-ear-20261014/hidden/README.md, Shawn chose it 2026-10-14). '
                 'Volume 6323.0 mm3, watertight, one body.'),
}
ORANGE_POSE_FIX = {
    'rear_frame': [('296.8 mm2 bed contact (the 1.2 mm wall ring and the two cap-screw boss ends on a 64.1 x 87.0 mm footprint)',
                    '252.0 mm2 bed contact (the 1.2 mm wall ring alone on a 64.1 x 87.0 mm footprint; the cap-screw bosses are gone)')],
    'rear_lid': [('2643.2 mm2 bed contact, 13.5 mm tall (the tongues point up). The rounded rear edges (R 4.3..8.0) leave the bed at a shallow angle and the two screw ears overhang at the top: tree support under both.',
                  '2643.7 mm2 bed contact, 13.5 mm tall (the tongues point up). The rounded rear edges (R 4.3..8.0) leave the bed at a shallow angle: tree support under them. The screw column stands vertical with its driver hole open on the bed face and a 1 mm floor bridging over the dia 2.3 clearance hole.')],
}


def orange_parts():
    """The V1.11 Orange records with the regenerated layout-F files bound in: sha, contact, change reason, evidence."""
    out = []
    for tpl in V111['parts']:
        p = dict(tpl); key = p['key']; row = ORANGE_ROWS[key]
        src = ref(LAYOUT_F / f'{key}-world.stl'); p['path'] = src['path']; p['sha256'] = src['sha256']
        area, size = contact(src['path'], p['sourceToPrint'])
        assert row['flatContactMinimumMm2'] <= area, f'{key}: bed contact {area:.1f} mm2 below the V1.15 row minimum {row["flatContactMinimumMm2"]}'
        p['flatContact'] = {'minimumAreaMm2': row['flatContactMinimumMm2']}
        if 'flatContactMinimumReason' in row: p['flatContact']['reason'] = row['flatContactMinimumReason']
        po = p['poseOrigin']
        for a, b in ORANGE_POSE_FIX[key]:
            assert a in po, f'{key}: pose text drifted'
            po = po.replace(a, b)
        p['poseOrigin'] = po
        p['poseCheck'] = dict(printStl=ref(LAYOUT_F / f'{key}-print.stl'), bedContactMm2=round(area, 2), printSizeMm=size,
                              note='V1.15: contact recomputed from the regenerated world STL with the V1.11 sourceToPrint (same print pose)')
        p['changeReason'] = ORANGE_CHANGE[key]
        p['incrementalEvidence'] = ref(LAYOUT_F / 'checks.json')
        p['evidenceAlso'] = [ref(LAYOUT_F / n) for n in ('build.json', 'README.md', 'layout_f.json', 'post_build.json', 'features.json')]
        p['supersedes'] = f'{key} of release V1.14 / V1.13 / V1.11 (same plate, never printed)'
        out.append(p)
    assert [p['key'] for p in out] == ['rear_frame', 'rear_lid'] and all(p['color'] == 'Orange' for p in out)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.15.json'); a = ap.parse_args()
    rows = json.loads((HERE / 'rows.json').read_text())
    poses = json.loads((HERE / 'pose-sources.json').read_text())
    parts = []
    for r in rows:
        src = ref(r['path'])
        assert src['sha256'] == PINNED[r['key']], f'{r["key"]}: STL sha256 {src["sha256"]} differs from the pinned source'
        pose = poses['poses'][r['key']][r['pose']]
        dev = pose.get('maxVertexDeviationMm')
        assert dev is None or dev < 1e-3, f'{r["key"]}: pose registration residual {dev}'
        area, size = contact(src['path'], pose['sourceToPrint'])
        assert r['flatContactMinimumMm2'] <= area, f'{r["key"]}: bed contact {area:.1f} mm2 below the stated minimum'
        part = dict(
            key=r['key'], color=r['color'], quantity=int(r.get('quantity', 1)), decision=r['decision'],
            replacesStockIds=[str(x) for x in r['replacesStockIds']], path=src['path'], sha256=src['sha256'],
            sourceFrame=r['sourceFrame'], sourceToPrint=pose['sourceToPrint'], flatContact={'minimumAreaMm2': r['flatContactMinimumMm2']},
            poseName=r['pose'], poseOrigin=r['poseOrigin'],
            poseCheck=dict(ref(HERE / 'pose-sources.json'), bedContactMm2=round(area, 2), printSizeMm=size, registrationMaxDeviationMm=dev),
            changeReason=r['changeReason'], supersedes=r['supersedes'], incrementalEvidence=ref(r['incrementalEvidence']),
            evidenceAlso=[ref(x) for x in r.get('evidenceAlso', [])],
            supportBlockers=[dict(ref(b['path']), machines=b['machines'], reason=b['reason']) for b in r.get('supportBlockers', [])])
        part.update({k: r[k] for k in ('objectSettings', 'objectSettingsReason', 'colourOnlyReprint') if k in r})
        parts.append(part)
    placements = []
    for key, x0, y0 in PLATE:
        r = next(x for x in rows if x['key'] == key); pose = poses['poses'][key][r['pose']]
        m_ = trimesh.load(r['path'], force='mesh'); m_.apply_transform(np.array(pose['sourceToPrint'], float)); lo = m_.bounds[0]
        placements.append(dict(key=key, copy=1, translation=[round(x0 - float(lo[0]), 4), round(y0 - float(lo[1]), 4), 0.0]))
    assert sorted(k for k, _, _ in PLATE) == sorted(r['key'] for r in rows)
    colors = sorted({p['color'] for p in parts})
    orange = orange_parts()
    parts = orange + parts
    colors = sorted({p['color'] for p in parts})
    assert colors == ['Orange', 'White'], colors
    m = dict(
        schemaVersion=1, releaseKind='incremental', version='V1.15', prototype=True,
        prototypeScope=('V1.15 single print-now package: the layout F rear converter box frame and cap regenerated without the cap ears (one hidden M2 x 10 plus a hook) and without the front passage P1 (every box wire runs outside the box), same print poses as V1.11, plus the V1.12 White increment unchanged on top of the printed V1.8 set, the V1.9 Orange plate and the released V1.11 box: '
                        'colour scheme C (Shawn, 2026-10-14). One White plate: the V2.0 side shells (one M2 x 6 each down into the '
                        'V1.9 pack shoulder bar, cross tunnel filled, M2 x 4 horn screws in counterbores), the two stock thighs in '
                        'white (colour only) and the V1.9 head cap in white (colour only, same STL: the head stays on ROBOTIS '
                        'M2.6 screws). The orange shells, thighs and V1.9 cap become spares. The V2.0 cap, lower head shell and jaw '
                        'frame are deferred until the head is next opened.'),
        knownFitBoundary=('Shells need the V1.9 rear pack (its shoulder bars); Shawn confirmed it is fitted. The pack bar has no printed '
                          'pilot: drill dia 1.6 through the shell roof hole with a tape flag 7.0 mm from the tip. Driver above each pack '
                          'screw on the finished robot: 57.8 mm to the lower head shell. Cap: the same V1.9 cap that is on the robot, closed with the '
                          'same three ROBOTIS M2.6 x 6. Thighs: same geometry as the 10/1 thighs; fitting them means '
                          'taking both legs apart and re-reading the joint zeros (guide/firmware/mac/pose_snapshot.py).'),
        baselineStock=V111['baselineStock'], profiles=V111['profiles'],
        placements={'White': placements, 'Orange': V111_ORANGE_PLACEMENTS},
        processOverrides=PROCESS_OVERRIDES, processOverrideReason=PROCESS_OVERRIDE_REASON,
        parts=parts,
        retiredParts=V111['retiredParts'] + [dict(part='shell_left (community-8)', printed='10/1 batch (Orange)', reason='replaced by the white V2.0 left shell; keep as a spare'),
                      dict(part='shell_right (community-10)', printed='10/1 batch (Orange)', reason='replaced by the white V2.0 right shell; keep as a spare'),
                      dict(part='thigh_left (community-74)', printed='10/1 batch (Orange)', reason='replaced by the same thigh in white; keep as a spare'),
                      dict(part='thigh_right (community-72)', printed='10/1 batch (Orange)', reason='replaced by the same thigh in white; keep as a spare'),
                      dict(part='head_cap_v19', printed='V1.9 (Orange)', reason='replaced by the same cap in white (colour only); keep as a spare')],
        deferred=[dict(part='head_cap_v20', path=str(PRINT / 'v20-source/head_cap_v20-world.stl'), reason='Shawn 2026-10-14: the head stays on ROBOTIS M2.6 screws while the lower shell is not reprinted; print with the V2.0 lower shell when the head is next opened'),
                  dict(part='head_bottom_v20', path=str(PRINT / 'v20-source/head_bottom_v20-world.stl'), reason='Shawn 2026-10-14: no real change; print when the head is next opened'),
                  dict(part='jaw_frame_v20', path=str(PRINT / 'v20-source/jaw_frame_v20-world.stl'), reason='Shawn 2026-10-14: no real change; print when the head is next opened')],
        deliveryContract=dict(colors=colors, filesPerColor=2, fileCount=2 * len(colors),
                              baseline='printed V1.8 set with the V1.9 Orange plate',
                              supersedes=['release V1.14 (box with ears and P1, not printed)', 'release V1.13 and V1.11 (same, not printed)', 'release V1.12 (same White plate, not printed)', 'rear_pack_cover (printed V1.8)', 'shell_left and shell_right (10/1, orange)', 'thigh_left and thigh_right (10/1, orange)', 'head_cap_v19 (V1.9, orange)'],
                              status='INCREMENTAL_REPRINT'))
    assert sha(m['baselineStock']['path']) == m['baselineStock']['sha256'], 'baseline stock drift'
    for k, v in m['profiles'].items():
        assert sha(v['path']) == v['sha256'], f'profile drift {k}'
    a.out.write_text(json.dumps(m, indent=1))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p.get('poseName'), p['poseCheck']['bedContactMm2'], p.get('objectSettings')) for p in parts]), indent=1))


if __name__ == '__main__':
    main()
