"""Write run/native-review.json for V1.41 (one Orange plate: battery backpack cap and battery hatch; the V1.40 frame is not
on the plate). From the V1.40 script. Read-only on the reviews; fails unless every review passed: scripts/review_v141.py and
review_brim.py, both machines.

    /tmp/microduck-cad-venv/bin/python scripts/make_native_review.py
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent; REL = HERE.parent; RUN = REL / 'run'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


prep = json.loads((RUN / 'preparation.json').read_text())
assert {r['color'] for r in prep['rows']} == {'Orange'}
reviews, o = {}, {}
for m in ('Bambu', 'Elegoo'):
    p = REL / f'review/Orange_{m}-review.json'; o[m] = json.loads(p.read_text()); assert o[m]['passed'] is True, p
    reviews[f'Orange_{m}'] = ref(p)
    p = REL / f'review/Orange_{m}-brim.json'; assert json.loads(p.read_text())['passed'] is True, p
    reviews[f'Orange_{m}_brim'] = ref(p)
archives = {}
for row in prep['rows']:
    res = json.loads((RUN / f"native/{row['color']}_{row['machine']}/result.json").read_text())
    a = Path(res['archive']['path']).resolve(); archives[str(a)] = sha(a)
fl = lambda m, k: o[m]['firstLayerComparison'][f'{k}_1']['v111']
keys = ('battery_backpack_cap', 'battery_hatch')
notes = ('V1.41 on one Orange plate: the battery backpack cap with two ear pockets in the roof, and the new battery hatch '
         '(battery-quickswap-20261101/build-v2), side by side and centred on the bed (preparation plateCentreOffsetMm). The V1.40 '
         'frame is not on the plate. First layer, Bambu / Elegoo: '
         + ', '.join(f"{k} {fl('Bambu', k)} / {fl('Elegoo', k)} mm2" for k in keys) + '. '
         'No support regions apply to the cap or the hatch (review_v141.py reports support, does not limit it). Brims as planned (review_brim.py).')
out = dict(passed=True, preparationSha256=sha(RUN / 'preparation.json'), reviewNotes=notes, nativeArchives=archives, reviews=reviews)
(RUN / 'native-review.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'passed': True, 'reviews': list(reviews), 'archives': len(archives)}))
