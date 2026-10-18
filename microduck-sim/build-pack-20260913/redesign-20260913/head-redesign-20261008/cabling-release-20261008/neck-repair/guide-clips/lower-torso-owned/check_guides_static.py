from pathlib import Path
import sys,json,base64,gc
D=Path(__file__).resolve().parent;N=D.parent.parent;H=N.parent.parent;sys.path.insert(0,str(N))
from short_path_worker import guard,save,sha
guard()
import numpy as np,trimesh,manifold3d as mf
C=H/'usb-access/usb-repair/robot-source-cache';idx=json.loads((C/'index.json').read_text());plan=json.loads((D/'candidate.json').read_text());rows=[]
def solid(t):
 s=mf.Manifold(mf.Mesh64(np.asarray(t.vertices,np.float64),np.asarray(t.faces,np.uint32)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
for guide in plan['guides']:
 for part in guide['parts']:
  tm=trimesh.load(part['mesh'],force='mesh',process=False);uv,ui=np.unique(tm.vertices,axis=0,return_inverse=True);tm=trimesh.Trimesh(uv,ui[tm.faces],process=False);a=solid(tm);b0=tm.bounds
  for key,p in idx['parts'].items():
   data=json.loads((C/p).read_text());b1=np.array(data['bounds']);r={'part':part['key'],'obstacle':key,'guideSha256':part['sha256'],'obstacleSha256':sha(C/p),'intersectionMm3':0,'aabbDisjoint':bool(np.any(b0[0]>=b1[1]) or np.any(b1[0]>=b0[1]))}
   if not r['aabbDisjoint']:
    v=np.frombuffer(base64.b64decode(data['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(data['indexB64']),'<u4').reshape(-1,3);t=trimesh.Trimesh(v,f,process=True);b=solid(t);hit=a^b;r['intersectionMm3']=max(0,hit.volume());r['bounds']=list(hit.bounding_box()) if hit.volume()>1e-6 else None;r['sourceWatertight']=bool(t.is_watertight);r['manifoldStatus']='NoError';del b,t,hit;gc.collect()
   rows.append(r)
  del a,tm;gc.collect()
out={'passed':all(r['intersectionMm3']<1e-5 for r in rows),'pairs':len(rows),'hits':[r for r in rows if r['intersectionMm3']>=1e-5],'rows':rows,'candidateHash':sha(D/'candidate.json'),'scope':'All103 canonical source obstacles, neutral; revised head and dynamic checks still separate.'};save(D/'static.json',out);print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
