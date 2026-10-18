from pathlib import Path
import os,json,hashlib,math
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
import developable_ribbon_roof_fold as dr
D=Path(__file__).resolve().parent;r=json.loads((D/'roof-fold-ribbon-fit.json').read_text());x=np.array(r['parameters']);p,t,w,L,bends,ops=dr.family(x)
def slab(s0,s1):
 ss=np.linspace(s0,s1,max(2,int(math.ceil((s1-s0)/.25))+1));vv=np.linspace(-8,8,17);coords=[];norms=[]
 for s in ss:
  for v in vv:
   q,n=dr.material_map(s,v,bends,(p,t,w,L));coords.append(q);norms.append(n)
 coords=np.array(coords);norms=np.array(norms);verts=np.r_[coords-.3*norms,coords+.3*norms];N=len(coords);nv=len(vv);ns=len(ss);faces=[]
 for i in range(ns-1):
  for j in range(nv-1):
   a=i*nv+j;b=a+1;c=b+nv;d=a+nv;faces.extend([[a,c,b],[a,d,c],[a+N,b+N,c+N],[a+N,c+N,d+N]])
 for i in range(ns-1):
  for j in [0,nv-1]:a=i*nv+j;b=a+nv;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 for i in [0,ns-1]:
  for j in range(nv-1):a=i*nv+j;b=a+1;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 m=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(m);assert m.is_watertight
 return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
edges=np.linspace(0,L,101);parts=[slab(a,b) for a,b in zip(edges,edges[1:])];bounds=[np.array(q.bounding_box()).reshape(2,3) for q in parts];tested=0;bbclear=0;hits=[];mingap=5.;gappair=None
for i,a in enumerate(parts):
 for j in range(i+2,len(parts)):
  tested+=1;ba,bb=bounds[i],bounds[j];sep=np.maximum(ba[0]-bb[1],bb[0]-ba[1]);d=float(np.linalg.norm(np.maximum(sep,0)))
  if np.any(sep>=0):bbclear+=1
  else:
   v=max(0,(a^parts[j]).volume())
   if v>1e-5:hits.append({'a':i,'b':j,'overlapMm3':v})
  if edges[j]-edges[i+1]>=10 and d<mingap:
   gap=float(a.min_gap(parts[j],mingap));
   if gap<mingap:mingap=gap;gappair=[i,j]
# Numerically test the isometry of the actual map, not the straight-line sweep.
errs=[]
for s in np.linspace(.1,L-.1,151):
 for v in [-7.5,-4,0,4,7.5]:
  h=1e-5;ds=(dr.material_map(s+h,v,bends,(p,t,w,L))[0]-dr.material_map(s-h,v,bends,(p,t,w,L))[0])/(2*h);dv=(dr.material_map(s,v+h,bends,(p,t,w,L))[0]-dr.material_map(s,v-h,bends,(p,t,w,L))[0])/(2*h)
  errs.append(max(abs(ds@ds-1),abs(dv@dv-1),abs(ds@dv)))
expected=(100-1)*(100-2)//2;out={'accepted':bool(not hits and tested==expected and max(errs)<1e-6),'scope':'Material geometry and self intersection only; no source obstacle or installation acceptance','expectedNonadjacentPairs':expected,'completedNonadjacentPairs':tested,'aabbClearPairs':bbclear,'overlaps':hits,'minimumNonlocalGapMm':mingap,'minimumGapPair':gappair,'distanceExclusion':'Distance excludes <10mm material separation; intersection excludes adjacent shared-face cells only.','isometrySampleCount':len(errs),'maximumFirstFundamentalFormError':max(errs),'analyticMaterialLengthMm':L,'sourceHashes':{str(q.resolve()):hashlib.sha256(q.read_bytes()).hexdigest() for q in [Path(__file__),D/'developable_ribbon_roof_fold.py',D/'roof-fold-ribbon-fit.json',D/'sc1892-roof-fold-receiving-world.stl']}}
(D/'roof-fold-material-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='sourceHashes'},indent=2))
