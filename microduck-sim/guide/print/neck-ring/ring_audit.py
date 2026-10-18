"""Collect every interference-audit result that involves the 4.9 mm neck pitch ring into ring-audit.json.

    ~/.venvs/microduck-guide/bin/python print/neck-ring/ring_audit.py

Run after build_solids.py, pairs.py, cables.py and steps_audit.py. Pass criteria: every final-pose overlap with the ring is
surface contact (depth <= 0.01 mm), no assembly step path collides with it, and no cable passes through it.
"""
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
IA = HERE.parents[1] / 'content' / 'interference-audit'
KEY = 'neck_pitch_ring'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def walk(o, hits, path=''):
    if isinstance(o, dict):
        if any(v == KEY for v in o.values() if isinstance(v, str)) or KEY in o.get('moving', []) if isinstance(o.get('moving'), list) else False:
            hits.append((path, o))
            return
        for k, v in o.items():
            walk(v, hits, f'{path}/{k}')
    elif isinstance(o, list):
        for i, v in enumerate(o):
            walk(v, hits, f'{path}[{i}]')


def main():
    pairs = json.loads((IA / 'pairs-raw.json').read_text())
    ring_pairs = [p for p in pairs['pairs'] if KEY in (p['a'], p['b']) and p.get('volumeMm3', 0) > 1e-9]
    contact = [dict(other=p['b'] if p['a'] == KEY else p['a'], volumeMm3=round(p['volumeMm3'], 4), depthMm=p.get('depthMm')) for p in ring_pairs]
    steps = json.loads((IA / 'steps-raw.json').read_text())
    step_hits = []
    walk(steps, step_hits)
    cables = json.loads((IA / 'cables-raw.json').read_text())
    cable_text = json.dumps(cables)
    rec = dict(
        part=KEY, ringRecord=json.loads((HERE / 'thicken_ring.json').read_text()),
        finalPoseOverlaps=contact,
        finalPosePass=all((c['depthMm'] or 0) <= 0.01 for c in contact),
        stepEntries=[dict(path=p, entry=e) for p, e in step_hits],
        cableMentions=cable_text.count(KEY),
        sources={f: sha(IA / f) for f in ('pairs-raw.json', 'steps-raw.json', 'cables-raw.json')})
    (HERE / 'ring-audit.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ('finalPoseOverlaps', 'finalPosePass', 'cableMentions')}, indent=1))
    for p, e in step_hits:
        print(p, json.dumps(e)[:400])


if __name__ == '__main__':
    main()
