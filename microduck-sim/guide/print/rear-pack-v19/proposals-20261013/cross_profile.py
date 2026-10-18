import sys, numpy as np, trimesh
sys.path.insert(0,'/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit')
from ia_lib import CACHE
def solid(k):
    z=np.load(CACHE/f'solid-{k}.npz'); return trimesh.Trimesh(z['v'],z['f'],process=False)
X,Z=-38.0,34.96
ys=np.arange(-30,30.01,0.1)
R=[0.0,0.8,1.0,1.1,1.6,1.75,1.9,2.0,2.2,2.5,3.0]
for k in ('shell_left','shell_right'):
    m=solid(k)
    rows={}
    for r in R:
        pts=[]
        for a in np.linspace(0,2*np.pi,12,endpoint=False) if r>0 else [0]:
            pts.append(np.c_[np.full_like(ys,X+r*np.cos(a)),ys,np.full_like(ys,Z+r*np.sin(a))])
        P=np.vstack(pts); inside=m.contains(P).reshape(-1,len(ys))
        rows[r]=inside.mean(0)  # fraction of ring in material
    # summarise runs: at each y, smallest r with any material
    prev=None; start=None
    def state(i):
        if rows[0.0][i]>0.5: return 'solid@axis'
        for r in R[1:]:
            if rows[r][i]>0.5: return f'hole d<{2*r:.1f}'
        return 'free>6'
    for i,y in enumerate(ys):
        s=state(i)
        if s!=prev:
            if prev is not None: print(k, f'{ys[start]:6.1f}..{ys[i-1]:6.1f}', prev)
            prev=s; start=i
    print(k, f'{ys[start]:6.1f}..{ys[-1]:6.1f}', prev); print()
