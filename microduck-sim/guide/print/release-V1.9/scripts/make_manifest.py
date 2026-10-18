"""Write the V1.9 incremental release manifest (13-RELEASE-PIPELINE schema 1).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.9.json] [--skip KEY ...]

Rows come from rows.json next to this script: one entry per part with key, color, decision, replacesStockIds, source
path (robot frame unless stated), sourceToPrint, flatContact minimum, changeReason, supportBlockers and evidence. The
script fills in sha256 values, copies the V1.8 baseline stock and slicer profiles plus the Orange brim override, checks
every ext-v19 source against the sha256 recorded in ext-v19/manifest-ext-v19.json, and checks every referenced file.
"""
import argparse, hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REL = HERE.parent
SIM = REL.parents[2]
V18 = json.loads((SIM / 'guide/print/release-V1.8/manifest-V1.8.json').read_text())
EXT = json.loads((SIM / 'guide/print/ext-v19/manifest-ext-v19.json').read_text())
EXT_SHA = {p['key']: p['sha256'] for p in EXT['parts']}
PINNED = {'rear_pack': 'e2d58d22231e43690aa274925fc9c91146b4a7e7109247a269b6ffc72a9eba00'}   # 2026-10-13 rev 2: DFR lips and feet removed (OpenRB in and out from behind); rev 1 was e0311236...


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p)
    assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.9.json')
    ap.add_argument('--skip', action='append', default=[], help='leave this row out (repeatable)')
    a = ap.parse_args()
    rows = [r for r in json.loads((HERE / 'rows.json').read_text()) if r['key'] not in a.skip]
    parts = []
    sup = {r['key']: r.get('supersedes') for r in rows}
    for r in rows:
        src = ref(r['path'])
        expected = PINNED.get(r['key']) or EXT_SHA.get(r['key'])
        assert expected, f'{r["key"]}: no expected sha256 (not in ext-v19 manifest, not pinned)'
        assert src['sha256'] == expected, f'{r["key"]}: STL sha256 {src["sha256"]} differs from the expected {expected}'
        parts.append(dict(
            key=r['key'], color=r['color'], quantity=int(r.get('quantity', 1)), decision=r['decision'],
            replacesStockIds=[str(x) for x in r['replacesStockIds']], path=src['path'], sha256=src['sha256'],
            sourceFrame=r.get('sourceFrame', 'robot frame (mm, x forward, y left, z up)'),
            sourceToPrint=r['sourceToPrint'], flatContact={'minimumAreaMm2': r['flatContactMinimumMm2']},
            poseOrigin=r.get('poseOrigin', ''), changeReason=r['changeReason'],
            incrementalEvidence=ref(r['incrementalEvidence']),
            supportBlockers=[dict(ref(b['path']), machines=b['machines'], reason=b['reason']) for b in r.get('supportBlockers', [])]))
    colors = [c for c in ('Yellow', 'White', 'Orange', 'Black') if any(p['color'] == c for p in parts)]
    assert colors == ['Orange'], colors
    m = dict(
        schemaVersion=1, releaseKind='incremental', version='V1.9', prototype=True,
        prototypeScope=('V1.9 Orange increment on top of the printed V1.8 set: the rear electronics pack with the BNO085 rib and the shell '
                        'seat bars, the head cap for the neck-route and audio extension (speaker collar, amplifier posts, no rear notch), '
                        'the speaker retainer, and the four neck-bundle cable clips (torso, bracket, head, cap). Every other printed part '
                        'stays, including the V1.8 Black rear pack cover.'),
        knownFitBoundary=('BNO085: two M2 x 4 through the board into the pack rib at the bench, before pack-in. Shells: the printed V1.8 shells '
                          'rest on the pack bars (0.15/0.27 mm roof gap). Cap: same three closure screws as V1.8; E-pi-04 becomes M2 x 8 under the '
                          'cap clip; speaker retainer 2 x M2 x 6, amplifier 2 x M2 x 6. Clips: 2 mm tabs under S12-horn-025 (M2 x 8), S11-horn-040 '
                          '(M2 x 8), H-jaw_support-03 (M2.5 x 8) and E-pi-04. Physical checks remain: clip shapes are untested in print, '
                          'and the jaw pose-cap table does not yet model the clips and wires (ext-v19/README.md).'),
        baselineStock=V18['baselineStock'], profiles=V18['profiles'],
        processOverrides=V18['processOverrides'],
        processOverrideReason=('Head cap tip angle 7.7 degrees (ext-v19/checks/orientation-ext-v19.json) is below the 10 degree line in '
                               'guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md; 4 mm outer brim carried over from V1.8.'),
        parts=parts,
        deliveryContract=dict(colors=colors, filesPerColor=2, fileCount=2 * len(colors), baseline='printed V1.6 set with the V1.7 and V1.8 reprints',
                              supersedes=sorted({sup.get(p['key']) or f'{p["key"]} (printed V1.8)' for p in parts if p['decision'] == 'replacement'}),
                              status='INCREMENTAL_REPRINT'))
    assert sha(m['baselineStock']['path']) == m['baselineStock']['sha256'], 'baseline stock drift'
    for k, v in m['profiles'].items():
        assert sha(v['path']) == v['sha256'], f'profile drift {k}'
    a.out.write_text(json.dumps(m, indent=1))
    print(json.dumps(dict(out=str(a.out), parts=[(p['key'], p['color'], p['decision'], p['replacesStockIds']) for p in parts], colors=colors)))


if __name__ == '__main__':
    main()
