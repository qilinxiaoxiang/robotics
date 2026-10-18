from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf,gc
D=Path(__file__).resolve().parent;M=D.parent;x=json.loads((D/'joint-right.json').read_text());hip=json.loads((M/'hip-coiled-right.json').read_text());rows=[]
for w in x['strands']:
 assert hashlib.sha256(Path(w['file']).read_bytes()).hexdigest()==w['sha256'],w['key']
 rows.append({'key':w['key'],'route':w['routeId'],'file':w['file'],'hash':w['sha256'],'bounds':w['boundsMm']})
for w in hip['strands']:
 f=Path(w['file']);f=f if f.is_absolute()else M/f;m=trimesh.load_mesh(f);rows.append({'key':'hip-'+str(w['id']),'route':'ttl-05-04','file':str(f),'hash':w['sha256'],'bounds':m.bounds.tolist()})
def solid(r):
 m=trimesh.load_mesh(r['file']);assert m.is_volume;return mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)))
checks=[]
for i,p in enumerate(rows):
 a=None
 for q in rows[i+1:]:
  bb=np.array(p['bounds']);cc=np.array(q['bounds']);v=0.;bound=None
  if not(np.any(bb[1]<cc[0])or np.any(cc[1]<bb[0])):
   if a is None:a=solid(p)
   b=solid(q);c=a^b;v=c.volume();bound=list(c.bounding_box())if v>1e-7 else None
  row={'a':p['key'],'b':q['key'],'volumeMm3':v,'bounds':bound};checks.append(row)
  if v>1e-7:print(row,flush=True)
 del a;gc.collect()
out={'passed':all(r['volumeMm3']<1e-7 for r in checks),'pairs':checks,'sourceHashes':{str(D/'joint-right.json'):hashlib.sha256((D/'joint-right.json').read_bytes()).hexdigest(),str(M/'hip-coiled-right.json'):hashlib.sha256((M/'hip-coiled-right.json').read_bytes()).hexdigest()}};(D/'joint-cross-right.json').write_text(json.dumps(out,indent=2));print('passed',out['passed'])
