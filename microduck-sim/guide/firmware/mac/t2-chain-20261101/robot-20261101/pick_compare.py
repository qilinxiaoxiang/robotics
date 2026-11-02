"""Hold (run 1) against the misses (run 2, run 9 x2): picture box, joints, jaw, tilt by T2 phase. argv: slices of mode seepick rows."""
import json, sys
def load(f):
    rows = [json.loads(l) for l in open(f)]; out, cur = [], []
    for r in rows:
        if cur and r['t'] - cur[-1]['t'] > 2: out.append(cur); cur = []
        cur.append(r)
    return out + [cur]
NAMES = ('rank', 'rknee', 'rhp', 'rroll', 'ryaw', 'lank', 'lknee', 'lhp', 'lroll', 'lyaw', 'neck?', 'hp?', 'hy', 'hr')
for f in sys.argv[1:]:
    for ep in load(f):
        print(f.split('/')[-1], 't', round(ep[0]['t'], 1), 'rows', len(ep), 'last phase', ep[-1].get('sp_phase'), 'keys jaw', [k for k in ep[0] if 'jaw' in k or k.startswith('sp')])
        for ph in (0.0, .1, .2, .3, .35, .4, .44, .5, .6, .7, .8):
            r = min(ep, key=lambda x: abs((x.get('sp_phase') or 0) - ph))
            b = r.get('sp_body') or []
            print('  ph %.2f box %s jawcmd %s jaw %s neck %.2f head %.2f hy %.2f gb %s' % (r.get('sp_phase') or 0, [round(x, 3) for x in b], r.get('sp_jaw'), r.get('jaw_deg'), r['q'][10], r['q'][11], r['q'][12], [round(x, 2) for x in r['gb']]))
