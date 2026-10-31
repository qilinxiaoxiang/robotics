"""Write the V1.39 incremental release manifest (Shawn 2026-10-31: backpack swaps by Dual Lock on a printed back plate for
the OpenRB pack, "就这样吧"): one Orange plate with the Dual Lock back plate. The plate has the V1.8 rear pack cover outline,
3 mm thick with no lip and no counterbores, and stays screwed to the four pack posts with the same M2 x 6; both
backpacks stick to its rear face (back-plate/duallock-plate-20261031/, DESIGN-CONTRACT.json). The row follows the V1.8
rear_pack_cover row (same face on the bed: the outer face, here the Dual Lock face x -48). Profiles, baseline stock and the
delivery contract come from manifest-V1.38.json.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import copy, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V138 = PRINT / 'release-V1.38/manifest-V1.38.json'
V18 = PRINT / 'release-V1.8/manifest-V1.8.json'
DP = PRINT / 'back-plate/duallock-plate-20261031'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


def printed(path, T):
    m = trimesh.load(path, force='mesh', process=False)
    m.apply_transform(np.array(T, float)); m.apply_translation([0, 0, -m.bounds[0, 2]])
    area = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    return area, (m.bounds[1] - m.bounds[0]).round(2).tolist(), m.bounds[0]


def main():
    m = json.loads(V138.read_text())
    row = copy.deepcopy([p for p in json.loads(V18.read_text())['parts'] if p['key'] == 'rear_pack_cover'][0])
    b = json.loads((DP / 'build/build.json').read_text())
    assert b['watertight'] and b['bodies'] == 1, b
    assert all(isinstance(v, dict) and v['overlap_mm3'] <= 0.01 for v in b['fit'].values()), b['fit']
    world = DP / 'build/duallock_plate-world.stl'
    T = b['source_to_print']
    area, size, lo = printed(world, T)
    assert area >= 2200, area
    row.update(
        key='duallock_plate', color='Orange', quantity=1, decision='addition', replacesStockIds=[],
        path=ref(world)['path'], sha256=sha(world), sourceToPrint=T, flatContact={'minimumAreaMm2': 2200},
        poseOrigin=('as the V1.8 rear_pack_cover: the outer face on the bed (robot x -48 becomes print z 0, robot y print x); '
                    f'{area:.1f} mm2 bed contact, {size[2]:.1f} mm tall, no support'),
        changeReason=('Shawn 2026-10-31: swapping the battery backpack and the charger box on the OpenRB pack takes too long, so '
                      'they stick on with Dual Lock (the two narrow strips in hand) and a printed back plate carries it. The plate '
                      'has the V1.8 pack cover outline (|y| <= 18.6, z -44..29.5; no wings, Shawn: "为什么要两个翅膀 好丑哦"), is 3 mm '
                      'thick (the same four M2 x 6 go through with 3 mm of thread in the posts; their heads stand outside the Dual Lock area), has no lip, and a top notch '
                      '(|y| <= 13.5, z 27 up) for the charger box\'s old front lip. Both backpacks print unchanged and sit about 8.7 mm '
                      'further back (3 mm plate plus the Dual Lock). Fit at rest: no overlap; nearest parts the shells 1.4 / 1.9 mm.'),
        poseCheck=dict(printStl=ref(DP / 'build/duallock_plate-print.stl'), bedContactMm2=round(area, 2), printSizeMm=size),
        incrementalEvidence=ref(DP / 'build/build.json'),
        evidenceAlso=[ref(DP / 'build_plate.py'), ref(DP / 'DESIGN-CONTRACT.json'), ref(DP / 'concept/backplate-concept-v3.png')],
        supportBlockers=[])
    for k in ('supersedes', 'thinWallAllowances'):
        row.pop(k, None)
    pl = [dict(key='duallock_plate', copy=1, translation=[round(128.0 - size[0] / 2 - float(lo[0]), 4), round(128.0 - size[1] / 2 - float(lo[1]), 4), 0.0])]
    m.update(version='V1.39', parts=[row], placements={'Orange': pl}, processOverrides={},
             processOverrideReason='No process overrides: the Orange profile; a flat 3 mm plate needs no support or brim.',
             retiredParts=[],
             prototypeScope='V1.39: the Dual Lock back plate for the OpenRB rear pack on one Orange plate.',
             knownFitBoundary=('Plate front face on the pack posts at x -45; the Dual Lock thickness (about 5.7 mm for 3M SJ3550-class, '
                               'not measured) sets how far the backpacks move back. Printed sizes not measured.'))
    m.pop('deferred', None)
    m['deliveryContract'] = dict(m['deliveryContract'], colors=['Orange'], filesPerColor=2, fileCount=2, baseline='printed releases through V1.38',
                                 status='INCREMENTAL_ADDITION', supersedes=[])
    (REL / 'manifest-V1.39.json').write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(contact=round(area, 1), size=size, placements=pl)))


if __name__ == '__main__':
    main()
