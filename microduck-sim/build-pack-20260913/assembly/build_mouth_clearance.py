from pathlib import Path
import sys,json,numpy as np,trimesh,manifold3d as md
from scipy.spatial.transform import Rotation
HERE=Path(__file__).resolve().parent;OLD=HERE.parents[1]/'hardware-design-20260912/whole-robot-20260912';sys.path.insert(0,str(OLD/'assembly'));from assembly_fk import fk,raw
sys.path.insert(0,str(OLD/'electrical/head-layout'));from geometry import man,tri
O=HERE/'mouth-clearance';O.mkdir(exist_ok=True)
cap=man(trimesh.load(OLD/'electrical/head-layout/final/head_cap_assembly.stl',force='mesh'))
g=next(g for g in fk()[1] if g['body']=='jaw_soft' and g['mesh']=='jaw');jaw=man(raw('jaw').apply_transform(g['local']));pivot=np.array([3.2,0,-18]);bounds=[]
for deg in np.arange(0,30.01,.5):
 R=Rotation.from_euler('y',deg,degrees=True).as_matrix();s=cap^jaw.transform(np.c_[R,pivot-R@pivot])
 if s.volume()>.001:bounds.append(tri(s).bounds)
lo=np.min(np.array(bounds)[:,0,:],0)-.6;hi=np.max(np.array(bounds)[:,1,:],0)+.6
cut=md.Manifold.cube(hi-lo,center=True).translate((hi+lo)/2)
new=cap-cut;m=tri(new);m.export(O/'head-cap-mouth-clearance-assembly.stl')
# Match original head_cap_print orientation using its matching invariant principal axes via builder record.
# Existing print is assembly rotated x=90 degrees (determine rigid transform with trimesh registration over principal axes).
origA=trimesh.load(OLD/'electrical/head-layout/final/head_cap_assembly.stl',force='mesh');origP=trimesh.load(OLD/'electrical/head-layout/final/head_cap_print.stl',force='mesh')
import itertools
best=None
from scipy.spatial import cKDTree
for perm in itertools.permutations(range(3)):
 for sg in itertools.product([-1,1],repeat=3):
  R=np.eye(3)[list(perm)]*np.array(sg)[:,None]
  if np.linalg.det(R)<.9:continue
  v=origA.vertices@R.T;t=origP.bounds.mean(0)-np.array([v.min(0),v.max(0)]).mean(0)
  ds=cKDTree(origP.vertices).query(v+t)[0];score=np.quantile(ds,.95)
  if best is None or score<best[0]:best=(score,R,t)
score,R,t=best;assert score<.05,(score,R,t)
P=np.eye(4);P[:3,:3]=R;P[:3,3]=t;p=m.copy().apply_transform(P);p.apply_translation([0,0,-p.bounds[0,2]]);p.export(O/'head-cap-mouth-clearance-print.stl')
tri(cut).export(O/'removed-clearance-tool.stl')
res={'pivot_inferred_mm':pivot.tolist(),'angle_samples_deg':[0,30,.5],'clearance_cut_bounds_mm':[lo.tolist(),hi.tolist()],'extra_clearance_mm':.6,'removed_volume_mm3':float(cap.volume()-new.volume()),'watertight':m.is_watertight,'connected_solids':len(m.split()),'print_orientation_match_p95_mm':score,'assembly_frame':'jaw_soft mm','frozen_source_unmodified':True,'warning':'Conditional inferred mouth mechanism; original fixed jaw-bearing interference is separate and must not be marked solved by cap trim.'}
(O/'design.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
