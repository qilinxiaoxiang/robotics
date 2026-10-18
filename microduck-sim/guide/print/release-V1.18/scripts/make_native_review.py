"""Write run/native-review.json for the V1.18 delta (one Orange plate: battery backpack frame and cap). Read-only on the reviews;
fails unless every review passed. Orange: scripts/review_v115.py (the two battery backpack frame support regions) and
review_brim.py, both machines. No White plate and no A7Z part: V1.17 carries them and is being printed.

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
sup = lambda m, k: o[m]['supportByRegion'][k]['supportTopZMm']
notes = ('V1.18 delta: only the D-010 battery backpack frame and cap on one Orange plate (V1.17 is being printed, Shawn 2026-10-15). '
         'Frame rim-down like the box frame: first layer '
         f"{fl('Bambu', 'battery_backpack_frame')} / {fl('Elegoo', 'battery_backpack_frame')} mm2 (Bambu / Elegoo) against 713 mm2 of "
         'mesh contact, one island; support under the front plate and under the cover flap reaches print z '
         f"{sup('Bambu', 'battery_backpack_frame:frontPlateCeiling')} / {sup('Elegoo', 'battery_backpack_frame:frontPlateCeiling')} under "
         f"the 19.35 mm overhang. Cap on its back face: first layer {fl('Bambu', 'battery_backpack_cap')} / {fl('Elegoo', 'battery_backpack_cap')} "
         'mm2, one island. No brim on either object (review_brim.py).')
out = dict(passed=True, preparationSha256=sha(RUN / 'preparation.json'), reviewNotes=notes, nativeArchives=archives, reviews=reviews)
(RUN / 'native-review.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'passed': True, 'reviews': list(reviews), 'archives': len(archives)}))
