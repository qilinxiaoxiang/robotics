"""Write the V1.12 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.12.json]

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


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.12.json'); a = ap.parse_args()
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
    assert colors == ['White'], colors
    m = dict(
        schemaVersion=1, releaseKind='incremental', version='V1.12', prototype=True,
        prototypeScope=('V1.12 White increment on top of the printed V1.8 set, the V1.9 Orange plate and the released V1.11 box: '
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
        placements={'White': placements},
        processOverrides=PROCESS_OVERRIDES, processOverrideReason=PROCESS_OVERRIDE_REASON,
        parts=parts,
        retiredParts=[dict(part='shell_left (community-8)', printed='10/1 batch (Orange)', reason='replaced by the white V2.0 left shell; keep as a spare'),
                      dict(part='shell_right (community-10)', printed='10/1 batch (Orange)', reason='replaced by the white V2.0 right shell; keep as a spare'),
                      dict(part='thigh_left (community-74)', printed='10/1 batch (Orange)', reason='replaced by the same thigh in white; keep as a spare'),
                      dict(part='thigh_right (community-72)', printed='10/1 batch (Orange)', reason='replaced by the same thigh in white; keep as a spare'),
                      dict(part='head_cap_v19', printed='V1.9 (Orange)', reason='replaced by the same cap in white (colour only); keep as a spare')],
        deferred=[dict(part='head_cap_v20', path=str(PRINT / 'v20-source/head_cap_v20-world.stl'), reason='Shawn 2026-10-14: the head stays on ROBOTIS M2.6 screws while the lower shell is not reprinted; print with the V2.0 lower shell when the head is next opened'),
                  dict(part='head_bottom_v20', path=str(PRINT / 'v20-source/head_bottom_v20-world.stl'), reason='Shawn 2026-10-14: no real change; print when the head is next opened'),
                  dict(part='jaw_frame_v20', path=str(PRINT / 'v20-source/jaw_frame_v20-world.stl'), reason='Shawn 2026-10-14: no real change; print when the head is next opened')],
        deliveryContract=dict(colors=colors, filesPerColor=2, fileCount=2 * len(colors),
                              baseline='printed V1.8 set with the V1.9 Orange plate and the V1.11 box',
                              supersedes=['shell_left and shell_right (10/1, orange)', 'thigh_left and thigh_right (10/1, orange)', 'head_cap_v19 (V1.9, orange)'],
                              status='INCREMENTAL_REPRINT'))
    assert sha(m['baselineStock']['path']) == m['baselineStock']['sha256'], 'baseline stock drift'
    for k, v in m['profiles'].items():
        assert sha(v['path']) == v['sha256'], f'profile drift {k}'
    a.out.write_text(json.dumps(m, indent=1))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p['poseName'], p['poseCheck']['bedContactMm2'], p.get('objectSettings')) for p in parts]), indent=1))


if __name__ == '__main__':
    main()
