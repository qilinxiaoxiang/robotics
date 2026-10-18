#!/usr/bin/env python3
"""Assemble results.json for the MicroDuck V1.6 print-orientation study.

    /tmp/microduck-cad-venv/bin/python scripts/build_results.py

Inputs (all inside orientation-study/): evidence/check-v16-screen.json (orientation_check.py screen),
evidence/register-10-1.json (10/1 batch registration), slices/<key>/<slug>/readback-<Machine>.json and
seats-<Machine>.json (native slices), evidence/jaw-bearing-seat.json, evidence/support-maps/*.json and
candidates/verdicts.json (authored verdicts). Loads no meshes. Fails if any of the 13 parts lacks candidates, metrics,
a recommendation or evidence, or if a changed part lacks a native slice.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ACCESSED = '2026-10-09'

CRITERIA = [
    dict(id='R1', rule='Stable flat base: real flat contact, centre of mass well inside the first-layer hull, no part '
         'that leans on support or brim to stay up.',
         sources=[dict(url='https://wiki.bambulab.com/en/filament-acc/filament/print-quality/warping-falling-off-collapsing',
                       quote='Consider reorienting the model to lie flat.'),
                  dict(url='https://wiki.bambulab.com/en/software/bambu-studio/auto-orientation',
                       note='Auto orientation prefers a larger bottom area and a larger bottom convex hull (stability).'),
                  dict(url='https://wiki.bambulab.com/en/software/bambu-studio/auto-brim',
                       quote='A taller part with a smaller footprint usually needs a wider brim'),
                  dict(url='https://help.prusa3d.com/article/skirt-and-brim_133969', quote='use at least a 3 mm brim'),
                  dict(url='https://wiki.elegoo.com/en/troubleshooting/fdm-printer/edge-warping',
                       note='Lists small bottom contact area as a warping cause; brim first.')],
         inference='The tip-angle threshold (10 degrees) and the 0.01 mm contact rule are project choices; the contact '
                   'rule is the release pipeline flatContact check.'),
    dict(id='R2', rule='Functional faces off support: screw-head seats, bearing and sliding seats, PCB pads and mating '
         'faces should face up, sit on the bed, or be vertical walls.',
         sources=[dict(url='https://wiki.bambulab.com/en/software/bambu-studio/auto-orientation',
                       quote='supports can damage the interface surface more or less'),
                  dict(url='https://wiki.bambulab.com/en/software/bambu-studio/support',
                       note='Top Z distance and interface layers trade removal ease against surface quality.')],
         inference='Ranking a moving fit (sliding seat) above a static clamp seat, and treating a down-facing end '
                   'under 0.6 mm as bridged, are project inferences checked against native slices here.'),
    dict(id='R3', rule='Holes and bores that must be round or accurately pitched print with a vertical axis.',
         sources=[dict(url='https://wiki.bambulab.com/en/software/bambu-studio/manual/auto-circle-contour-compensation',
                       quote='semicircles or circles in the vertical direction will not be compensated'),
                  dict(url='https://www.hubs.com/knowledge-base/how-does-part-orientation-affect-3d-print/',
                       note='Non-official: vertical-axis cylinders are smooth and accurate; horizontal ones facet.'),
                  dict(url='https://www.makerverse.com/resources/the-fused-deposition-modeling-fdm-design-guide/',
                       note='Non-official: horizontal holes step and turn slightly elliptical.')],
         inference='No official slicer or printer source covers horizontal-hole droop or teardrop holes.'),
    dict(id='R4', rule='Do not make layers carry the main load: keep bending and tension of thin arms, pins and clips '
         'in the layer plane when the load is significant.',
         sources=[dict(url='https://wiki.bambulab.com/en/knowledge-sharing/common-print-quality-problem',
                       quote='avoid having the layers bear the main load'),
                  dict(url='https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135',
                       quote='FFF prints are stronger in one direction than another'),
                  dict(url='https://www.hubs.com/knowledge-base/how-does-part-orientation-affect-3d-print/',
                       quote='Z tension increases the risk of delamination and fracture.')],
         inference='Whether a MicroDuck load is significant is judged per part (for example the neck ears, about '
                   '1.5 MPa estimated); no printed strength test was run.'),
    dict(id='R5', rule='Cosmetic faces and elephant foot: the bed face is flat but flared and takes the plate texture; '
         'supported faces print rough.',
         sources=[dict(url='https://wiki.bambulab.com/en/software/bambu-studio/parameter/elephant-foot',
                       quote='the flared base directly affects fit'),
                  dict(url='https://wiki.bambulab.com/en/filament-acc/acc/plates',
                       quote='Adds a unique textured finish to the bottom surface of printed parts.'),
                  dict(url='https://help.prusa3d.com/article/elephant-foot-compensation_114487',
                       note='About 0.2 mm for a 0.4 mm nozzle.')],
         inference=None),
    dict(id='R6', rule='Support volume, removal access and overhangs: prefer poses with less support, none trapped '
         'in cavities or hole cores; slopes under 45 degrees from the bed need support (profile threshold 30 degrees).',
         sources=[dict(url='https://wiki.bambulab.com/en/software/bambu-studio/support',
                       quote='The default threshold angle is 30 degrees.'),
                  dict(url='https://wiki.bambulab.com/en/filament-acc/filament/print-quality/overhang',
                       quote='smaller than 45°, it is recommended to add supports'),
                  dict(url='https://help.prusa3d.com/article/support-material_1698',
                       note='Reorient or split the model to reduce supports.')],
         inference=None),
    dict(id='R7', rule='Height, time and filament decide only between poses that tie on R1-R6.',
         sources=[dict(url='https://www.hubs.com/knowledge-base/how-does-part-orientation-affect-3d-print/',
                       note='Non-official: layer count scales with height.')],
         inference='No official FDM source gives a numeric orientation-to-time rule; native slice ETA is the measure.'),
]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads((HERE / p).read_text())


def main():
    screen = load('evidence/check-v16-screen.json')
    reg = load('evidence/register-10-1.json')
    verdicts = load('candidates/verdicts.json')['parts']
    jaw = load('evidence/jaw-bearing-seat.json')
    reg_rows = {r['key']: r for r in (reg['rows'] if isinstance(reg, dict) and 'rows' in reg else reg)}
    keep_cols = ('name', 'origin', 'sameAs', 'rank', 'heightMm', 'contactMm2', 'firstLayerSectionMm2', 'tipAngleDeg',
                 'overhang45Mm2', 'overhang60Mm2', 'supportProxyMm3', 'supportOnModelMm2', 'holesVertical',
                 'holesInclined', 'holesHorizontal', 'holeEndsFacingDown', 'bossFacesFacingDown', 'pinsVertical',
                 'pinsHorizontal', 'penalty', 'penaltyTerms', 'bedFacingSourceDir', 'sourceToPrint')
    parts, problems = [], []
    for p in screen['parts']:
        key = p['key']
        slices = []
        for d in sorted((HERE / 'slices' / key).glob('*')):
            for rb in sorted(d.glob('readback-*.json')):
                if rb.name.endswith('-resource.json'):
                    continue
                r = json.loads(rb.read_text())
                seats_p = d / rb.name.replace('readback-', 'seats-')
                s = json.loads(seats_p.read_text()) if seats_p.exists() else {}
                man = json.loads((d / 'manifest.json').read_text())
                slices.append(dict(slug=d.name, poseName=man['prototypeScope'].split("posed as '")[-1].rstrip("'."),
                                   machine=r['machine'], etaMinutes=r['etaMinutes'], totalGrams=r['headerGrams'],
                                   supportGrams=r['supportGrams'], gramsByFeature=r['gramsByFeature'],
                                   layers=r['layers'], layerHeight=r['layerHeight'],
                                   firstLayerModelMm2=[round(x['model_area_mm2'], 1) for x in r['firstLayer']],
                                   supportUnderDownHoleEndsMm=s.get('supportUnderDownEndsMm'),
                                   supportUnderDownBossFacesMm=s.get('supportUnderDownBossFacesMm'),
                                   supportInHoleCoresMm=s.get('supportInHoleCoresMm'),
                                   archive=r['archive'], readback=str(rb.relative_to(HERE))))
        maps = {m.stem: json.loads(m.read_text()) for m in sorted((HERE / 'evidence/support-maps').glob(f'{key}-*.json'))
                if not m.stem.endswith('-resource')}
        v = verdicts.get(key)
        row = dict(key=key, color=p['color'], source=p['source'], features=p['features'], flags=p['flags'],
                   candidates=[{k: c.get(k) for k in keep_cols} for c in sorted(p['candidates'], key=lambda c: c['rank'])],
                   batch10_1=({k: reg_rows[key].get(k) for k in ('accepted', 'stockCopy', 'stockExtentMm', 'newToOldMm', 'oldToNewMm')}
                              if key in reg_rows else None),
                   nativeSlices=slices, supportMaps=maps or None, verdict=v)
        if key == 'jaw_support_original':
            row['seatSupport'] = jaw['rows']
        parts.append(row)
        if not p['candidates'] or len(p['candidates']) < 2:
            problems.append(f'{key}: fewer than two candidates')
        if not v or v.get('recommendation') not in ('keep', 'change'):
            problems.append(f'{key}: no recommendation')
        if not slices:
            problems.append(f'{key}: no native slice')
        if v and v['recommendation'] == 'change' and not any(s['slug'] != 'current' for s in slices):
            problems.append(f'{key}: changed without a native slice of the new pose')
        for e in (v or {}).get('evidence', []):
            if not (HERE / e).exists():
                problems.append(f'{key}: evidence path missing: {e}')
    if len(parts) != 13:
        problems.append(f'expected 13 parts, found {len(parts)}')
    res = dict(
        study='MicroDuck V1.6 print orientation study', date=ACCESSED,
        manifest=screen['manifest'], manifestSha256=screen['manifestSha256'],
        scope='Read-only study. No release, sliced delivery, Downloads or build-pack file was changed. Native slices are '
              'single-part STUDY manifests through the unmodified 13-RELEASE-PIPELINE (BambuStudio 02.08.02.61, '
              'OrcaSlicer 2.4.2 for Elegoo), each run under run_bounded_cad.py.',
        summary=dict(keep=sorted(k for k, v in verdicts.items() if v['recommendation'] == 'keep'),
                     change=sorted(k for k, v in verdicts.items() if v['recommendation'] == 'change'),
                     nativeSlices=sum(len(p['nativeSlices']) for p in parts)),
        criteria=[dict(c, sources=[dict(s, accessed=ACCESSED) for s in c['sources']]) for c in CRITERIA],
        sourceGaps=['No official Bambu, Prusa, Orca or Elegoo page covers horizontal-hole droop or teardrop holes.',
                    'No official source covers screw-boss or thread orientation.',
                    'Elegoo publishes no orientation guidance.',
                    'No official numeric rule links orientation to print time.'],
        checkerPenaltyWeights=screen['penaltyWeights'],
        knownCheckerLimits=['It does not know which curved faces are sliding or bearing fits (jaw support flip screens '
                            'best but puts the sliding seat on support).',
                            'Penalty weights are heuristic; the screen orders candidates for slicing and review only.'],
        acceptance=dict(problems=problems, passed=not problems),
        inputs={str(Path(f)): sha(HERE / f) for f in ('evidence/check-v16-screen.json', 'evidence/register-10-1.json',
                                                      'candidates/verdicts.json', 'evidence/jaw-bearing-seat.json',
                                                      'orientation_check.py')},
        parts=parts)
    (HERE / 'results.json').write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n')
    print('parts', len(parts), 'slices', res['summary']['nativeSlices'], 'keep', len(res['summary']['keep']),
          'change', res['summary']['change'], 'problems', problems)
    if problems:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
