"""Free height in front of the A7Z component side, measured along the board normal n from the PCB top face,
on a 0.5 mm grid over the board (s along the board from the pin-1 end, d up from the header edge).
Obstacles: every head part that is not the A7Z itself. Output JSON + per-zone minima."""
import json, sys, numpy as np, trimesh
A='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/a7z-head/'
W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
F='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/face-a7z/'
fr=json.load(open(A+'checks.json'))['frame']
O=np.array(fr['origin']); ES=np.array(fr['es']); ED=np.array(fr['ed']); N=np.array(fr['n']); T=1.6
w=lambda s,d,h: O+s*ES+d*ED+h*N
obs={'camera':F+'camera_13m214.stl','face':F+'face_panel_a7z.stl','trim':F+'eye_trim_a7z.stl','cap':A+'head_cap_a7z-world.stl',
     'clip_cap':A+'clip_cap_a7z-world.stl','head_bottom':W+'head_bottom.stl','jaw_frame':W+'jaw_frame.stl','antenna':W+'antenna.stl',
     'coax':W+'antenna_coax.stl','ribbon':W+'camera_ribbon.stl','amplifier':W+'amplifier.stl','clip_head':W+'clip_head.stl'}
M={k:trimesh.load(p) for k,p in obs.items()}
ss=np.arange(0.25,65,0.5); ds=np.arange(0.25,30,0.5)
S,D=np.meshgrid(ss,ds,indexing='ij'); pts=np.array([w(s,d,T+0.01) for s,d in zip(S.ravel(),D.ravel())])
free=np.full(len(pts),60.0); who=np.array(['']*len(pts),dtype=object)
for k,m in M.items():
    loc,ri,_=m.ray.intersects_location(pts,np.tile(N,(len(pts),1)),multiple_hits=False)
    if len(ri)==0: continue
    dist=((loc-pts[ri])@N)
    better=dist<free[ri]; free[ri[better]]=dist[better]; who[ri[better]]=k
free=free.reshape(S.shape); who=who.reshape(S.shape)
def zone(s0,s1,d0,d1):
    m=(S>=s0)&(S<=s1)&(D>=d0)&(D<=d1); f=free[m]; u,c=np.unique(who[m],return_counts=True)
    return {'min':round(float(f.min()),2),'p10':round(float(np.percentile(f,10)),2),'median':round(float(np.median(f)),2),'blockers':{str(a):int(b) for a,b in sorted(zip(u,c),key=lambda t:-t[1])}}
res={'note':'free height along board normal from PCB top face (h=1.6) to first non-A7Z part, mm',
     'soc_footprint_s20.4-35.8_d10-25.3':zone(20.4,35.8,10.0,25.3),
     'heatsink15_centred_s20.6-35.6_d10.2-25.2':zone(20.6,35.6,10.2,25.2),
     'board_minus_header_strip_s0-65_d7-30':zone(0,65,7,30),
     'board_all':zone(0,65,0,30)}
json.dump(res,open(sys.argv[1],'w'),indent=1); print(json.dumps(res,indent=1))
np.save(sys.argv[1].replace('.json','.npy'),free)
