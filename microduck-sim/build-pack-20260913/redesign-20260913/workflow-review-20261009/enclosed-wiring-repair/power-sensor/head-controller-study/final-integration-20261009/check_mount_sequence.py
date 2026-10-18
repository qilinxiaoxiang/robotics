from pathlib import Path
import sys,json,hashlib,numpy as np,trimesh,manifold3d as mf
F=Path(__file__).resolve().parent;src=F/'mounted-package.json';r=json.loads(src.read_text());mode=sys.argv[1];checks=[];repairs=[]
def load(q):
 p=Path(q['file']);assert hashlib.sha256(p.read_bytes()).hexdigest()==q['sha256'];m=trimesh.load_mesh(p);m.apply_transform(q['worldTransform'])
 if not m.is_volume:m=m.convex_hull;repairs.append(q['key'])
 assert m.is_volume;v=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=float),np.asarray(m.faces,dtype=np.uint64)));assert v.status()==mf.Error.NoError;return v
def inter(a,b):
 A=np.array(a.bounding_box()).reshape(2,3);B=np.array(b.bounding_box()).reshape(2,3)
 if np.any(A[1]<B[0])or np.any(B[1]<A[0]):return 0,None
 c=a^b;assert c.status()==mf.Error.NoError;v=max(0,c.volume());return v,list(c.bounding_box())if v>1e-6 else None
T=np.array(r['boardNativeToWorld']);P=np.array(r['piCurrentWorldDelta']);features=r['mountFeatures'];rows=r['parts'];results=[]
if mode=='controller-insert':
 selected=[q for q in rows if q['group'] in ['controller','c_receiver']];obs=[q for q in rows if q['group']=='mounts'or q['key']=='current_cap'];axis=-T[:3,2]
elif mode=='pi-insert':
 selected=[q for q in rows if q['group'] in ['pi','micro_receiver']];obs=[q for q in rows if q['group'] in ['controller','c_receiver','mounts']or q['key']=='current_cap'];axis=P[:3,2]
else:
 selected=[];obs=[q for q in rows if q['group'] in (['controller','c_receiver','mounts']if mode=='controller-tools'else['controller','c_receiver','mounts','pi','micro_receiver'])or q['key']=='current_cap']
if selected:
 # Retain each component; compose without boolean union to preserve original contacts.
 body=mf.Manifold.compose([load(q)for q in selected]);assert body.status()==mf.Error.NoError
 for q in obs:
  b=load(q);worst=0;hit=[]
  for d in np.linspace(40,0,81):
   a=body.translate((axis*d).tolist());v,bb=inter(a,b);checks.append({'obstacle':q['key'],'offsetMm':float(d),'volumeMm3':v,'bounds':bb});worst=max(worst,v)
   if v>1e-4:hit.append(float(d))
  results.append({'obstacle':q['key'],'worstMm3':worst,'hitOffsets':hit})
else:
 fs=features[:4]if mode=='controller-tools'else features[4:]
 tools=[]
 for f in fs:
  axis=-T[:3,2]if mode=='controller-tools'else P[:3,2]
  for j,seat in enumerate([f['seat']]if mode=='controller-tools'else f['seats']):
   start=np.array(seat)+axis*(1.6+1.7);end=start+axis*45
   mesh=trimesh.creation.cylinder(radius=1.5,height=45,sections=24);M=trimesh.geometry.align_vectors([0,0,1],axis);M[:3,3]=(start+end)/2;mesh.apply_transform(M);v=mf.Manifold(mf.Mesh64(np.asarray(mesh.vertices,dtype=float),np.asarray(mesh.faces,dtype=np.uint64)));tools.append((f['key']+'-'+str(j),v))
 for q in obs:
  b=load(q)
  for key,a in tools:
   v,bb=inter(a,b);checks.append({'tool':key,'obstacle':q['key'],'volumeMm3':v,'bounds':bb})
hits=[q for q in checks if q['volumeMm3']>1e-4];out={'sourceManifest':str(src),'sourceSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'mode':mode,'stepMm':.5 if selected else None,'checks':checks,'hits':hits,'pairsComplete':True,'conservativeRepairs':repairs,'wholeHeadAccepted':False,'scope':'Detached cap bench installation; camera/face/neck mechanisms are not attached until after boards. Controller seated and fastened before Pi; connectors preplugged.'};(F/(mode+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'mode':mode,'checks':len(checks),'hits':len(hits),'first':hits[:8]},indent=2))
