"""Effective open area of the lower head shell's neck opening: vertical rays from below through the opening; a ray counts
as open when it reaches z 125 (inside the head) without hitting any guide part (neck servo, ring, yaw link, jaw parts,
clips, shell). Meshes decoded from guide-data.json (float32 positions, uint32 indices)."""
import json, base64, sys, numpy as np, trimesh
d=json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/data/guide-data.json'))
ms={}
for p in d['parts']:
    b=p['bounds']; lo,hi=b if isinstance(b[0],list) else (b[:3],b[3:])
    if hi[0]>0 and lo[0]<50 and hi[1]>-35 and lo[1]<35 and hi[2]>60 and lo[2]<135:
        V=np.frombuffer(base64.b64decode(p['positionB64']),dtype=np.float32).reshape(-1,3)
        I=np.frombuffer(base64.b64decode(p['indexB64']),dtype=np.uint32).reshape(-1,3) if p.get('indexB64') else np.arange(len(V)).reshape(-1,3)
        ms[p['key']]=trimesh.Trimesh(V.astype(float),I,process=False)
print('parts', sorted(ms))
xs=np.arange(10.75,40,0.5); ys=np.arange(-28.25,28.5,0.5); X,Y=np.meshgrid(xs,ys,indexing='ij')
o=np.column_stack([X.ravel(),Y.ravel(),np.full(X.size,60.0)]); up=np.tile([0,0,1.0],(X.size,1))
# the opening = rays that pass head_bottom
hb=ms['head_bottom'].ray.intersects_any(o,up)
blocked=np.zeros(X.size,bool); by={}
for k,m in ms.items():
    if k in ('head_bottom','head_cap'): continue
    # count a hit only between z 95 and 125 (from the shell floor level up into the head)
    l,r,_=m.ray.intersects_location(o,up,multiple_hits=True)
    if len(r)==0: continue
    sel=(l[:,2]>95)&(l[:,2]<125); rr=np.unique(r[sel])
    for x in rr:
        if not blocked[x] and not hb[x]: by[k]=by.get(k,0)+1
    blocked[rr]=True
openA=(~hb).sum()*0.25; free=((~hb)&(~blocked)).sum()*0.25
res={'opening_area_mm2':float(openA),'unobstructed_vertical_area_mm2':float(free),'first_blockers_cells':by}
print(json.dumps(res,indent=1)); json.dump(res,open(sys.argv[1],'w'),indent=1)
