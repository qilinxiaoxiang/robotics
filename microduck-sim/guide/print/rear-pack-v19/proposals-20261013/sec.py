import sys, numpy as np, trimesh, shapely
G='/Users/xiangzheng/code/robotics/microduck-sim/guide'
sys.path.insert(0, G+'/content/interference-audit')
from ia_lib import CACHE
S = str(__import__('pathlib').Path(__file__).resolve().parent) + '/'
def mesh(k):
    z=np.load(CACHE/f'solid-{k}.npz'); return trimesh.Trimesh(z['v'],z['f'],process=False)
YZ=np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0],[0,0,0,1]],float)
sl,sr,rp=mesh('shell_left'),mesh('shell_right'),mesh('rear_pack')
c12=trimesh.load(S+'community12_guide.stl')
def sec(m,x):
    s=m.section(plane_origin=[x,0,0],plane_normal=[1,0,0])
    if s is None: return shapely.Polygon()
    p,_=s.to_2D(to_2D=YZ); return shapely.unary_union(list(p.polygons_full))
for x in (-31,-28,-25,-22,-20.5,-19.5):
    sh=sec(sl,x).union(sec(sr,x)); c=sec(c12,x); pk=sec(rp,x)
    band=sh.buffer(2.5)
    pad=c.intersection(band).difference(sh).difference(pk)
    print(f'x {x}: shell area {sh.area:.0f} orig {c.area:.0f} pack {pk.area:.0f} pad {pad.area:.1f} pad bounds {np.round(pad.bounds,1)}  gap shell-pack {sh.distance(pk):.2f} shell-orig {sh.distance(c):.2f}')
    if hasattr(pad,'geoms'):
        for g in pad.geoms:
            if g.area>0.5: print('    piece', np.round(g.bounds,1), round(g.area,1), 'touch pack', round(g.distance(pk),2))
