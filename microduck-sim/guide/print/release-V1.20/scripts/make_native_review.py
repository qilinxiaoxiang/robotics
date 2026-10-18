"""Write run/native-review.json for the V1.20 delta (one Orange plate: the box cap, the battery backpack frame refitted to the
Swann 39 switch, and its cap). Read-only on the reviews; fails unless every review passed. Orange: scripts/review_v120.py
(backpack frame support regions) and review_brim.py, both machines. No White plate.

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
notes = ('V1.20 delta on one Orange plate: the rear converter box cap (V1.19 design, never printed), the battery backpack frame '
         'with the 12.3 x 27.5 mm Swann 39 switch hole and its cap, one row centred on the bed (preparation plateCentreOffsetMm). '
         f"First layer {fl('Bambu', 'rear_lid')} / {fl('Elegoo', 'rear_lid')} mm2 (box cap), "
         f"{fl('Bambu', 'battery_backpack_frame')} / {fl('Elegoo', 'battery_backpack_frame')} mm2 (frame, rim-down) and "
         f"{fl('Bambu', 'battery_backpack_cap')} / {fl('Elegoo', 'battery_backpack_cap')} mm2 (backpack cap), Bambu / Elegoo, one island each. "
         'Tree support reaches the frame front plate and cover flap on both machines (review_v120.py). Brims as planned (review_brim.py).')
out = dict(passed=True, preparationSha256=sha(RUN / 'preparation.json'), reviewNotes=notes, nativeArchives=archives, reviews=reviews)
(RUN / 'native-review.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'passed': True, 'reviews': list(reviews), 'archives': len(archives)}))
