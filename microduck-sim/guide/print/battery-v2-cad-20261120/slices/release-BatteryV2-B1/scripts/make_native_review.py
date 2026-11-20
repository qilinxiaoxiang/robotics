"""Write run/native-review.json for BatteryV2-B1 (one Orange plate: battery backpack V2 frame and cap). From
release-V1.41/scripts/make_native_review.py. Read-only on the reviews; fails unless every review passed
(scripts/review_bp.py and review_brim.py, both machines).

    ~/.venvs/microduck-cad/bin/python scripts/make_native_review.py
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
keys = ('battery_v2_frame', 'battery_v2_cap')
notes = ('BatteryV2-B1 on one Orange plate: battery backpack V2 rev B frame (front face down) and cap (back face down), side by '
         'side. First layer, Bambu / Elegoo: ' + ', '.join(f"{k} {fl('Bambu', k)} / {fl('Elegoo', k)} mm2" for k in keys) + '. '
         'No support regions apply (review_bp.py reports support, does not limit it). Brims as planned (review_brim.py).')
out = dict(passed=True, preparationSha256=sha(RUN / 'preparation.json'), reviewNotes=notes, nativeArchives=archives, reviews=reviews)
(RUN / 'native-review.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'passed': True, 'reviews': list(reviews), 'archives': len(archives)}))
