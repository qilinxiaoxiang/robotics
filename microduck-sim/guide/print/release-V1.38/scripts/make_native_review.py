"""Write run/native-review.json for V1.38 (one Orange plate: the rear converter box cap, D-034). From the V1.20 script.
Read-only on the reviews; fails unless every review passed: scripts/review_v138.py and review_brim.py, both machines.

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
notes = ('V1.38 on one Orange plate: the rear converter box cap whose four screw columns reach the boards (D-034), centred on the '
         f"bed (preparation plateCentreOffsetMm). First layer {fl('Bambu', 'rear_lid')} / {fl('Elegoo', 'rear_lid')} mm2, Bambu / Elegoo. "
         'Same pose and profile as the printed V1.20 cap (outer rear face on the bed, tree support under the rounded rear edges). '
         'Brims as planned (review_brim.py).')
out = dict(passed=True, preparationSha256=sha(RUN / 'preparation.json'), reviewNotes=notes, nativeArchives=archives, reviews=reviews)
(RUN / 'native-review.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'passed': True, 'reviews': list(reviews), 'archives': len(archives)}))
