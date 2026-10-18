"""Camera saddle matched to CURRENT 3MF object 6; mm; no assumed full robot assembly."""
from pathlib import Path
import json, numpy as np, trimesh
P=Path(__file__).resolve().parent
SRC=P/'source-head-6.npz'
d=np.load(SRC); original=trimesh.Trimesh(d['vertices'],d['faces'])
# Original local coordinates: camera base Z points along original +Y.
# Camera base origin at original (15,24,0); its X maps +Z, Y maps +X.
xs=np.linspace(5,25,41);zs=np.linspace(-18,18,73)
coords=np.array([[x,60,z] for x in xs for z in zs]); directions=np.tile([0,-1,0],(len(coords),1))
loc,ridx,_=original.ray.intersects_location(coords,directions)
outer=np.full(len(coords),np.nan);inner=outer.copy()
for i in range(len(coords)):
 vals=np.sort(loc[ridx==i,1]); assert len(vals)==2,(i,vals); inner[i],outer[i]=vals

def height_solid(lower,upper):
 N=len(coords);v=np.vstack([np.c_[coords[:,0],lower,coords[:,2]],np.c_[coords[:,0],upper,coords[:,2]]]);f=[];nz=len(zs)
 for a in range(len(xs)-1):
  for b in range(nz-1):
   i=a*nz+b;j=i+nz
   f.extend([(i,i+1,j),(i+1,j+1,j),(i+N,j+N,i+1+N),(i+1+N,j+N,j+1+N)])
 boundary=list(range(nz))+[a*nz+nz-1 for a in range(1,len(xs))]+list(range(N-2,N-nz-1,-1))+[a*nz for a in range(len(xs)-2,0,-1)]
 for a,b in zip(boundary,boundary[1:]+boundary[:1]): f.extend([(a,a+N,b),(b,a+N,b+N)])
 m=trimesh.Trimesh(v,f);m.fix_normals();assert m.is_watertight;return m
saddle=height_solid(outer+.18,np.full(len(coords),24.))
backing=height_solid(np.full(len(coords),14.),inner-.18)
# Cylinders aligned with original Y.
holes=[]
for z in [-11,11]:
 h=trimesh.creation.cylinder(radius=1.7,height=50,sections=64); h.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]));h.apply_translation([15,10,z]);holes.append(h)
cutters=trimesh.boolean.union(holes,engine='manifold')
saddle=trimesh.boolean.difference([saddle,cutters],engine='manifold');backing=trimesh.boolean.difference([backing,cutters,original],engine='manifold')
slot=trimesh.creation.box([3,30,20]);slot.apply_translation([29,20,0])
head=trimesh.boolean.difference([original,cutters,slot],engine='manifold')
parts={'head-camera-holes':head,'camera-conformal-saddle':saddle,'camera-inner-backing':backing}
# Print coordinates use original Y -> Z; flip saddle so its flat top is on the bed.
rot=np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1.]])
result={}
for name,m in parts.items():
 assert m.is_watertight and m.is_volume and len(m.split())==1,(name,m.is_watertight,m.volume,len(m.split()))
 m.export(P/(name+'-assembly.stl'))
 q=m.copy();q.apply_transform(rot)
 if name=='camera-conformal-saddle':q.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
 q.apply_translation([-q.bounds.mean(0)[0],-q.bounds.mean(0)[1],-q.bounds[0,2]])
 q.export(P/(name+'.stl'))
 result[name]={'watertight':bool(m.is_watertight),'single_body':True,'volume_mm3':float(m.volume),'print_dimensions_mm':q.extents.tolist()}
for n,m in [('saddle',saddle),('backing',backing)]:
 intersection=trimesh.boolean.intersection([original,m],engine='manifold');result[n+'_original_intersection_mm3']=float(intersection.volume) if not intersection.is_empty else 0
assert result['saddle_original_intersection_mm3'] < .01
assert result['backing_original_intersection_mm3'] < .01
result['camera_base_to_original_head_4x4']=[[0,1,0,15],[0,0,1,24],[1,0,0,0],[0,0,0,1]]
result['fasteners']='2x M3x20 + M3 washers + locknuts; verify actual screw protrusion before power-up'
result['source']='AI-FanGe/Microduck-build-tutorial 4967821 microduck3D打印.3mf object 6, sha256 e78a329d264bc5050c00b8ff6a37d6b1195b6ea128bd9760492f31b4a91cc71e'
result['boundary']='Only head-shell local assembly validated; assembled robot and moving joint clearance not available.'
(P/'validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
