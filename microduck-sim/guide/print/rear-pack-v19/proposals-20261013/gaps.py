import sys, numpy as np, trimesh, shapely
G='/Users/xiangzheng/code/robotics/microduck-sim/guide'
sys.path.insert(0, G+'/content/interference-audit')
from ia_lib import CACHE
S=str(__import__('pathlib').Path(__file__).resolve().parent)+'/'
def mesh(k):
    z=np.load(CACHE/f'solid-{k}.npz'); return trimesh.Trimesh(z['v'],z['f'],process=False)
YZ=np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0],[0,0,0,1]],float)
sl,sr,rp=mesh('shell_left'),mesh('shell_right'),mesh('rear_pack'); c12=trimesh.load(S+'community12_guide.stl')
def sec(m,x):
    s=m.section(plane_origin=[x,0,0],plane_normal=[1,0,0])
    if s is None: return shapely.Polygon()
    p,_=s.to_2D(to_2D=YZ); return shapely.unary_union(list(p.polygons_full))
regions={'roof (z>33)':shapely.box(-33,33,33,45),'shoulder/step (z 18..33)':shapely.box(-33,18,33,33),'lower (z<18)':shapely.box(-33,-50,33,18)}
for name,m,x in (('V1.8 pack plate',rp,-20.0),('V1.8 pack plate',rp,-20.9),('original part',c12,-21.5),('original part',c12,-24),('original part',c12,-28)):
    sh=sec(sl,x).union(sec(sr,x)); p=sec(m,x)
    out=[]
    for rn,box in regions.items():
        a=p.intersection(box); b=sh
        out.append(f'{rn}: {a.distance(b):.2f}' if not a.is_empty else f'{rn}: none')
    print(f'{name} x={x}: ', '; '.join(out))
# where exactly the step blocks are and the shoulder above
x=-20.0; sh=sec(sl,x); p=sec(rp,x)
blk=sh.intersection(shapely.box(15,15,33,33)); print('left shell inner block at x -20', np.round(blk.bounds,2))
sho=p.intersection(shapely.box(15,25,33,45)); print('pack plate shoulder (|y|>15, z>25)', np.round(sho.bounds,2))
for xx in (-30,-26,-23,-21.5,-20,-19,-18):
    b=sec(sl,xx).intersection(shapely.box(15,15,33,32)); print('  step block at x',xx, np.round(b.bounds,2) if not b.is_empty else None)
