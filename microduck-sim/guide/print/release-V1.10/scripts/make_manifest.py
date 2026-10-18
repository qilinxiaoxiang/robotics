"""Write the V1.10 incremental release manifest (13-RELEASE-PIPELINE schema 1).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.10.json]

Rows come from rows.json next to this script: rear_frame and rear_lid (Orange), the two printed parts of the rear
converter box, layout C revision 2 (guide/print/back-plate/). The script fills in sha256 values, copies the V1.9
baseline stock and slicer profiles, checks both sources against the sha256 pinned below (the C2 build), checks that
scripts/pose-check.json (scripts/verify_poses.py) passed for these exact sources and poses, and checks every
referenced file.

The printed V1.8 rear_pack_cover was an addition in V1.8 (no stock instance in copy-manifest.json), so the two new
parts are additions too; the schema accepts replacesStockIds only for real copy-manifest object IDs. The retired cover
is named in deliveryContract.supersedes.
"""
import argparse, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REL = HERE.parent
SIM = REL.parents[2]
V19 = json.loads((SIM / 'guide/print/release-V1.9/manifest-V1.9.json').read_text())
PINNED = {  # back-plate layout C revision 2, 2026-10-14 (back-plate/build_rear_plate.py output)
    'rear_frame': '6cdd8a9974a977de59d994fcd1f0a9d3345b03f274aca27ed2ccc1a2bf3d81c3',
    'rear_lid': '400d3b29d0034c02bfc881024c23718f778aeefb1fce2f99cf76af30eb43605d',
}
# Support: the Orange donor profiles already print tree(auto) support at a 30 degree threshold with
# bridge_no_support = 0 and support_on_build_plate_only = 0, so the frame's top-wall bridge and lip get tree support
# and the flat lid gets none without any support override. Brim: rear_frame's tip angle is below 10 degrees in the
# V1.10 orientation check, so the V1.8/V1.9 Orange 4 mm outer brim stays (PRINT-ORIENTATION-PRACTICE.md R1).
PROCESS_OVERRIDES = {'Orange_Bambu': {'brim_type': 'outer_only', 'brim_width': '4'},
                     'Orange_Elegoo': {'brim_type': 'outer_only', 'brim_width': '4'}}
PROCESS_OVERRIDE_REASON = (
    'Supports: no support override. The Orange donor profiles (12-REPAIR-V1-20261008/dual-printer/Orange_*_editable.3mf) '
    'already set enable_support 1, support_type tree(auto), support_threshold_angle 30, bridge_no_support 0 and '
    'support_on_build_plate_only 0, so the frame\'s 61.7 x 18.9 mm top-wall bridge (supports stand inside the box on the '
    'bottom wall and come out through the open back) and the 7.5 mm lip underside (supports on the bed in front of the '
    'plate) get tree support, and the lid (no overhang) gets none; the native slices confirm it '
    '(review/Orange_*-review.json supportByRegion). Brim: rear_frame prints 90.5 mm tall on its 1339.7 mm2 bottom wall '
    'with a tip angle of {frame_tip} degrees (orientation-check.json), below the 10 degree line in '
    'guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md R1, so the 4 mm outer brim used for Orange in V1.8 and '
    'V1.9 stays (it also rings the 1.2 mm lid, tip angle {lid_tip} degrees, harmlessly).')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p)
    assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.10.json')
    ap.add_argument('--frame-tip', default='n/a', help='rear_frame tip angle from orientation-check.json (text for the reason)')
    ap.add_argument('--lid-tip', default='n/a', help='rear_lid tip angle from orientation-check.json')
    a = ap.parse_args()
    rows = json.loads((HERE / 'rows.json').read_text())
    pose = json.loads((HERE / 'pose-check.json').read_text())
    assert pose['passed'], 'scripts/pose-check.json did not pass; run scripts/verify_poses.py'
    parts = []
    for r in rows:
        src = ref(r['path'])
        assert src['sha256'] == PINNED[r['key']], f'{r["key"]}: STL sha256 {src["sha256"]} differs from the pinned C2 {PINNED[r["key"]]}'
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
        schemaVersion=1, releaseKind='incremental', version='V1.10', prototype=True,
        prototypeScope=('V1.10 Orange increment on top of the printed V1.9 set: the rear converter box (layout C revision 2, '
                        'guide/print/back-plate/), printed as the frame and a flat lid. The frame replaces the printed V1.8 '
                        'rear pack cover and carries two XL4015 step-down boards and one Adafruit 5991 USB-C PD trigger. '
                        'Every other printed part stays.'),
        knownFitBoundary=('Frame to pack: the four V1.8 cover screws (M2 x 6) at (-47, +-16.1, 26.0) and (-47, +-16.1, -36.5); the '
                          'frame goes on empty because the upper cover screws sit behind the boards. Boards: 8 x M2 x 6 into the '
                          'XL4015 bosses, 4 x M2 x 6 into the 5991 bosses; lid 2 x M2 x 6. Checked at HOME only (frame to shells '
                          '1.40 / 1.449 mm, raised top 7.414 mm to the shells); no walking-pose sweep of the legs against the box '
                          'or the USB-C plug has been run (back-plate/README.md open items). Read the XL4015 IN/OUT label before '
                          'mounting; trimmers are set with the lid off.'),
        baselineStock=V19['baselineStock'], profiles=V19['profiles'],
        processOverrides=PROCESS_OVERRIDES,
        processOverrideReason=PROCESS_OVERRIDE_REASON.format(frame_tip=a.frame_tip, lid_tip=a.lid_tip),
        parts=parts,
        retiredParts=[dict(part='rear_pack_cover', printed='V1.8 (Black)', reason='replaced by the V1.10 rear_frame, which carries the same cover outline, holes and lip')],
        deliveryContract=dict(colors=colors, filesPerColor=2, fileCount=2 * len(colors),
                              baseline='printed V1.6 set with the V1.7, V1.8 and V1.9 reprints',
                              supersedes=['rear_pack_cover (printed V1.8)'], status='INCREMENTAL_REPRINT'))
    assert sha(m['baselineStock']['path']) == m['baselineStock']['sha256'], 'baseline stock drift'
    for k, v in m['profiles'].items():
        assert sha(v['path']) == v['sha256'], f'profile drift {k}'
    a.out.write_text(json.dumps(m, indent=1))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p['color'], p['decision'], p['replacesStockIds']) for p in parts],
                          colors=colors, processOverrides=PROCESS_OVERRIDES)))


if __name__ == '__main__':
    main()
