#!/usr/bin/env python3
"""Assemble poses.json from the screen, the native slices (readback-*.json, faces-*.json, pose.json, preparation.json)
and decisions.json (the chosen slug per key with the written reasons). Fails if a chosen pose lacks a slice on either
machine. Read-only on the slices.
    /tmp/microduck-cad-venv/bin/python build_poses.py
"""
import hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; POSES = HERE.parent
MACHINES = ['Bambu', 'Elegoo']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(POSES))


def summarise(key, slug):
    run = POSES / 'slices' / key / slug
    pose = json.loads((run / 'pose.json').read_text()); prep = json.loads((run / 'run/preparation.json').read_text()); part = prep['parts'][0]
    per = {}; faces = {}; runs = [rel(run / 'manifest.json'), rel(run / 'run/preparation.json'), rel(run / 'prepare.log'), rel(run / 'prepare-resource.json')]
    for mc in MACHINES:
        rb = json.loads((run / f'readback-{mc}.json').read_text()); fc = json.loads((run / f'faces-{mc}.json').read_text())
        res = json.loads((run / f"run/native/{part['color']}_{mc}/result.json").read_text())
        fl = rb['firstLayer'][0]
        per[mc] = dict(etaMinutes=rb['etaMinutes'], totalGrams=rb['headerGrams'], supportGrams=rb['supportGrams'], layers=rb['layers'],
                       supportExtrusionMm=fc['supportExtrusionTotalMm'], supportInterfaceMm=fc['supportInterfaceMm'],
                       firstLayerModelAreaMm2=round(fl['model_area_mm2'], 1), firstLayerIslands=fl['modelIslands'], firstLayerSupportAreaMm2=round(fl['support_area_mm2'], 1),
                       brim=fc['brim']['objects'][f'{key}_1'], brimReviewPassed=fc['brim']['passed'], supportInsideCavitiesMm=fc['supportInsideCavitiesMm'],
                       firstThreeLayersByFeatureMm=fc['firstThreeLayersByFeatureMm'], tongueModelToolpathMm=fc['tongueModelToolpathMm'],
                       nativeArchive={'path': res['archive']['path'], 'sha256': res['archive']['sha256']}, gcodeSha256=res['gcodeSha256'])
        runs += [rel(run / f'slice-{mc}.log'), rel(run / f'slice-{mc}-resource.json'), rel(run / f'readback-{mc}.log'), rel(run / f'readback-{mc}.json'),
                 rel(run / f'faces-{mc}.log'), rel(run / f'faces-{mc}.json')]
        for name, s in fc['faceSets'].items():
            f = faces.setdefault(name, dict(must=s['must'], meaning=s['meaning'], areaMm2=s['areaMm2'], downMm2=s['downMm2'], upMm2=s['upMm2'], sideMm2=s['sideMm2'],
                                             onBedMm2=s['onBedMm2'], printZMm=s['printZMm'], restsOnSupportMm2={}, nearSupportMm2={}, supportInsideMm={}))
            f['restsOnSupportMm2'][mc] = s['touchedDownMm2']; f['nearSupportMm2'][mc] = s['touchedMm2']
            if 'supportInsideMm' in s: f['supportInsideMm'][mc] = s['supportInsideMm']
    for f in faces.values():
        f['clean'] = all(v == 0 for v in f['restsOnSupportMm2'].values()) and all(v == 0 for v in f['supportInsideMm'].values())
    return dict(slug=slug, poseName=pose['name'], screenCandidate=pose['candidate'], sourceToPrint=pose['localToPrint'],
                bedContactMm2=round(part['flatContactAreaMm2'], 2), heightMm=pose['heightMm'], footprintMm=pose['footprintMm'],
                tipAngleDeg=part['tipAngleDeg'], objectSettings=part['objectSettings'], objectSettingsSource=part['objectSettingsSource'],
                perMachine=per, functionalFaces=faces, runs=runs)


def main():
    dec = json.loads((POSES / 'decisions.json').read_text())
    screen = json.loads((POSES / 'screen.json').read_text()); l2p = json.loads((POSES / 'local-to-printstl.json').read_text())
    plan = json.loads((POSES / 'slice-plan.json').read_text())
    out = dict(schemaVersion=1, date='2026-10-19', scope=dec['scope'], method=dec['method'],
               inputs=dict(screen=dict(path=rel(POSES / 'screen.json'), sha256=sha(POSES / 'screen.json')), manifest=dict(path=rel(POSES / 'manifest-screen.json'), sha256=sha(POSES / 'manifest-screen.json')),
                           extraPoses=rel(POSES / 'extra-poses.json'), slicePlan=rel(POSES / 'slice-plan.json'), screenLog=rel(POSES / 'logs/screen.log'), screenResource=rel(POSES / 'logs/screen-resource.json'),
                           sliceLog=rel(POSES / 'logs/slice-plan.log')),
               parts={})
    for key in ['left_base', 'right_base', 'left_cheek', 'right_cheek', 'left_sleeve', 'right_sleeve']:
        d = dec['parts'][key]
        chosen = summarise(key, d['slug'])
        alts = [summarise(key, r['slug']) for r in plan if r['key'] == key and r['slug'] != d['slug']]
        for a in alts:
            a['rejectedBecause'] = d['alternatives'][a['slug']]
        sc = screen['parts'][[p['key'] for p in screen['parts']].index(key)]
        out['parts'][key] = dict(localStl=dict(path=l2p[key]['localStl'], sha256=l2p[key]['localSha256']),
                                 printStl20261007=dict(path=l2p[key]['printStl'], sha256=l2p[key]['printSha256'], localToPrintStl=l2p[key]['localToPrintStl']),
                                 chosen=dict(**chosen, sameAs20261007Trial=d['sameAsTrial'], reason=d['reason'], cleanFaces=[n for n, f in chosen['functionalFaces'].items() if f['must'] and f['clean']],
                                             facesWithSupport=d['facesWithSupport'], drillPass=d['drillPass'], brimDecision=d['brim'], openItems=d.get('openItems', [])),
                                 alternatives=alts,
                                 screenSummary=[dict(name=c['name'], rank=c['rank'], penalty=c['penalty'], contactMm2=c['contactMm2'], tipAngleDeg=c['tipAngleDeg'], heightMm=c['heightMm'], overhang60Mm2=c['overhang60Mm2'], sameAs=c['sameAs']) for c in sorted(sc['candidates'], key=lambda c: c['rank'])])
        # consistency: every MUST face listed as not clean must be explained
        unexplained = [n for n, f in chosen['functionalFaces'].items() if f['must'] and not f['clean'] and n not in {x['face'] for x in d['facesWithSupport']}]
        assert not unexplained, (key, unexplained)
    (POSES / 'poses.json').write_text(json.dumps(out, indent=1) + '\n')
    for key, p in out['parts'].items():
        c = p['chosen']
        print(key, c['slug'], 'contact', c['bedContactMm2'], 'h', c['heightMm'], 'tip', c['tipAngleDeg'], 'brim', c['objectSettings'].get('brim_type'),
              {mc: (v['supportExtrusionMm'], v['supportGrams'], v['etaMinutes']) for mc, v in c['perMachine'].items()}, 'clean', c['cleanFaces'], 'support on', [x['face'] for x in c['facesWithSupport']])


if __name__ == '__main__':
    main()
