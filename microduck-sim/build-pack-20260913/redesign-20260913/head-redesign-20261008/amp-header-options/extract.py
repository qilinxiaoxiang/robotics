"""Extract the amplifier and its head neighbours from the current guide (read-only) into a local cache."""
import sys, json, pickle
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / 'guide/content/interference-audit') if (HERE.parents[3] / 'guide').exists() else '')
SIM = Path('/Users/xiangzheng/code/robotics/microduck-sim')
sys.path.insert(0, str(SIM / 'guide/content/interference-audit'))
from ia_lib import decode_guide_part
G = json.loads((SIM / 'guide/data/guide-data.json').read_text())
amp = [p for p in G['parts'] if p['key'] == 'amplifier'][0]
lo, hi = amp['bounds']
box = [[lo[0] - 45, lo[1] - 45, lo[2] - 40], [hi[0] + 45, hi[1] + 45, hi[2] + 30]]
out = {}
rows = []
for p in G['parts']:
    a, b = p['bounds']
    rows.append((p['key'], p['name'], p['module'], [round(x, 1) for x in a], [round(x, 1) for x in b]))
    if all(a[i] <= box[1][i] and box[0][i] <= b[i] for i in range(3)):
        v, f = decode_guide_part(p)
        out[p['key']] = {'v': v, 'f': f, 'name': p['name'], 'module': p['module'], 'bounds': p['bounds']}
cables = {c['id']: c for c in G['cables'] if c.get('id') in ('i2s', 'spk', 'csi', 'pi-trunk', 'imu', 'uart')}
steps = [{k: s.get(k) for k in ('id', 'title', 'show', 'add', 'cables')} for s in G['steps']]
pickle.dump({'parts': out, 'cables': cables, 'box': box, 'revision': G.get('revision'), 'steps': steps},
            open(sys.argv[1], 'wb'))
print('amp bounds', amp['bounds'])
print('neighbours', sorted(out))
for r in rows:
    if r[0] in out: print(r)
for cid, c in cables.items():
    print(cid, {k: v for k, v in c.items() if k != 'path'})
    print('  path', [[round(x, 1) for x in q] for q in c['path']])
