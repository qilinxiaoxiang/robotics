"""Official Rev2 body11.5; conservative standard-end16 width20mm+3mm taper.
Only width-dependent clearance sensitivity. Does not establish installed revision.
Same exact200mm developed material map and fixed lowered Pi as inner-entry baseline.
"""
from pathlib import Path
import os,json,hashlib,math
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
import developable_ribbon_inner_entry as dr
D=Path(__file__).resolve().parent
fit=json.loads((D/'inner-entry-ribbon-fit.json').read_text());p,t,w,L,bends,ops=dr.family(np.array(fit['parameters']))
def width(s):return 11.5 if s<=177 else (11.5+(s-177)*1.5 if s<180 else 16.)
def build(s0=0,s1=200,spacing=.35):
 ss=np.unique(np.r_[np.linspace(s0,s1,math.ceil((s1-s0)/spacing)+1),[s for s in [177,180] if s0<s<s1]]);vv=np.linspace(-.5,.5,17);coords=[];norms=[]
 for s in ss:
  for f in vv:
   q,n=dr.material_map(s,f*width(s),bends,(p,t,w,L));coords.append(q);norms.append(n)
 coords=np.array(coords);norms=np.array(norms);verts=np.r_[coords-.3*norms,coords+.3*norms];N=len(coords);nv=len(vv);ns=len(ss);faces=[]
 for i in range(ns-1):
  for j in range(nv-1):
   a=i*nv+j;b=a+1;c=b+nv;d=a+nv;faces.extend([[a,c,b],[a,d,c],[a+N,b+N,c+N],[a+N,c+N,d+N]])
 for i in range(ns-1):
  for j in [0,nv-1]:a=i*nv+j;b=a+nv;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 for i in [0,ns-1]:
  for j in range(nv-1):a=i*nv+j;b=a+1;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 m=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(m);assert m.is_watertight
 solid=mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)));assert solid.status()==mf.Error.NoError
 return solid,m
if __name__=='__main__':
 solid,m=build();assert len(solid.decompose())==1
 out=D/'sc1892-rev2-inner-entry-diagnostic-world.stl';m.export(out)
 r={'integrationReady':False,'accepted':False,'scope':'Rev2 width sensitivity only; full obstacle, self, insertion and strain acceptance remain incomplete. Installed revision unknown.','sourceRevision':'RP-009201-PC-1 PCN36 camera cables Rev2','bodyWidthMm':11.5,'standardEndWidthMm':16,'standardFullWidthEndLengthReceivingMm':20,'taperLengthReceivingMm':3,'endShapeBoundary':'20mm full-width standard end plus3mm taper are receiving bounds, not manufacturer-stated reinforcement measurements.','thicknessReceivingMm':.6,'intrinsicMaterialLengthMm':L,'oneBody':len(solid.decompose())==1,'watertight':bool(m.is_watertight),'boundsMm':m.bounds.tolist(),'sourceHashes':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [Path(__file__),D/'developable_ribbon_inner_entry.py',D/'inner-entry-ribbon-fit.json',out]}}
 (D/'rev2-inner-entry-diagnostic.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
