import sys, numpy as np, trimesh
sys.path.insert(0,'/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit')
from ia_lib import CACHE
def solid(k):
    z=np.load(CACHE/f'solid-{k}.npz'); return trimesh.Trimesh(z['v'],z['f'],process=False)
X,Z=-38.0,34.96
rs=np.arange(0,8.01,0.05); angs=np.linspace(0,2*np.pi,36,endpoint=False)
for k,yr in (('shell_left',np.arange(0.5,31,1.0)),('shell_right',np.arange(-29.5,0,1.0))):
    m=solid(k)
    print(k)
    for y in yr:
        P=np.array([[X+r*np.cos(a),y,Z+r*np.sin(a)] for a in angs for r in rs])
        ins=m.contains(P).reshape(len(angs),len(rs))
        hole=[];outer=[]
        for i,a in enumerate(angs):
            row=ins[i]; idx=np.where(row)[0]
            if len(idx)==0: hole.append(9);outer.append(9);continue
            r0=rs[idx[0]]; after=np.where(~row[idx[0]:])[0]
            r1=rs[idx[0]+after[0]] if len(after) else 8
            hole.append(r0); outer.append(r1)
        hole=np.array(hole); outer=np.array(outer)
        j=np.argmin(outer)
        print(f'  y {y:5.1f}: hole d {2*hole.min():.2f}-{2*hole.max():.2f}  outer surface min r {outer.min():.2f} at {np.degrees(angs[j]):.0f} deg -> wall after 4.4 bore {outer.min()-2.2:.2f}')
