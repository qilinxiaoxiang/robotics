"""Write run/native-review.json for the V1.21 delta (one Orange plate: the left and right hot-glue sole molds).
Read-only on the reviews; fails unless every review passed. Orange: scripts/review_v121.py (no support anywhere) and
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
notes = ('V1.21 delta on one Orange plate: the left and right hot-glue sole molds (tools, any PLA spool), one row centred '
         'on the bed (preparation plateCentreOffsetMm). '
         f"First layer {fl('Bambu', 'hotglue_mold_left')} / {fl('Elegoo', 'hotglue_mold_left')} mm2 (left) and "
         f"{fl('Bambu', 'hotglue_mold_right')} / {fl('Elegoo', 'hotglue_mold_right')} mm2 (right), Bambu / Elegoo, one island each. "
         'No support and no brim on either machine (review_v121.py, review_brim.py). 0.12 mm layers, top ironing, seam at the back.')
out = dict(passed=True, preparationSha256=sha(RUN / 'preparation.json'), reviewNotes=notes, nativeArchives=archives, reviews=reviews)
(RUN / 'native-review.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'passed': True, 'reviews': list(reviews), 'archives': len(archives)}))
