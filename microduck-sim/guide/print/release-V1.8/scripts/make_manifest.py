"""Write the V1.8 incremental release manifest (13-RELEASE-PIPELINE schema 1).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--head-only] [--out manifest-V1.8.json]

Rows come from rows.json next to this script: one entry per part with key, color, decision, replacesStockIds, source
path (robot frame unless stated), sourceToPrint, flatContact minimum, changeReason, supportBlockers and evidence. The
script fills in sha256 values, copies the V1.7 slicer profiles and brim override, and checks every referenced file.
"""
import argparse, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REL = HERE.parent
SIM = REL.parents[2]
V17 = json.loads((SIM / 'guide/print/release-V1.7/manifest-V1.7.json').read_text())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p)
    assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--head-only', action='store_true')
    ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.8.json')
    a = ap.parse_args()
    rows = json.loads((HERE / 'rows.json').read_text())
    if a.head_only:
        rows = [r for r in rows if r['group'] == 'head']
    parts = []
    sup = {r['key']: r.get('supersedes') for r in rows}
    for r in rows:
        src = ref(r['path'])
        parts.append(dict(
            key=r['key'], color=r['color'], quantity=int(r.get('quantity', 1)), decision=r['decision'],
            replacesStockIds=[str(x) for x in r['replacesStockIds']], path=src['path'], sha256=src['sha256'],
            sourceFrame=r.get('sourceFrame', 'robot frame (mm, x forward, y left, z up)'),
            sourceToPrint=r['sourceToPrint'], flatContact={'minimumAreaMm2': r['flatContactMinimumMm2']},
            poseOrigin=r.get('poseOrigin', ''), changeReason=r['changeReason'],
            incrementalEvidence=ref(r['incrementalEvidence']),
            supportBlockers=[dict(ref(b['path']), machines=b['machines'], reason=b['reason']) for b in r.get('supportBlockers', [])]))
    colors = [c for c in ('Yellow', 'White', 'Orange', 'Black') if any(p['color'] == c for p in parts)]
    m = dict(
        schemaVersion=1, releaseKind='incremental', version='V1.8', prototype=True,
        prototypeScope=('V1.8 head and torso rebuild on top of the printed V1.6/V1.7 set: White face plate with direct camera screws, '
                        'Yellow lower head shell without the beak-roof window and with the upper lip, Yellow jaw frame with the lower lip, Orange head cap with the Pi rails 1 mm higher, Black eye '
                        'trim with the two camera screw pilots' + ('' if a.head_only else ', plus the Orange rear electronics pack and its Black cover that replace the power '
                        'support, OpenRB tray, fuse bank, regulator insert and IMU clamp/cover, and the Black 4.9 mm neck pitch ring with '
                        'optional 1 mm and 2 mm shims') + '. Every other printed part stays.'),
        knownFitBoundary=('Camera: two M2 x 8 TAP screws from behind the board into the eye-trim pilots; the side holes sit on the face pegs. '
                          'Pi: three M2 x 6 and one M2 x 4 (E-pi-02) into the cap rails as in V1.7, seats 1 mm higher. Physical checks remain: '
                          'ribbon dressing at the camera connector, cap closing with the plugged jumper housings, and the pack slide-in behind the hip-yaw motors.'),
        baselineStock=V17['baselineStock'], profiles=V17['profiles'],
        processOverrides=V17['processOverrides'], processOverrideReason=V17['processOverrideReason'],
        parts=parts,
        deliveryContract=dict(colors=colors, filesPerColor=2, fileCount=2 * len(colors), baseline='printed V1.6 set with the V1.7 reprints',
                              supersedes=sorted({sup.get(p['key']) or f'{p["key"]} (printed V1.6/V1.7)' for p in parts if p['decision'] == 'replacement'}),
                              status='INCREMENTAL_REPRINT'))
    assert sha(m['baselineStock']['path']) == m['baselineStock']['sha256'], 'baseline stock drift'
    for k, v in m['profiles'].items():
        assert sha(v['path']) == v['sha256'], f'profile drift {k}'
    a.out.write_text(json.dumps(m, indent=1))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p['color'], p['decision'], p['replacesStockIds']) for p in parts], colors=colors)))


if __name__ == '__main__':
    main()
