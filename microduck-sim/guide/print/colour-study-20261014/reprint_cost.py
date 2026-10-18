"""Reprint list per colour option from colour_as_built.json and the spec colour maps.  python3 reprint_cost.py"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
parts = {p['key']: p for p in json.loads((HERE / 'colour_as_built.json').read_text())['parts']}
GROUP = {'shells': ['shell_left', 'shell_right'], 'thighs': ['thigh_left', 'thigh_right'], 'head_cap': ['head_cap_v19'],
         'box': ['rear_frame', 'rear_lid'], 'pack': ['rear_pack']}
V20 = {'shell_left', 'shell_right', 'head_cap_v19'}   # v20-source/README.md: reprinted in V2.0 anyway (source only, not released)
out = {}
for k in 'ABCDE':
    s = json.loads((HERE / f'spec-{k}.json').read_text()); base = json.loads((HERE / 'spec-A.json').read_text())['colours']
    rows = []
    for g, c in s['colours'].items():
        if c == base[g]:
            continue
        for key in GROUP[g]:
            p = parts[key]
            rows.append({'key': key, 'name': p['name'], 'from': p['colour'], 'to': c, 'grams': p['grams'],
                         'gramsSource': p['gramsSource'], 'alreadyPrinted': p.get('installed', True),
                         'alsoInV20Source': key in V20})
    out[k] = {'label': s['label'], 'reprints': rows, 'whiteGrams': round(sum(r['grams'] for r in rows if r['to'] == 'White'), 2),
              'partsToReprint': len(rows), 'extraBeyondV20': [r['key'] for r in rows if not r['alsoInV20Source']]}
(HERE / 'reprint_cost.json').write_text(json.dumps(out, indent=1) + '\n')
for k, v in out.items():
    print(k, v['label'], v['partsToReprint'], v['whiteGrams'], 'extra beyond V2.0:', v['extraBeyondV20'])
