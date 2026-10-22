"""Free depth behind the A7Z (along -n from the PCB rear face h=0) and in front of it (along +n from h=1.6),
on a 0.5 mm grid over the board. Obstacles: guide-data parts, excluding the A7Z itself and parts that ride on it."""
import json, base64, sys, numpy as np, trimesh
G='/Users/xiangzheng/code/robotics/microduck-sim/guide/'
fr=json.load(open(G+'print/a7z-head/checks.json'))['frame']
O=np.array(fr['origin']); ES=np.array(fr['es']); ED=np.array(fr['ed']); N=np.array(fr['n'])
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
ss=np.arange(0.25,65,0.5); ds=np.arange(0.25,30,0.5); S,D=np.meshgrid(ss,ds,indexing='ij')
def cast(h,dirn):
    pts=O+S.ravel()[:,None]*ES+D.ravel()[:,None]*ED+h*N
    free=np.full(len(pts),60.0); who=np.array(['']*len(pts),dtype=object)
    for k,m in ms.items():
        loc,ri,_=m.ray.intersects_location(pts,np.tile(dirn,(len(pts),1)),multiple_hits=False)
        if len(ri)==0: continue
        dist=(loc-pts[ri])@dirn; bt=dist<free[ri]; free[ri[bt]]=dist[bt]; who[ri[bt]]=k
    return free.reshape(S.shape), who.reshape(S.shape)
rear,rw=cast(-0.01,-N); front,fw=cast(1.61,N)
np.savez(sys.argv[1],S=S,D=D,rear=rear,front=front,rw=rw.astype(str),fw=fw.astype(str))
def zone(F,W,s0,s1,d0,d1):
    m=(S>=s0)&(S<=s1)&(D>=d0)&(D<=d1); f=F[m]; u,c=np.unique(W[m],return_counts=True)
    i=np.argmin(np.where(m,F,99)); 
    return {'min':round(float(f.min()),2),'p10':round(float(np.percentile(f,10)),2),'median':round(float(np.median(f)),2),
            'min_at_s_d':[float(S.ravel()[i]),float(D.ravel()[i])],'blockers':{str(a):int(b) for a,b in sorted(zip(u,c),key=lambda t:-t[1])}}
res={'note':'rear = free depth along -n from PCB rear face; front = along +n from PCB front face; mm; s from pin-1 end, d up from header edge',
 'rear_board_all':zone(rear,rw,0,65,0,30),'rear_above_header_d6-30':zone(rear,rw,0,65,6,30),'rear_header_strip_d0-6':zone(rear,rw,0,65,0,6),
 'rear_pin1_half_s0-32':zone(rear,rw,0,32,6,30),'rear_pin40_half_s33-65':zone(rear,rw,33,65,6,30),
 'front_board_all':zone(front,fw,0,65,0,30),'front_d6-30':zone(front,fw,0,65,6,30)}
print(json.dumps(res,indent=1)); json.dump(res,open(sys.argv[1]+'.json','w'),indent=1)
