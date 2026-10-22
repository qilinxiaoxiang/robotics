"""Write the V1.28 incremental release manifest: both lower-leg links in one piece with the V1.22 ankle sleeve printed on
(print/link-sleeve-20261022/make_link.py), black, in the 10/1 print pose of the stock links. Replaces stock objects 60
(left, community-30) and 58 (right, community-32) and the two V1.22 sleeves; supersedes the unprinted V1.27.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
V120 = PRINT / 'release-V1.20/manifest-V1.20.json'; LS = PRINT / 'link-sleeve-20261022'
STOCK_ID = dict(left='60', right='58')
WALL_REASON = ('thin walls of the stock 10/1 link (community-30/32), kept unchanged; the two beside the boss lose up to 0.08 mm '
               'where the sleeve disc meets them (link-sleeve-20261022)')


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


m = json.loads(V120.read_text()); parts = []; pl = []
check = json.loads((LS / 'link-check.json').read_text())
for i, side in enumerate(('left', 'right')):
    stl = Path(check['sides'][side]['files']['print']); assert sha(stl) == check['sides'][side]['files']['printSha256']
    k = trimesh.load(stl, force='mesh', process=False); k.apply_translation([0, 0, -k.bounds[0, 2]])
    area = float(k.area_faces[np.max(np.abs(k.triangles[:, :, 2]), axis=1) <= .01].sum()); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
    regs = [g for g in wall_check.check(k.copy(), (), side)['regions'] if g['status'] == 'FAIL']
    allow = [dict(bbox=[[c - .05 for c in g['bbox'][0]], [c + .05 for c in g['bbox'][1]]], minMm=round(g['minMm'] - .005, 3), reason=WALL_REASON) for g in regs]
    key = f'lower_{side}'
    parts.append(dict(key=key, color='Black', quantity=1, decision='replacement', replacesStockIds=[STOCK_ID[side]],
        path=str(stl), sha256=sha(stl), sourceFrame='10/1 print frame of the stock link', sourceToPrint=np.eye(4).tolist(),
        flatContact={'minimumAreaMm2': round(.95 * area, 1)}, poseName='10/1 pose',
        poseOrigin=f'10/1 pose of the stock link, flat, {size[2]} mm tall, {area:.1f} mm2 contact.',
        poseCheck=dict(printStl=ref(stl), bedContactMm2=round(area, 2), printSizeMm=size, note='10/1 print frame dropped to the bed'),
        changeReason=('One-piece lower-leg link: the stock link with the V1.22 ankle sleeve (OD 14.6, 2.8 wide) printed on its 10 mm boss '
                      '(Shawn 2026-10-22); same seated contacts and assembly paths as link + sleeve (link-check.json).'),
        supersedes=f'{key}: the 10/1 link and the V1.22 ankle sleeve on it', incrementalEvidence=ref(LS / 'link-check.json'),
        thinWallAllowances=allow))
    pl.append(dict(key=key, copy=1, translation=[round(103.0 + 50 * i - (k.bounds[0, 0] + k.bounds[1, 0]) / 2, 4), round(128.0 - (k.bounds[0, 1] + k.bounds[1, 1]) / 2, 4), 0.0]))
m.update(parts=parts, placements={'Black': pl}, processOverrides={}, retiredParts=[], version='V1.28',
         processOverrideReason='Stock profile (brims per object by the pipeline R1 rule or the manifest objectSettings).',
         prototypeScope='V1.28 delta package: one Black plate with the left and right one-piece lower-leg links (sleeve printed on). Supersedes the unprinted V1.27.',
         knownFitBoundary='The sleeve ring keeps the V1.22 sleeve outer size, about 0.4 mm diametral running clearance in the inner half; printed size not measured.')
m.pop('deferred', None)
m['deliveryContract'].update(colors=['Black'], fileCount=2, baseline='printed releases through V1.25', status='INCREMENTAL_REPRINT',
                             supersedes=['the two V1.22 black ankle sleeves', 'the unprinted V1.27 right link'])
(REL / 'manifest-V1.28.json').write_text(json.dumps(m, indent=1, ensure_ascii=False)); print('ok', [p['key'] for p in parts], pl)
