"""Write run/native-review.json for the V1.30 delta (White: the U20 face panel; Black: the U20 eye trim and the exit jaw support; Yellow: the exit lower head shell). Read-only on the
reviews; fails unless every review passed: scripts/review_v130.py and review_brim.py, on both machines.

    /tmp/microduck-cad-venv/bin/python scripts/make_native_review.py
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent; REL = HERE.parent; RUN = REL / 'run'
COLOURS = ('White', 'Black', 'Yellow')


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
sup = lambda c, m: o[c, m]['supportExtrusionTotalMm']
keys = {c: [p['key'] for p in prep['parts'] if p['color'] == c] for c in COLOURS}
lines = ['V1.30 delta: the U20 face panel (White); the U20 eye trim and the exit jaw support side by side (Black); the exit lower head shell (Yellow); each plate centred on its bed (preparation plateCentreOffsetMm). Per part the '
         'first-layer model area Bambu / Elegoo in mm2, then the plate support extrusion Bambu / Elegoo in mm.']
for c in COLOURS:
    lines.append(f'{c}: ' + '; '.join(f"{k} {fl(c, 'Bambu', k)} / {fl(c, 'Elegoo', k)}" for k in keys[c]) +
                 f"; support {sup(c, 'Bambu')} / {sup(c, 'Elegoo')}.")
lines.append('V1.17 White overrides (support interface) on the face plate, Black and Yellow donor profiles as is; brims as planned per object (review_brim.py); '
             'the head shell keeps the V1.8 support blockers (pilot-1 moved with its seat), support inside each blocker no more than the accepted V1.8 slice '
             '(review/Yellow_<Machine>-review.json supportInBlockers); where support lands is mapped in review/<Colour>_<Machine>-support-map.json '
             '(orientation-study/scripts/support_map.py).')
out = dict(passed=True, preparationSha256=sha(RUN / 'preparation.json'), reviewNotes=' '.join(lines), nativeArchives=archives, reviews=reviews)
(RUN / 'native-review.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps({'passed': True, 'reviews': list(reviews), 'archives': len(archives)}))
