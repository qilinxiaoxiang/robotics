"""Write the V1.9 incremental release manifest (13-RELEASE-PIPELINE schema 1): one Black plate that replaces the V1.8
Black plate. It carries the two V1.8 Black parts unchanged (eye trim, rear pack cover), the 4.9 mm neck pitch ring and
two optional shims (1 mm and 2 mm) that stack under it. V1.8 Yellow, White and Orange stay as released.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py

Profiles, process overrides and the baseline stock come from manifest-V1.8.json. The ring prints flat, as the 10/1
4 mm ring did (plate-05/17_community-102.stl lies with its axis on z).
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REL = HERE.parent
SIM = REL.parents[2]
V18 = json.loads((SIM / 'guide/print/release-V1.8/manifest-V1.8.json').read_text())
RING = SIM / 'guide/print/world/neck_pitch_ring.stl'
EVIDENCE = SIM / 'guide/print/neck-ring/ring-audit.json'
SHIMS = SIM / 'guide/print/neck-ring/shims.json'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p)
    assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def main():
    src = ref(RING)
    part = dict(
        key='neck_pitch_ring', color='Black', quantity=1, decision='replacement', replacesStockIds=['96'],
        path=src['path'], sha256=src['sha256'], sourceFrame='robot frame (mm, x forward, y left, z up)',
        # Robot frame already has the ring axis on z; centre it and put its lower face on the bed.
        sourceToPrint=[[1, 0, 0, -26.0], [0, 1, 0, 0.0], [0, 0, 1, -99.2146], [0, 0, 0, 1]],
        flatContact={'minimumAreaMm2': 100},
        poseOrigin='Flat, axis vertical, as the 10/1 4 mm ring (plate-05/17_community-102.stl). Bed face is the chamfered lower face, about 133 mm2.',
        changeReason=('Neck pitch ring lengthened from 4.0 to 4.9 mm. In the assembled model the 4 mm ring sat on the pitch bracket '
                      'shoulder with its top face 0.91 mm below the ID13 case and nothing around its outside, so it floated and '
                      'carried no load. At 4.9 mm it touches both faces, like the working hip-yaw rings. ID 16.4 and OD 22 unchanged '
                      '(print/neck-ring/thicken_ring.py).'),
        incrementalEvidence=ref(EVIDENCE), supportBlockers=[])
    shims = []
    for t in (1, 2):
        s = ref(SIM / f'guide/print/neck-ring/shim_{t}mm.stl')
        shims.append(dict(
            key=f'neck_ring_shim_{t}mm', color='Black', quantity=1, decision='addition', replacesStockIds=[],
            path=s['path'], sha256=s['sha256'], sourceFrame='print frame (mm, axis z, lower face on z 0)',
            sourceToPrint=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
            flatContact={'minimumAreaMm2': 100}, poseOrigin='Flat, axis vertical, like the ring.',
            changeReason=(f'Optional {t} mm shim with the ring bore (16.4 mm) and outside (22 mm). It stacks on the 18 mm '
                          'shoulder under the 4.9 mm ring when the printed stack still leaves a gap under ID13 '
                          '(print/neck-ring/make_shims.py).'),
            incrementalEvidence=ref(SHIMS), supportBlockers=[]))
    v18_black = [dict(p) for p in V18['parts'] if p['color'] == 'Black']
    assert sorted(p['key'] for p in v18_black) == ['eye_trim', 'rear_pack_cover'], [p['key'] for p in v18_black]
    for p in v18_black:
        assert sha(p['path']) == p['sha256'], f'V1.8 source drift {p["key"]}'
        # The 2026-10-12 audit rerun for the ring regenerated v18-audit.json and pack-audit.json; both still pass these
        # parts (eye trim: only the intended 0.001 mm push fit into the face; cover: no overlaps), so bind the current files.
        p['incrementalEvidence'] = ref(p['incrementalEvidence']['path'])
    m = dict(
        schemaVersion=1, releaseKind='incremental', version='V1.9', prototype=True,
        prototypeScope='V1.9 Black plate, printed instead of the V1.8 Black plate: the V1.8 eye trim and rear pack cover (unchanged), the 4.9 mm neck pitch ring that replaces the 4 mm ring, and optional 1 mm and 2 mm shims for it. V1.8 Yellow, White and Orange stay as released.',
        knownFitBoundary='The ring must be pinched between the pitch bracket and the ID13 case without stopping ID13 from turning. Physical check: no up-down rattle after the four horn screws are in, and ID13 turns by hand.',
        baselineStock=V18['baselineStock'], profiles=V18['profiles'],
        processOverrides=V18.get('processOverrides', {}), processOverrideReason=V18.get('processOverrideReason', ''),
        parts=v18_black + [part] + shims,
        deliveryContract=dict(colors=['Black'], filesPerColor=2, fileCount=2, baseline='printed V1.6 set with the V1.7 and V1.8 reprints',
                              supersedes=['V1.8 Black plate (eye trim, rear pack cover)', '4 mm neck pitch ring (10/1 batch, stock object 96)'], status='INCREMENTAL_REPRINT'))
    assert sha(m['baselineStock']['path']) == m['baselineStock']['sha256'], 'baseline stock drift'
    for k, v in m['profiles'].items():
        assert sha(v['path']) == v['sha256'], f'profile drift {k}'
    out = REL / 'manifest-V1.9.json'
    out.write_text(json.dumps(m, indent=1))
    print(out)


if __name__ == '__main__':
    main()
