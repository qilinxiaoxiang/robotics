import json, sys
rows=[json.loads(l) for l in open(sys.argv[1]) if l.startswith('{')]
t0=1793584883.6
sel=[r for r in rows if 3.8<=r['t']-t0<=4.85]
pr=lambda v:[round(x,2) for x in v] if v else v
N=None
for i,r in enumerate(sel):
    if i%4==0 or r['t']-t0>4.5:
        print(f"{r['t']-t0:5.2f} {r['mode'][:4]} q",pr(r['q']),'a',pr(r['action']),'gy',pr(r['gyro_body']),'cmd',str(r.get('cmd'))[:60],'lastcur',r['cur_ma'][:5] if r.get('cur_ma') else None,'pol',r.get('policy'),'late',r.get('late'),'miss',r.get('missing'))
print(sorted(sel[0].keys())[28:])
