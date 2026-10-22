import json, base64, numpy as np, trimesh
exec(open('rear_free.py').read().split("ss=np.arange")[0].replace("sys.argv","[0,'x']"))
ss=np.arange(0.25,65,0.5)
# rear depth for rows d up to 45 (board shifted up)
for d in (14,20,30,34,38,42):
    pts=O+ss[:,None]*ES+d*ED-0.01*N
    best=np.full(len(ss),60.0); who=['']*len(ss)
    for k,m in ms.items():
        loc,ri,_=m.ray.intersects_location(pts,np.tile(-N,(len(ss),1)),multiple_hits=False)
        for j,(l) in zip(ri,loc):
            dd=(l-pts[j])@(-N)
            if dd<best[j]: best[j]=dd; who[j]=k
    print('row d',d,'min',best.min().round(1),'p10',np.percentile(best,10).round(1),'med',np.median(best).round(1), sorted(set(w for w,b in zip(who,best) if b<14)))
# room above the board top edge along +ED, for a slab from h=-14 (rear) to h=+4 (front)
for h in (-14,-10,-6,-2,0.8,3):
    pts=O+ss[:,None]*ES+30*ED+h*N
    best=np.full(len(ss),60.0); who=['']*len(ss)
    for k,m in ms.items():
        loc,ri,_=m.ray.intersects_location(pts,np.tile(ED,(len(ss),1)),multiple_hits=False)
        for j,l in zip(ri,loc):
            dd=(l-pts[j])@ED
            if dd<best[j]: best[j]=dd; who[j]=k
    print('up from top edge at h',h,'min',best.min().round(1),'p10',np.percentile(best,10).round(1),'med',np.median(best).round(1), sorted(set(w for w,b in zip(who,best) if b<10)))
