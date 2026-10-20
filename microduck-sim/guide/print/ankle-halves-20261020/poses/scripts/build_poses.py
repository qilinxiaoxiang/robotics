#!/usr/bin/env python3
"""Assemble poses.json for the four two-half ankle parts from the native slices (pose.json, readback-*.json, faces-*.json)
and decisions.json (per key: the chosen slug, or the mirror of a left slug for the right side, with the written reason).
Fails if a chosen pose lacks a slice on either machine or if a MUST face rests on support without a written explanation.
    /tmp/microduck-cad-venv/bin/python build_poses.py
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent; POSES = HERE.parent
MACHINES = ['Bambu', 'Elegoo']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def summarise(key, slug):
    run = POSES / 'slices' / key / slug
    pose = json.loads((run / 'pose.json').read_text()); per = {}
    for mc in MACHINES:
        r = json.loads((run / f'readback-{mc}.json').read_text()); f = json.loads((run / f'faces-{mc}.json').read_text())
        per[mc] = dict(etaMinutes=r['etaMinutes'], grams=r['headerGrams'], supportGrams=r['supportGrams'], supportExtrusionMm=f['supportExtrusionTotalMm'],
                       brimPassed=f['brim']['passed'], objectSettings=f['objectSettings'], objectSettingsSource=f['objectSettingsSource'],
                       mustOnSupport={n: dict(touchedMm2=s['touchedMm2'], supportInsideMm=s.get('supportInsideMm', 0)) for n, s in f['faceSets'].items()
                                      if s['must'] and (s['touchedMm2'] > 0 or s.get('supportInsideMm', 0) > 0)},
                       reportOnSupport={n: s['touchedMm2'] for n, s in f['faceSets'].items() if not s['must'] and s['touchedMm2'] > 0},
                       files=[str((run / x).relative_to(POSES)) for x in (f'readback-{mc}.json', f'faces-{mc}.json')])
    return pose, per


def main():
    dec = json.loads((POSES / 'decisions.json').read_text()); out = dict(schemaVersion=1, parts={})
    for key, d in dec.items():
        pose, per = summarise(key, d['slug'])
        assert pose['localStl']['sha256'] == sha(pose['localStl']['path']), f'{key}: local STL changed since slicing'
        for mc, s in per.items():
            assert not s['mustOnSupport'] or d.get('mustExplanation'), (key, mc, s['mustOnSupport'])
        out['parts'][key] = dict(localStl=pose['localStl'], chosen=dict(poseName=d.get('poseName', f'local {pose["down"]} down'), slug=d['slug'], why=d['why'],
                                 sourceToPrint=pose['sourceToPrint'], bedContactMm2=pose['contactMm2'], heightMm=pose['heightMm'], footprintMm=pose['footprintMm'],
                                 objectSettingsReason='pipeline R1 brim rule (objectSettingsSource in the slices)', perMachine=per,
                                 **({'mustExplanation': d['mustExplanation']} if d.get('mustExplanation') else {}),
                                 brim=d.get('brim', {})),   # brimInsideHullAllowance* / brimAlongSupportReason for the release rows
                                 rejected=d.get('rejected', {}))
    (POSES / 'poses.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: (v['chosen']['poseName'], v['chosen']['bedContactMm2'], {m: (s['supportExtrusionMm'], s['brimPassed'], s['mustOnSupport']) for m, s in v['chosen']['perMachine'].items()}) for k, v in out['parts'].items()}, indent=1))


if __name__ == '__main__':
    main()
