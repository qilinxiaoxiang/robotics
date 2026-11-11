"""Write run/native-review.json for FlightPack-D1 (Orange: wing plate, trays L/R, FC bracket at 100 % infill; Black: the four
nacelle clamp halves). From release-V1.41/scripts/make_native_review.py. Read-only on the reviews; fails unless every review
passed: scripts/review_fp.py and review_brim.py, both colours, both machines.

    /tmp/microduck-cad-venv/bin/python scripts/make_native_review.py
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent; REL = HERE.parent; RUN = REL / 'run'
COLOURS = ('Orange', 'Black')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ref(p):
    return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


prep = json.loads((RUN / 'preparation.json').read_text())
assert {r['color'] for r in prep['rows']} == set(COLOURS)
reviews, o = {}, {}
for c in COLOURS:
    for m in ('Bambu', 'Elegoo'):
        p = REL / f'review/{c}_{m}-review.json'; o[c, m] = json.loads(p.read_text()); assert o[c, m]['passed'] is True, p
        reviews[f'{c}_{m}'] = ref(p)
        p = REL / f'review/{c}_{m}-brim.json'; assert json.loads(p.read_text())['passed'] is True, p
        reviews[f'{c}_{m}_brim'] = ref(p)
archives = {}
for row in prep['rows']:
    res = json.loads((RUN / f"native/{row['color']}_{row['machine']}/result.json").read_text())
    a = Path(res['archive']['path']).resolve(); archives[str(a)] = sha(a)
fl = lambda c, m, k: o[c, m]['firstLayerComparison'][f'{k}_1']['v111']
parts = {c: [p['key'] for p in prep['parts'] if p['color'] == c] for c in COLOURS}
notes = ('FlightPack-D1, geometry c31e5e2d. Orange plate at 100 % sparse infill (wing plate root band sized as solid PLA). '
         'First layer, Bambu / Elegoo: '
         + '; '.join(f"{k} {fl(c, 'Bambu', k)} / {fl(c, 'Elegoo', k)} mm2" for c in COLOURS for k in parts[c]) + '. '
         'No support regions apply (review_fp.py reports support, does not limit it). Brims as planned (review_brim.py).')
out = dict(passed=True, preparationSha256=sha(RUN / 'preparation.json'), reviewNotes=notes, nativeArchives=archives, reviews=reviews)
(RUN / 'native-review.json').write_text(json.dumps(out, indent=1))
print(notes)
