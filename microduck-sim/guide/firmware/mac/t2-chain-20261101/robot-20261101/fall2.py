"""Tick by tick from the hand-back to the guard trip: which joints and which fields moved."""
import json, sys, math
rows=[json.loads(l) for l in open(sys.argv[1]) if l.startswith('{')]
t0=1793584883.6
sel=[r for r in rows if 3.7<=r['t']-t0<=4.85]
print(sorted(sel[0].keys()))
names=list(sel[0]['q'].keys()) if isinstance(sel[0]['q'],dict) else None
print('names',names)
for i,r in enumerate(sel):
    if i%3 and not (4.45<r['t']-t0): continue
    a=r['action']; idx=sorted(range(len(a)),key=lambda k:-abs(a[k]))[:3]
    print(f"{r['t']-t0:5.2f} {r['mode']:7s} g {r['gb'][0]:+.2f} {r['gb'][1]:+.2f} top a "+' '.join(f"{k}:{a[k]:+.2f}" for k in idx)+f" hold {r.get('hold')} grip {r.get('grip_stop')} kp {r.get('kp')} cmd {r.get('cmd')}"[:150])
r=sel[0]; print('seepick end q',r['q']); print('action',[round(x,2) for x in r['action']])
for r in sel:
    if r['mode']=='walk': print('first walk q',r['q']); print('action',[round(x,2) for x in r['action']]); print('goal',r['goal_tick'],'cur',r['cur_ma']); break
for r in sel[-8:]:
    print(round(r['t']-t0,2), r['mode'], 'q', [round(x,2) for x in r['q']], 'a', [round(x,2) for x in r['action']], 'cur', r['cur_ma'])
