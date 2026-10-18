"""Write the V1.17 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.17 is the single print-now package (Shawn 2026-10-14: one package with everything unprinted): all of V1.16 plus three head
parts for the Radxa Cubie A7Z and the Radxa Camera 13M 214 (Shawn 2026-10-15: "give me a new eye ring and front face print file,
merged into the unprinted 1.16"). V1.16 is superseded unprinted.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.17.json]

Changes against V1.16 (scripts/make_manifest.py there; everything else is that script unchanged):
- White plate: the A7Z head cap (a7z-head/head_cap_a7z-world.stl, the V1.9 cap with material removed inside only) replaces
  head_cap_v19_white in the same V1.9 pose with the same 4 mm brim, support blocker, support overrides and first layer; the
  A7Z face panel (face-a7z/face_panel_a7z.stl, robot frame = world/face_panel.stl, V1.8 face transform) is added and replaces the printed V1.8 face. The V1.16
  layout is moved 12 mm towards the front of the bed (same spacing) so the face fits behind the thighs.
- Orange plate: the A7Z cap wire clip (a7z-head/clip_cap_a7z-world.stl, V1.9 clip pose) is added to the V1.16 box plate
  (layout F frame and cap, unchanged) and replaces the printed V1.9 cap clip.
- The eye trim is unchanged (byte-identical to the V1.8 trim) and is not reprinted.
Rows come from rows.json; each row names its pose in pose-sources.json (V1.16, unchanged) or pose-sources-a7z.json
(scripts/pose_sources_a7z.py). The script pins every source sha256, measures each pose's bed contact with the pipeline rule
(triangles within 0.01 mm of the bed after the drop) and checks it against the row's flatContactMinimumMm2.
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
    'head_cap_a7z': 'bbedb8044687c86906cdcf1adb82eae5c3c5f8bb84fc8bdd24f5824375b5e257',   # a7z-head/build_a7z_head.py
    'face_panel_a7z': 'ff0fa31c726fa0bd5b8d31602126bf4995d445b7d60c0e8e7c9e634314611ef1',  # face-a7z/face_panel_a7z.stl = world/face_panel.stl (guide geometry)
    'clip_cap_a7z': 'ab50937dac7f6bf43bca5eb083d28a1369cedc7a97082f6abc8ddaa85d562d21',   # a7z-head/build_a7z_head.py
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
# for its 4.1 mm brim. V1.16 layout moved 12 mm to the front (y 34 -> 22) with the same spacing, plus the face 12 mm behind
# the left thigh. Row 1: cap, left shell. Row 2: right shell, left thigh, right thigh. Row 3: face (87.7 x 44.6 mm) beside the
# right shell. Extent x 33.8..222.2, y 22.0..233.9 (cap brim to y 17.9); pipeline model limit 18..238 on both axes.
DY = -12.0
PLATE = [('head_cap_a7z', 33.8, 34.0 + DY), ('shell_left_v20', 176.3, 34.0 + DY),
         ('shell_right_v20', 33.8, 141.6 + DY), ('thigh_left', 88.2, 141.6 + DY), ('thigh_right', 161.2, 141.6 + DY),
         ('face_panel_a7z', 88.2, 141.6 + DY + 47.7 + 12.0)]
# Orange plate: the V1.11 / V1.16 box plate (frame x 57.9..122.0, lid x 134.0..198.1, y 84.5..171.5) plus the clip 12 mm
# behind the lid, lower-left corner of its print-frame box at (134.0, 175.5): extent y 84.5..193.3.
ORANGE_ADD = [('clip_cap_a7z', 134.0, 175.5)]
A7Z = {'head_cap_a7z', 'face_panel_a7z', 'clip_cap_a7z'}
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
    'rear_frame': ('V1.16 rear converter box frame, layout F regenerated from build_f.py (back-plate/layout-F/README.md): the V1.11 frame with the two '
                   'cap-screw ear bosses and their webs removed, the front passage P1 filled (solid front plate) and no tooth slots or hook notch '
                   '(Shawn 2026-10-15: the cap is held by screws only). Shawn 2026-10-14: every box wire runs outside the box through the '
                   'side windows or over the box top (the slot made assembly hard and left a seam between the boards), and the +y ear tail was ugly. Everything else is the '
                   'V1.11 frame: cover outline, four cover holes and lip, wide and narrow tiers, side windows, USB-C slot, eight XL4015 bosses, four 5991 '
                   'bosses, driver lanes. The two XL4015 bosses at z 38.7 and the two upper 5991 bosses now take the cap screws. '
                   'Wire notch A, the top-wall front edge cut back from x -47.0 to -49.8 over y 3.2..12.4 (rear corners r 1.0), and notch B, the '
                   'cover-plate top edge lowered from z 29.5 to 28.5 over the same band (floor corners r 0.5, cover lip untouched); the 7 V and 5 V '
                   'pairs climb the outside of the +y wall, cross the box top, drop through notch A into the box front cavity and pass under the '
                   'shell lip through notch B onto the cover lip into the pack. Volume 10292.8 mm3, watertight, one body (layout-F/checks.json, post_build.json).'),
    'rear_lid': ('V1.16 cap: the V1.11 rounded cap without its two screw ears, tongues or hook; it pushes straight on (Shawn 2026-10-15: "if a screw fits, use a screw"). '
                 'Four hidden M2 x 10, each driven from a dia 4.4 hole in the cap back down a dia 5.6 column onto a 1.0 mm floor with a dia 2.3 clearance hole: '
                 'two low columns (floor x -56.1..-55.1) on the 5991 upper hole axes (y +11.367, z -16.667) and (y -11.366, z -16.54) through the 5991 into its standoff bosses (3.9 mm of thread), '
                 'and two top columns (floor x -55.6..-54.6, flattened to |y| <= 30.6, z <= 41.55 inside the frame) on the 7 V XL4015 top corner hole axes (y +-28.25, z 38.7) '
                 'through the board into the frame bosses (4.6 mm of thread). Ray cast in layout-F/raycast_cap_screws.json. Nothing outside the box outline. '
                 'Volume 6404.0 mm3, watertight, one body.'),
}
ORANGE_POSE_FIX = {
    'rear_frame': [('296.8 mm2 bed contact (the 1.2 mm wall ring and the two cap-screw boss ends on a 64.1 x 87.0 mm footprint)',
                    '252.0 mm2 bed contact (the 1.2 mm wall ring alone on a 64.1 x 87.0 mm footprint; the cap-screw bosses are gone)')],
    'rear_lid': [('2643.2 mm2 bed contact, 13.5 mm tall (the tongues point up). The rounded rear edges (R 4.3..8.0) leave the bed at a shallow angle and the two screw ears overhang at the top: tree support under both.',
                  '2634.0 mm2 bed contact, 12.5 mm tall (open side up, no tongues). The rounded rear edges (R 4.3..8.0) leave the bed at a shallow angle: tree support under them. The four screw columns stand vertical with their driver holes open on the bed face and 1 mm floors bridging over the dia 2.3 clearance holes.'),
                 ('the tongues stand 5.5 mm proud of the rim.', 'the four screw columns stand up to 4.5 mm proud of the rim.')],
}


def orange_parts():
    """The V1.11 Orange records with the regenerated layout-F files bound in: sha, contact, change reason, evidence."""
    out = []
    for tpl in V111['parts']:
        p = dict(tpl); key = p['key']; row = ORANGE_ROWS[key]
        src = ref(LAYOUT_F / f'{key}-world.stl'); p['path'] = src['path']; p['sha256'] = src['sha256']
        area, size = contact(src['path'], p['sourceToPrint'])
        assert row['flatContactMinimumMm2'] <= area, f'{key}: bed contact {area:.1f} mm2 below the V1.16 row minimum {row["flatContactMinimumMm2"]}'
        p['flatContact'] = {'minimumAreaMm2': row['flatContactMinimumMm2']}
        if 'flatContactMinimumReason' in row: p['flatContact']['reason'] = row['flatContactMinimumReason']
        po = p['poseOrigin']
        for a, b in ORANGE_POSE_FIX[key]:
            assert a in po, f'{key}: pose text drifted'
            po = po.replace(a, b)
        p['poseOrigin'] = po
        p['poseCheck'] = dict(printStl=ref(LAYOUT_F / f'{key}-print.stl'), bedContactMm2=round(area, 2), printSizeMm=size,
                              note='V1.16: contact recomputed from the regenerated world STL with the V1.11 sourceToPrint (same print pose)')
        p['changeReason'] = ORANGE_CHANGE[key]
        p['incrementalEvidence'] = ref(LAYOUT_F / 'checks.json')
        p['evidenceAlso'] = [ref(LAYOUT_F / n) for n in ('build.json', 'README.md', 'layout_f.json', 'post_build.json', 'features.json')]
        p['supersedes'] = f'{key} of release V1.15 / V1.14 / V1.13 / V1.11 (same plate, never printed)'
        out.append(p)
    assert [p['key'] for p in out] == ['rear_frame', 'rear_lid'] and all(p['color'] == 'Orange' for p in out)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.17.json'); a = ap.parse_args()
    rows = json.loads((HERE / 'rows.json').read_text())
    poses = json.loads((HERE / 'pose-sources.json').read_text())
    poses['poses'].update(json.loads((HERE / 'pose-sources-a7z.json').read_text())['poses'])
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
            poseCheck=dict(ref(HERE / ('pose-sources-a7z.json' if r['key'] in A7Z else 'pose-sources.json')), bedContactMm2=round(area, 2), printSizeMm=size, registrationMaxDeviationMm=dev),
            changeReason=r['changeReason'], supersedes=r['supersedes'], incrementalEvidence=ref(r['incrementalEvidence']),
            evidenceAlso=[ref(x) for x in r.get('evidenceAlso', [])],
            supportBlockers=[dict(ref(b['path']), machines=b['machines'], reason=b['reason']) for b in r.get('supportBlockers', [])])
        part.update({k: r[k] for k in ('objectSettings', 'objectSettingsReason', 'colourOnlyReprint') if k in r})
        if 'flatContactMinimumReason' in r: part['flatContact']['reason'] = r['flatContactMinimumReason']
        parts.append(part)
    def place(key, x0, y0):
        r = next(x for x in rows if x['key'] == key); pose = poses['poses'][key][r['pose']]
        m_ = trimesh.load(r['path'], force='mesh'); m_.apply_transform(np.array(pose['sourceToPrint'], float)); lo = m_.bounds[0]
        return dict(key=key, copy=1, translation=[round(x0 - float(lo[0]), 4), round(y0 - float(lo[1]), 4), 0.0])
    placements = [place(*x) for x in PLATE]
    orange_add = [place(*x) for x in ORANGE_ADD]
    assert sorted(k for k, _, _ in PLATE) == sorted(r['key'] for r in rows if r['color'] == 'White')
    assert sorted(k for k, _, _ in ORANGE_ADD) == sorted(r['key'] for r in rows if r['color'] == 'Orange')
    colors = sorted({p['color'] for p in parts})
    orange = orange_parts()
    parts = orange + parts
    colors = sorted({p['color'] for p in parts})
    assert colors == ['Orange', 'White'], colors
    m = dict(
        schemaVersion=1, releaseKind='incremental', version='V1.17', prototype=True,
        prototypeScope=('V1.17 single print-now package: all of V1.16 plus three head parts for the Radxa Cubie A7Z and the Radxa Camera 13M 214 '
                        '(Shawn 2026-10-15), on top of the printed V1.8 set and the V1.9 Orange plate. Orange plate: the layout F rear converter '
                        'box frame and cap of V1.16 (four hidden M2 x 10, no front passage P1, same print poses as V1.11) plus the A7Z cap wire '
                        'clip (the V1.9 cap clip with a notch over the micro HDMI). White plate: colour scheme C (Shawn, 2026-10-14), the V2.0 side '
                        'shells, the two stock thighs in white (colour only), the A7Z head cap in white (the V1.9 cap with the board rails '
                        'relieved to round pads at the four holes and a slot through each rail end for the camera connector and the microSD; '
                        'the head stays on ROBOTIS M2.6 screws) and the A7Z face panel (four camera bosses on its back, front unchanged). '
                        'The eye trim is the V1.8 trim byte for byte and is reused. The orange shells, thighs and V1.9 cap become spares; the '
                        'V1.8 face and the V1.9 cap clip are retired. The V2.0 cap, lower head shell and jaw frame stay deferred until the '
                        'head is next opened.'),
        knownFitBoundary=('Shells need the V1.9 rear pack (its shoulder bars); Shawn confirmed it is fitted. The pack bar has no printed '
                          'pilot: drill dia 1.6 through the shell roof hole with a tape flag 7.0 mm from the tip. Driver above each pack '
                          'screw on the finished robot: 57.8 mm to the lower head shell. Cap: closes with the same three ROBOTIS M2.6 x 6 '
                          'as the V1.9 cap; the A7Z rests on the four round pads and screws on with the Pi screws (E-pi-01..04). Face: the '
                          'camera takes 4 x M2 x 4 into 2.4 mm of thread (below the 3.5 mm target, face-a7z/README.md) and the eye trim '
                          '2 x M2 x 6 from the face back; the image needs a 90 deg rotation in software. Thighs: same geometry as the 10/1 '
                          'thighs; fitting them means taking both legs apart and re-reading the joint zeros (guide/firmware/mac/pose_snapshot.py).'),
        baselineStock=V111['baselineStock'], profiles=V111['profiles'],
        placements={'White': placements, 'Orange': V111_ORANGE_PLACEMENTS + orange_add},
        processOverrides=PROCESS_OVERRIDES, processOverrideReason=PROCESS_OVERRIDE_REASON,
        parts=parts,
        retiredParts=V111['retiredParts'] + [dict(part='shell_left (community-8)', printed='10/1 batch (Orange)', reason='replaced by the white V2.0 left shell; keep as a spare'),
                      dict(part='shell_right (community-10)', printed='10/1 batch (Orange)', reason='replaced by the white V2.0 right shell; keep as a spare'),
                      dict(part='thigh_left (community-74)', printed='10/1 batch (Orange)', reason='replaced by the same thigh in white; keep as a spare'),
                      dict(part='thigh_right (community-72)', printed='10/1 batch (Orange)', reason='replaced by the same thigh in white; keep as a spare'),
                      dict(part='head_cap_v19', printed='V1.9 (Orange)', reason='replaced by the white A7Z head cap; keep as a spare for the Pi Zero W'),
                      dict(part='face_panel (V1.8)', printed='V1.8 (White)', reason='replaced by the A7Z face panel: its back carries the Camera Module 3 lands and pegs, not the 13M 214 bosses'),
                      dict(part='clip_cap_v19', printed='V1.9 (Orange)', reason='replaced by the A7Z cap clip: its arm crosses the A7Z micro HDMI socket')],
        deferred=[dict(part='head_cap_v20', path=str(PRINT / 'v20-source/head_cap_v20-world.stl'), reason='Shawn 2026-10-14: the head stays on ROBOTIS M2.6 screws while the lower shell is not reprinted; print with the V2.0 lower shell when the head is next opened'),
                  dict(part='head_bottom_v20', path=str(PRINT / 'v20-source/head_bottom_v20-world.stl'), reason='Shawn 2026-10-14: no real change; print when the head is next opened'),
                  dict(part='jaw_frame_v20', path=str(PRINT / 'v20-source/jaw_frame_v20-world.stl'), reason='Shawn 2026-10-14: no real change; print when the head is next opened')],
        deliveryContract=dict(colors=colors, filesPerColor=2, fileCount=2 * len(colors),
                              baseline='printed V1.8 set with the V1.9 Orange plate',
                              supersedes=['release V1.16 (same box and White plate without the A7Z parts, not printed)', 'release V1.15 and V1.14 (box with ears or hook and P1, not printed)', 'release V1.13 and V1.11 (same, not printed)', 'release V1.12 (same White plate, not printed)', 'rear_pack_cover (printed V1.8)', 'shell_left and shell_right (10/1, orange)', 'thigh_left and thigh_right (10/1, orange)', 'head_cap_v19 (V1.9, orange)', 'face_panel (V1.8, white)', 'clip_cap_v19 (V1.9, orange)'],
                              status='INCREMENTAL_REPRINT'))
    assert sha(m['baselineStock']['path']) == m['baselineStock']['sha256'], 'baseline stock drift'
    for k, v in m['profiles'].items():
        assert sha(v['path']) == v['sha256'], f'profile drift {k}'
    a.out.write_text(json.dumps(m, indent=1))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p.get('poseName'), p['poseCheck']['bedContactMm2'], p.get('objectSettings')) for p in parts]), indent=1))


if __name__ == '__main__':
    main()
