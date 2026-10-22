"""Back-to-back A7Z, vertical, header on top: sweep the board's rear (component) face position Xc and recast clearances.
6530B envelope from Radxa's photos: body s 0-65, d 6-30, 11.5 mm; corner legs s 0-7 / 58-65 over the header strip d 0-6;
fan (inlet up) s 4-27, d 7-29, needs 3 mm above the 11.5 mm top. d = distance from the header edge (now the top edge)."""
import json, base64, sys, numpy as np, trimesh
G='/Users/xiangzheng/code/robotics/microduck-sim/guide/'
d=json.load(open(G+'data/guide-data.json'))
skip=lambda k: k=='pi' or k.startswith('head_pi_') or k in ('camera_ribbon','antenna_coax','antenna_ipex')
ms={}
for p in d['parts']:
    b=p['bounds']; lo,hi=b if isinstance(b[0],list) else (b[:3],b[3:])
    if skip(p['key']): continue
    if hi[0]>-10 and lo[0]<95 and hi[1]>-40 and lo[1]<40 and hi[2]>95 and lo[2]<165:
        V=np.frombuffer(base64.b64decode(p['positionB64']),dtype=np.float32).reshape(-1,3)
        I=np.frombuffer(base64.b64decode(p['indexB64']),dtype=np.uint32).reshape(-1,3) if p.get('indexB64') else np.arange(len(V)).reshape(-1,3)
        ms[p['key']]=trimesh.Trimesh(V.astype(float),I,process=False)
ZTOP=144.6; Y1=32.5
def world(s,dd,x): return np.column_stack([np.full(len(s),x), Y1-s, ZTOP-dd])
ss=np.arange(0.25,65,0.5); ds=np.arange(0.25,30,0.5); S,D=np.meshgrid(ss,ds,indexing='ij'); S=S.ravel(); D=D.ravel()
def cast(pts,dirn):
    free=np.full(len(pts),80.0); who=np.array(['']*len(pts),dtype=object)
    for k,m in ms.items():
        loc,ri,_=m.ray.intersects_location(pts,np.tile(dirn,(len(pts),1)),multiple_hits=False)
        if len(ri)==0: continue
        dist=(loc-pts[ri])@dirn; bt=(dist<free[ri])&(dist>-1e-6); free[ri[bt]]=dist[bt]; who[ri[bt]]=k
    return free,who
body=(D>=6); legs=(D<6)&((S<7)|(S>58)); fan=(S>=4)&(S<=27)&(D>=7)&(D<=29); plug=(D<6)&(S>=7)&(S<=58)
ends=(S<6)|(S>59)
out=[]
for Xc in np.arange(65,70.01,1.0):
    rear,rw=cast(world(S,D,Xc-0.01),np.array([-1.0,0,0])); front,fw=cast(world(S,D,Xc+1.61),np.array([1.0,0,0]))
    need=np.where(fan,14.5,np.where(body|legs,11.5,np.where(plug,17.0,0)))
    short=need+1.0-rear                                  # 1 mm clearance
    redesign={'clip_cap','clip_head'}
    bad=(short>0)&~np.isin(rw.astype(str),list(redesign))
    badfix=bad&~(ends&(rw.astype(str)=='head_cap'))
    fbad=(front<3.0)&~np.isin(fw.astype(str),list(redesign))   # underside parts 2 mm + 1 mm
    u,c=np.unique(rw[badfix].astype(str),return_counts=True); fu,fc=np.unique(fw[fbad].astype(str),return_counts=True)
    out.append({'Xc':float(Xc),'rear_short_cells':int(badfix.sum()),'worst_rear_short':round(float(short[badfix].max()) if badfix.any() else 0,2),
                'rear_blockers':dict(zip(u.tolist(),c.tolist())),'front_min_gap':round(float(front[~np.isin(fw.astype(str),list(redesign))].min()),2),
                'front_bad_cells':int(fbad.sum()),'front_blockers':dict(zip(fu.tolist(),fc.tolist())),'cap_end_rail_cells':int((bad&ends&(rw.astype(str)=='head_cap')).sum())})
for o in out: print(json.dumps(o))
json.dump(out,open('b2b_sweep.json','w'),indent=1)
