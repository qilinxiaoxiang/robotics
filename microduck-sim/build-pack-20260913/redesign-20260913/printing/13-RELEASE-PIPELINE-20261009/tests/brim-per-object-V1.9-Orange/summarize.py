"""Write acceptance.json from the four brim reviews in this folder (before: delivered V1.9 run-r2; after: the v2 scratch slice).

    /tmp/microduck-cad-venv/bin/python summarize.py
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ref(p):
    p = (HERE / p).resolve()
    return dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())


out = dict(purpose='Pipeline v2 per-object brim acceptance on a scratch copy of the V1.9 Orange plate (release-V1.9 untouched).',
           date='2026-10-14', manifest=ref('manifest.json'), sourceManifest=ref('source-manifest-V1.9.json'),
           preparation=ref('run/preparation.json'), verify=ref('run/final-binding-check-v2.json'),
           slicing=('release_pipeline_v2.py slice run directly, not through run_bounded_cad.py (the caller excluded the CAD runner); '
                    'the runner lock was checked free before each slice. Bambu 11.6 s / 484 MiB max RSS, Elegoo 12.0 s / 802 MiB.'),
           machines={})
for m in ('Bambu', 'Elegoo'):
    new = json.loads((HERE / f'brim-review-v2-Orange-{m}.json').read_text())
    old = json.loads((HERE / f'brim-review-V1.9-run-r2-Orange-{m}.json').read_text())
    out['machines'][m] = dict(
        before=dict(review=ref(f'brim-review-V1.9-run-r2-Orange-{m}.json'), archive=old['archive'], plate=old['plateBrimSettings'], passed=old['passed']),
        after=dict(review=ref(f'brim-review-v2-Orange-{m}.json'), archive=new['archive'], plate=new['plateBrimSettings'], passed=new['passed']),
        objects={k: dict(plan=v['brimType'], modelMm2=v['modelAreaMm2'],
                         beforeBrimMm2=old['objects'][k]['brimAreaMm2'], beforeInsideOwnHullMm2=old['objects'][k]['brimInsideOwnHullMm2'],
                         beforeFailures=old['objects'][k]['failures'],
                         afterBrimMm2=v['brimAreaMm2'], afterReachMm=v['brimReachMm'], afterPassed=v['passed'])
                 for k, v in new['objects'].items()})
(HERE / 'acceptance.json').write_text(json.dumps(out, indent=1) + '\n')
for m, v in out['machines'].items():
    print(m, 'before passed', v['before']['passed'], '| after passed', v['after']['passed'])
    for k, o in v['objects'].items():
        print(f"   {k}: plan {o['plan']}, before {o['beforeBrimMm2']} mm2 (inside own hull {o['beforeInsideOwnHullMm2']}), after {o['afterBrimMm2']} mm2, model {o['modelMm2']}")
