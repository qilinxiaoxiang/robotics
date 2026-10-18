from pathlib import Path
import json,hashlib,gc,numpy as np,trimesh,manifold3d as mf
F=Path(__file__).resolve().parent
source=F/'integrated-rigid-package.json';r=json.loads(source.read_text());ports=json.loads((F/'current-head-interfaces.json').read_text())['piPorts'];p1=next(q for q in ports if q['physicalPin']==1);p2=next(q for q in ports if q['physicalPin']==2)
n=np.array(p1['outwardAxis']);u=np.array(p2['femaleSeatedFrontWorldMm'])-p1['femaleSeatedFrontWorldMm'];u/=np.linalg.norm(u);v=np.array([0.,-1.,0.]);origin=np.array(p1['femaleSeatedFrontWorldMm'])+1.27*u+24.13*v
R=np.column_stack([u,v,n]);T=np.eye(4);T[:3,:3]=R;T[:3,3]=origin
# Manufacturer maxima:51.3+.3 x 5+.2 x8.5+.15. Axial full seating at male plastic face.
def box(lo,hi):
 m=trimesh.creation.box(np.array(hi)-lo);m.apply_translation((np.array(hi)+lo)/2);m.apply_transform(T);return m
parts=[]
def add(key,m):
 f=F/(key+'.stl');m.export(f);parts.append({'key':key,'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'worldTransform':np.eye(4).tolist(),'group':'right_angle_header'})
add('gpio-smt-housing',box([-2.6,-25.8,0],[2.6,25.8,4.1]))
for col in range(20):
 for row in range(2):
  y=-24.13+2.54*col;side=1 if row else -1
  add('gpio-smt-tail-%02d'%(col*2+row+1),box(sorted([side*2.5,side*4])[0:1]+[y-.25,3.5],sorted([side*2.5,side*4])[1:]+[y+.25,4.1]))
newports=[]
for q in ports:
 pin=q['physicalPin'];row=(pin-1)%2;col=(pin-1)//2;y=-24.13+2.54*col;side=1 if row else -1
 # Short insulated wire leaves solder tab towards board normal, past male tip, then routes independently.
 x=side*3.65;z=4.1;rad=.6 if pin in [1,3,5,9] else .75
 add('gpio-smt-solder-pin-%02d'%pin,box([x-rad,y-rad,z-.5],[x+rad,y+rad,7.1]))
 start=T@np.array([x,y,7.1,1]);newports.append({'physicalPin':pin,'wireExitWorldMm':start[:3].tolist(),'outwardAxis':n.tolist(),'wireReceivingDiameterMm':rad*2,'connection':'insulated solder lead on existing 2.54mm side pad; original male header unmodified'})
rows=[q for q in r['parts']if 'gpio_pin_'not in q['key']];checks=[];conservative=[]
def solid(m):
 if not m.is_volume:m=m.convex_hull
 assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
mov={q['key']:solid(trimesh.load_mesh(q['file']))for q in parts}
for q in rows:
 assert hashlib.sha256(Path(q['file']).read_bytes()).hexdigest()==q['sha256'];m=trimesh.load_mesh(q['file']);m.apply_transform(q['worldTransform'])
 if not m.is_volume:conservative.append(q['key'])
 b=solid(m);B=np.array(b.bounding_box()).reshape(2,3)
 for k,a in mov.items():
  A=np.array(a.bounding_box()).reshape(2,3);sep=np.any(A[1]<B[0])or np.any(B[1]<A[0]);c=None if sep else a^b
  if c is not None:assert c.status()==mf.Error.NoError
  vv=0 if sep else max(0,c.volume());checks.append({'moving':k,'obstacle':q['key'],'volumeMm3':vv,'boundsMm':list(c.bounding_box())if vv>1e-6 else None})
 del b;gc.collect()
hits=[q for q in checks if q['volumeMm3']>1e-6];out={'sourceManifest':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'drawing':str(F/'sources/header-2187.jpg'),'drawingSha256':hashlib.sha256((F/'sources/header-2187.jpg').read_bytes()).hexdigest(),'worldFrame':T.tolist(),'parts':parts,'piPorts':newports,'expectedPairs':len(rows)*len(parts),'completedPairs':len(checks),'hits':hits,'checks':checks,'conservativeRepairs':conservative,'accepted':False,'notes':['Whole40 tail envelope is deliberately conservative, metal holes and separated tail spaces not subtracted.','Board male header mating contacts must be individually classified; no automatic exemption.','Original12 straight female housings replaced only in this isolated diagnostic.','Ordinary solder tails with individually insulated leads, not mating short tails to Dupont female.']};(F/'smt-header-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'hits':hits,'pairs':len(checks)},indent=2))
