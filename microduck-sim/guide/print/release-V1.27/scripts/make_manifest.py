"""Write the V1.27 incremental release manifest (13-RELEASE-PIPELINE schema 1, pipeline v2).

V1.27 reprints the right lower-leg link (the knee-to-ankle link of the right leg, stock community-32.stl, copy-manifest object
58) unchanged in black: Shawn 2026-10-22 found the printed one bent. The STL is the 10/1 print file in its printed pose (flat,
7.95 mm tall), so the row is the exact stock STL with an identity pose and a `damageReprint` reason. The side comes from the
guide's solids report (right_lower = 07_community-32.stl, module right-leg); community-30 is the left link and differs in shape.
Shawn asked for the Bambu X1C file only; the pipeline still slices both machines, and only the X1C file is handed over.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py [--out manifest-V1.27.json]
"""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import sys
import trimesh

HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
V120_PATH = PRINT / 'release-V1.20/manifest-V1.20.json'
V120_SHA = 'b912b3c7eea53f81b96ccf861f4f04cee46eeffe8bf42259f75b0a839b8ce171'
STL = SIM / 'build-pack-20260913/assembly/print-parts/community-32.stl'
STL_SHA = '92b8f80f1dba7adf0a8b24a80f691c7dacdd48dc77d42298c56661f87add2edc'   # copy-manifest object 58
SOLIDS = SIM / 'guide/content/interference-audit/solids-report.json'
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
WALL_REASON = ('stock community-32 as printed in the 10/1 batch, which served on the robot until it bent; '
               'printed before the 1.2 mm wall rule and reprinted unchanged')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    p = Path(p); assert p.is_file(), p
    return {'path': str(p.resolve()), 'sha256': sha(p)}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=REL / 'manifest-V1.27.json'); a = ap.parse_args()
    assert sha(V120_PATH) == V120_SHA, 'manifest-V1.20.json changed since V1.22 was set up'
    assert sha(STL) == STL_SHA, 'community-32.stl differs from the printed stock'
    side = next(p for p in json.loads(SOLIDS.read_text())['records'] if p['key'] == 'right_lower')
    assert side['module'] == 'right-leg' and side['source']['path'].endswith('07_community-32.stl'), side
    m = trimesh.load(STL, force='mesh', process=False); m.apply_translation([0, 0, -m.bounds[0, 2]])
    area = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    size = (m.bounds[1] - m.bounds[0]).round(2).tolist()
    # Every thin region of the stock link, each allowed only down to its own measured minimum.
    regs = [g for g in wall_check.check(m.copy(), (), 'lower_right')['regions'] if g['status'] == 'FAIL']
    allow = [dict(bbox=[[c - .05 for c in g['bbox'][0]], [c + .05 for c in g['bbox'][1]]], minMm=round(g['minMm'] - .005, 3), reason=WALL_REASON) for g in regs]
    evidence = REL / 'damage-evidence.json'
    evidence.write_text(json.dumps(dict(
        report='Shawn 2026-10-22: the right knee link of the MicroDuck looks bent; reprint it.',
        part='Right lower-leg link (knee servo to ankle servo, right leg)', stockObjectId='58', stl=ref(STL),
        sideSource=dict(ref(SOLIDS), key='right_lower', module=side['module'], sourcePath=side['source']['path']),
        colourSource='guide/print/colour-study-20261014/colour_as_built.json lower_right: Black, stock print, 10/1 batch'), indent=1))
    row = dict(
        key='lower_right', color='Black', quantity=1, decision='replacement', replacesStockIds=['58'],
        path=str(STL), sha256=STL_SHA, sourceFrame='10/1 print STL (already in its print pose)',
        sourceToPrint=np.eye(4).tolist(), flatContact={'minimumAreaMm2': round(0.95 * area, 1)},
        poseName='10/1 pose', poseOrigin=f'10/1 pose, flat, {size[2]} mm tall, {area:.1f} mm2 contact; the link printed and served in this pose.',
        poseCheck=dict(printStl=ref(STL), bedContactMm2=round(area, 2), printSizeMm=size, note='10/1 print STL dropped to the bed'),
        changeReason='Damage reprint: the printed right lower-leg link bent (Shawn 2026-10-22); stock geometry, same colour.',
        damageReprint='The printed right lower-leg link (community-32, 10/1 batch, black) is bent; same part, same colour.',
        supersedes='lower_right: the bent community-32 from the 10/1 batch',
        incrementalEvidence=ref(evidence), thinWallAllowances=allow)
    m120 = json.loads(V120_PATH.read_text())
    lo = m.bounds[0]
    m120['parts'] = [row]
    m120['placements'] = {'Black': [dict(key='lower_right', copy=1, translation=[round(128.0 - size[0] / 2 - float(lo[0]), 4), round(128.0 - size[1] / 2 - float(lo[1]), 4), 0.0])]}
    m120['processOverrides'] = {}
    m120['processOverrideReason'] = 'Stock profile (brims per object by the pipeline R1 rule or the manifest objectSettings).'
    m120['retiredParts'] = []
    m120['version'] = 'V1.27'
    m120['prototypeScope'] = 'V1.27 delta package: one Black plate with the right lower-leg link, reprinted unchanged because the printed one bent.'
    m120['knownFitBoundary'] = 'Same STL and pose as the 10/1 link that fitted; no new fit.'
    m120.pop('deferred', None)
    dc = m120['deliveryContract']
    dc.update(colors=['Black'], fileCount=2,
              baseline='printed V1.8 set and every later printed release through V1.25',
              supersedes=['the bent right lower-leg link (community-32, 10/1 batch)'], status='INCREMENTAL_REPRINT')
    a.out.write_text(json.dumps(m120, indent=1, ensure_ascii=False))
    print(json.dumps(dict(out=str(a.out), contact=round(area, 1), size=size, thin=[(g['minMm'], g['areaMm2']) for g in regs], placements=m120['placements'])))


if __name__ == '__main__':
    main()
