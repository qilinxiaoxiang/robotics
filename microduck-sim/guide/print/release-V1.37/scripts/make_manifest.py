"""Write the V1.37 incremental release manifest (D-033, Shawn 2026-10-29: "出文件"): two capped jaw rings on one Black plate,
one to fit and one spare. The ring replaces the V1.6 mouth sliding ring, which fell off the right jaw boss: a dia 14 cup
2.1 mm tall, 1.5 mm bottom with a dia 1.6 pilot, no flange, held on the boss (cut back 2 mm by hand) by one M2 x 8 from
outside the jaw arm (print/jaw-ring-screw-20261029/build_jaw_ring.py, checks.json, DESIGN-CONTRACT.json).
Profiles, baseline stock and the delivery contract come from manifest-V1.36.json. Pose: closed end on the bed, sleeve up,
written as the print STL (identity); every surface faces up or is vertical, nothing needs support. Stock Black process.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import hashlib, json
from pathlib import Path
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent
V136 = PRINT / 'release-V1.36/manifest-V1.36.json'
CAD = PRINT / 'jaw-ring-screw-20261029'
GAP_MM = 10.0


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


def main():
    m = json.loads(V136.read_text())
    checks = json.loads((CAD / 'checks.json').read_text())
    assert checks['wallsOk'] and checks['envelope']['ok'] and checks['clearances']['jaw_frame_boss_cut']['ringSamplesInsideJaw'] == 0, checks
    stl = CAD / 'build/jaw_ring_capped-print.stl'
    k = trimesh.load(stl, force='mesh', process=False)
    assert abs(k.bounds[0, 2]) < 1e-6
    area = float(k.area_faces[np.max(np.abs(k.triangles[:, :, 2]), axis=1) <= .01].sum())
    size = (k.bounds[1] - k.bounds[0]).round(2).tolist(); src = ref(stl); c = checks
    row = dict(
        key='jaw_ring_capped', color='Black', quantity=2, decision='addition', replacesStockIds=[],
        path=src['path'], sha256=src['sha256'],
        sourceFrame='print frame: closed end on the bed, sleeve up (robot frame: x - 26.1, z - 118.62, -y - 37.5)',
        sourceToPrint=np.eye(4).tolist(), flatContact={'minimumAreaMm2': round(0.95 * area, 1)},
        poseName='closed end on the bed',
        poseOrigin=('Closed end on the bed, open sleeve up: the bottom is a flat disc on the bed and the sleeve wall is vertical, so '
                    'nothing needs support; the M2 pilot is vertical.'),
        poseCheck=dict(printStl=src, bedContactMm2=round(area, 2), printSizeMm=size, note='STL written in its print pose (identity)'),
        changeReason=(f'D-033 (Shawn 2026-10-29: "右下颚连接处的圈掉了 … 设计一个圆圈 通过螺丝固定在右下颚上", "能不能直接一个件搞定", '
                      f'"有螺丝固定就不用那个特别薄的挡板了吧"): one-piece capped ring, OD {c["part"]["outerDiameterMm"]}, bore '
                      f'{c["part"]["boreMm"]}, {c["part"]["lengthMm"]} mm tall, {c["walls"]["plateMm"]} mm bottom with a dia '
                      f'{c["part"]["pilotMm"]} pilot, no flange. On the boss cut back {c["bossCut"]["removedMm"]} mm it ends where the old '
                      f'ring ended (y {c["envelope"]["ringYmax"]}), so the jaw springs in with the usual bend; one M2 x 8 from outside the '
                      f'arm (hole drilled to 2.5) gives {c["screw"]["threadInPlateMm"]} mm of thread in the bottom. Clear of the lower '
                      f'shell {c["clearances"]["head_bottom"]["minDistanceMm"]} mm and the jaw support '
                      f'{c["clearances"]["jaw_support"]["minDistanceMm"]} mm, as the old sleeve. Two copies: one spare.'),
        supersedes='mouth_sliding_ring (V1.6 package, Black)',
        objectSettings={'brim_type': 'outer_only', 'brim_width': '5', 'brim_object_gap': '0.1'},
        objectSettingsReason=('the first V1.37 plate failed (Shawn 2026-10-29, IMG_7204): both 14 mm rings came off the textured plate after '
                              'the first layers without a brim (R1 default: tip angle over 10 deg, no brim); a 0.64 g part with 146 mm2 '
                              'of contact needs the 5 mm outer brim to stay down'),
        incrementalEvidence=ref(CAD / 'checks.json'),
        evidenceAlso=[ref(CAD / 'build_jaw_ring.py'), ref(CAD / 'DESIGN-CONTRACT.json')],
    )
    lo = k.bounds[0]; w = size[0]
    pl = []
    for i in range(2):
        x0 = 128.0 - (2 * w + GAP_MM) / 2 + i * (w + GAP_MM); y0 = 128.0 - size[1] / 2
        pl.append(dict(key='jaw_ring_capped', copy=i + 1, translation=[round(x0 - float(lo[0]), 4), round(y0 - float(lo[1]), 4), 0.0]))
    m.update(version='V1.37', parts=[row], placements={'Black': pl},
             processOverrides={'Black_Bambu': dict(slow_down_layer_time=['12'], slow_down_min_speed=['5', '5']),
                               'Black_Elegoo': dict(outer_wall_speed='35', inner_wall_speed='35', internal_solid_infill_speed='35',
                                                   top_surface_speed='35', sparse_infill_speed='35', gap_infill_speed='35')},
             processOverrideReason=('Black: each 0.1 mm layer of the two 14 mm rings took about 4 s at the donor speeds (their 4 s minimum), so the '
                                    'top of the first plate melted into a lump (Shawn 2026-10-29). Minimum layer time 12 s (slow down to 5 mm/s) '
                                    'on the X1C; Orca loads the Elegoo filament profile over the project, so there the wall and infill speeds drop to 35 mm/s instead (fan already at full below 80 s layers). Each layer then has time to set.'),
             retiredParts=[{'part': 'mouth_sliding_ring', 'printed': 'V1.6 (Black)',
                            'reason': 'replaced by the V1.37 capped jaw ring held by one M2 x 8 (D-033); the old ring fell off the right jaw boss'}],
             prototypeScope='V1.37: two capped jaw rings (one spare) on one Black plate.',
             knownFitBoundary=(f'Bore {c["part"]["boreMm"]} on the dia 10.0 boss and OD {c["part"]["outerDiameterMm"]} in the seat, as the old '
                               'ring; the pilot 1.6 for M2 TAP. The boss cut and the 2.5 drill are done by hand; printed sizes not measured.'))
    m.pop('deferred', None)
    m['deliveryContract'] = dict(m['deliveryContract'], colors=['Black'], filesPerColor=2, fileCount=2, baseline='printed releases through V1.36',
                                 status='INCREMENTAL_REPLACEMENT', supersedes=['mouth_sliding_ring of V1.6 (Black)'])
    (REL / 'manifest-V1.37.json').write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(dict(contact=round(area, 1), size=size, placements=pl)))


if __name__ == '__main__':
    main()
