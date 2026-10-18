"""Write the V1.11 incremental release manifest (13-RELEASE-PIPELINE schema 1).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.11.json]

Rows come from rows.json next to this script: rear_frame and rear_lid (Orange), the two printed parts of the rear
converter box, layout F (guide/print/back-plate/layout-F/). V1.11 supersedes V1.10 (layout C revision 2). The script
fills in sha256 values, copies the V1.9 baseline stock and slicer profiles, checks both sources against the sha256
pinned below (the layout F build), checks that scripts/pose-check.json (scripts/verify_poses.py) passed for these exact
sources and poses, and checks every referenced file.

The printed V1.8 rear_pack_cover was an addition in V1.8 and the V1.10 parts were additions, none with a stock instance
in copy-manifest.json, so the two new parts are additions too; the schema accepts replacesStockIds only for real
copy-manifest object IDs. The retired cover and the superseded V1.10 parts are named in retiredParts and
deliveryContract.supersedes.
"""
import argparse, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REL = HERE.parent
SIM = REL.parents[2]
V19 = json.loads((SIM / 'guide/print/release-V1.9/manifest-V1.9.json').read_text())
PINNED = {  # back-plate layout F, 2026-10-14 (back-plate/layout-F/build_f.py output, mirrored for the XL4015 handedness)
    'rear_frame': 'dc9fcdaccee61641e20766fbf8ee8398df21f62f29b5af82a100be61cdb59234',
    'rear_lid': '5773e28d642889283a434eee40beef91b98f93280528f999a55f5e584bf2e671',
}
# Support: the Orange donor profiles already print tree(auto) support at a 30 degree threshold with
# bridge_no_support = 0 and support_on_build_plate_only = 0, so the rim-down frame's front-plate ceiling and cover flap and
# the cap's rounded edges and ears get tree support without any support override.
# Brim: none. The rim-down frame stands on a 1.2 mm wall ring (296.8 mm2) on a 64.1 x 87.0 mm footprint (tip angle about
# 71 deg) and the cap on its 2918 mm2 face; R1 adds a brim only below a 10 deg tip angle. The plate-wide 4 mm outer brim came
# from the V1.9 head cap (7.7 deg) and was carried forward; a 0.1 mm-gap brim on a thin wall is very hard to peel (Shawn,
# 2026-10-14). brim_type no_brim is set explicitly because the donor profiles default to auto_brim.
PROCESS_OVERRIDES = {'Orange_Bambu': {'brim_type': 'no_brim'},
                     'Orange_Elegoo': {'brim_type': 'no_brim'}}
PROCESS_OVERRIDE_REASON = (
    'Supports: no support override. The Orange donor profiles (12-REPAIR-V1-20261008/dual-printer/Orange_*_editable.3mf) '
    'already set enable_support 1, support_type tree(auto), support_threshold_angle 30, bridge_no_support 0 and '
    'support_on_build_plate_only 0, so the frame\'s front plate (a ceiling 12.1 mm above the bed inside the rim-down box) and '
    'the cover flap below the box floor get tree support, and the cap (outer face down) gets tree support under its rounded rear edges and screw ears; the native '
    'slices confirm it (review/Orange_*-review.json supportByRegion). The boss tips (PCB seats) sit under the ceiling and '
    'print on support: clean them flat before mounting the boards. Brim: rear_frame stands 21.6 mm tall on a 1.2 mm wall '
    'ring (296.8 mm2) spread over a 64.1 x 87.0 mm footprint, tip angle {frame_tip} degrees; the cap lies on its outer face ({lid_tip} '
    'degrees) (orientation-check.json). Neither needs a brim (guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md R1: a brim '
    'only below a 10 degree tip angle), so brim_type is no_brim on both machines; it is set explicitly because the donor '
    'profiles default to auto_brim. The plate-wide 4 mm outer brim carried since V1.9 (head cap, 7.7 degrees) is dropped: '
    'a 0.1 mm-gap brim on the frame\'s 1.2 mm wall ring is very hard to peel.')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p)
    assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.11.json')
    ap.add_argument('--frame-tip', default='n/a', help='rear_frame tip angle from orientation-check.json (text for the reason)')
    ap.add_argument('--lid-tip', default='n/a', help='rear_lid tip angle from orientation-check.json')
    a = ap.parse_args()
    rows = json.loads((HERE / 'rows.json').read_text())
    pose = json.loads((HERE / 'pose-check.json').read_text())
    assert pose['passed'], 'scripts/pose-check.json did not pass; run scripts/verify_poses.py'
    parts = []
    for r in rows:
        src = ref(r['path'])
        assert src['sha256'] == PINNED[r['key']], f'{r["key"]}: STL sha256 {src["sha256"]} differs from the pinned layout F {PINNED[r["key"]]}'
        pc = pose['parts'][r['key']]
        assert pc['passed'] and pc['worldSha256'] == src['sha256'], f'{r["key"]}: pose check is for other bytes'
        assert pc['flatContactMinimumMm2'] == r['flatContactMinimumMm2'] <= pc['bedContactMm2']
        parts.append(dict(
            key=r['key'], color=r['color'], quantity=int(r.get('quantity', 1)), decision=r['decision'],
            replacesStockIds=[str(x) for x in r['replacesStockIds']], path=src['path'], sha256=src['sha256'],
            sourceFrame=r.get('sourceFrame', 'robot frame (mm, x forward, y left, z up)'),
            sourceToPrint=r['sourceToPrint'], flatContact={'minimumAreaMm2': r['flatContactMinimumMm2']},
            poseOrigin=r.get('poseOrigin', ''), poseCheck=dict(ref(HERE / 'pose-check.json'), printStl=ref(pc['printStl']),
                                                              maxVertexDeviationMm=pc['maxVertexDeviationMm'], bedContactMm2=pc['bedContactMm2']),
            changeReason=r['changeReason'], incrementalEvidence=ref(r['incrementalEvidence']),
            evidenceAlso=[ref(x) for x in r.get('evidenceAlso', [])],
            supportBlockers=[dict(ref(b['path']), machines=b['machines'], reason=b['reason']) for b in r.get('supportBlockers', [])]))
    colors = [c for c in ('Yellow', 'White', 'Orange', 'Black') if any(p['color'] == c for p in parts)]
    assert colors == ['Orange'], colors
    m = dict(
        schemaVersion=1, releaseKind='incremental', version='V1.11', prototype=True,
        prototypeScope=('V1.11 Orange increment on top of the printed V1.9 set: the rear converter box, layout F '
                        '(guide/print/back-plate/layout-F/), printed as the frame and a lid. The frame replaces the printed V1.8 '
                        'rear pack cover and supersedes the V1.10 frame and lid (layout C revision 2), which should not be printed. '
                        'It carries two XL4015 step-down boards (7 V top tier, 5 V middle tier) and one Adafruit 5991 USB-C PD '
                        'trigger (bottom tier). Every other printed part stays; the printed V1.8 pack stays as built.'),
        knownFitBoundary=('Frame to pack: the four V1.8 cover screws (M2 x 6) at (-47, +-16.1, 26.0) and (-47, +-16.1, -36.5); the '
                          'frame goes on empty. Boards: 8 x M2 x 6 into the XL4015 bosses, 4 x M2 x 6 into the 5991 standoff bosses, '
                          'cap: two tongues under the top wall with teeth in the top-wall slots (slide on 1.2 mm low, lift) and 2 x M2 x 6 through the ears at (y -23.8, z -17.4) and (y +23.8, z -33.6); the lower cover screws sit in dia 4.4 driver lanes. HOME: frame to shells 1.04 / 1.175 mm, to the OpenRB 4.931 mm. Hip sweep (each hip '
                          'pitch HOME +-30 deg with hip roll +-10 deg, layout-F/hip_sweep.json): USB-C plug envelope to the left '
                          'upper leg 4.28 mm minimum, frame to the legs at least 6 mm, cap at least 6 mm, window loops at least 13.9 mm. XL4015 IN '
                          'ends face -y and OUT ends +y (kit photo and mesh); read the printed IN/OUT labels before wiring. The '
                          'tether hole in the V1.8 pack stays open and unused. Boss tips print on support: clean them flat.'),
        baselineStock=V19['baselineStock'], profiles=V19['profiles'],
        processOverrides=PROCESS_OVERRIDES,
        processOverrideReason=PROCESS_OVERRIDE_REASON.format(frame_tip=a.frame_tip, lid_tip=a.lid_tip),
        parts=parts,
        retiredParts=[dict(part='rear_pack_cover', printed='V1.8 (Black)', reason='replaced by the V1.11 rear_frame, which carries the same cover outline, holes and lip'),
                      dict(part='rear_frame (V1.10, layout C revision 2)', printed='V1.10 release (Orange)', reason='superseded by the V1.11 layout F rear_frame; do not print or fit'),
                      dict(part='rear_lid (V1.10, layout C revision 2)', printed='V1.10 release (Orange)', reason='superseded by the V1.11 layout F rear_lid; do not print or fit')],
        deliveryContract=dict(colors=colors, filesPerColor=2, fileCount=2 * len(colors),
                              baseline='printed V1.6 set with the V1.7, V1.8 and V1.9 reprints',
                              supersedes=['rear_pack_cover (printed V1.8)', 'release V1.10 (rear_frame and rear_lid, layout C revision 2)'],
                              status='INCREMENTAL_REPRINT'))
    assert sha(m['baselineStock']['path']) == m['baselineStock']['sha256'], 'baseline stock drift'
    for k, v in m['profiles'].items():
        assert sha(v['path']) == v['sha256'], f'profile drift {k}'
    a.out.write_text(json.dumps(m, indent=1))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p['color'], p['decision'], p['replacesStockIds']) for p in parts],
                          colors=colors, processOverrides=PROCESS_OVERRIDES)))


if __name__ == '__main__':
    main()
