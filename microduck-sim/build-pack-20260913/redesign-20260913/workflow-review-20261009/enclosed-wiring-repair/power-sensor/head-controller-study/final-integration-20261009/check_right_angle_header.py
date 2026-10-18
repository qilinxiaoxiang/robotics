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
add('gpio-right-angle-housing',box([-2.6,-25.8,0],[2.6,25.8,8.65]))
# Conservatively includes all 40 uncut 3.2mm solder tails and right-angle bends.
# Tails extend toward+u (upward along Pi short axis). Max axial 8.65+1.8+2.64=13.09.
add('gpio-right-angle-40-tail-envelope',box([-.0,-25.8,8.65],[6.2,25.8,13.09]))
newports=[]
for q in ports:
 pin=q['physicalPin'];row=(pin-1)%2;col=(pin-1)//2;y=-24.13+2.54*col;z=10.45+row*2.64
 # One insulated solder splice at each used pad; no Dupont housing stacked onto short tail.
 add('gpio-solder-pin-%02d'%pin,box([2.6,y-.8,z-.8],[9.2,y+.8,z+.8]))
 start=T@np.array([9.2,y,z,1]);newports.append({'physicalPin':pin,'wireExitWorldMm':start[:3].tolist(),'outwardAxis':u.tolist(),'wireReceivingDiameterMm':1.6,'connection':'soldered insulated lead on ordinary 2.54mm right-angle header tail'})
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
hits=[q for q in checks if q['volumeMm3']>1e-6];out={'sourceManifest':str(source),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'drawing':str(F/'sources/header-2823.pdf'),'drawingSha256':hashlib.sha256((F/'sources/header-2823.pdf').read_bytes()).hexdigest(),'worldFrame':T.tolist(),'parts':parts,'piPorts':newports,'expectedPairs':len(rows)*len(parts),'completedPairs':len(checks),'hits':hits,'checks':checks,'conservativeRepairs':conservative,'accepted':False,'notes':['Whole40 tail envelope is deliberately conservative, metal holes and separated tail spaces not subtracted.','Board male header mating contacts must be individually classified; no automatic exemption.','Original12 straight female housings replaced only in this isolated diagnostic.','Ordinary solder tails with individually insulated leads, not mating short tails to Dupont female.']};(F/'right-angle-header-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'hits':hits,'pairs':len(checks)},indent=2))
