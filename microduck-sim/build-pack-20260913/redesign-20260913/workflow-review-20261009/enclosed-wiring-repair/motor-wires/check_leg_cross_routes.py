from pathlib import Path
import json,hashlib,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).parent;P=D/'leg-local-manifest.json';x=json.loads(P.read_text());parts=x['parts'];rows=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
 f=Path(p['file']);assert sha(f)==p['sha256'];m=trimesh.load_mesh(f);assert m.is_volume,p['key'];a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(a.status())=='Error.NoError'and a.volume()>0;return a
for i,p in enumerate(parts):
 a=None
 for q in parts[i+1:]:
  if p['routeId']==q['routeId']:continue
  row={'a':p['key'],'b':q['key'],'aSha256':p['sha256'],'bSha256':q['sha256']};bb=np.array(p['expectedFinalBoundsMm']);cc=np.array(q['expectedFinalBoundsMm'])
  if np.any(bb[1]<cc[0])or np.any(cc[1]<bb[0]):row.update(method='AABB separated',overlapMm3=0.)
  else:
   if a is None:a=load(p)
   b=load(q);c=a^b;v=c.volume();row.update(method='valid solid exact mesh intersection',overlapMm3=v,bounds=list(c.bounding_box())if v>1e-7 else None);del b,c
  rows.append(row)
  if row['overlapMm3']>1e-7:print('FAIL',row,flush=True)
 del a;gc.collect()
passed=all(r['overlapMm3']<1e-7 for r in rows);out={'passed':passed,'sourceManifestSha256BeforeGate':sha(P),'partHashes':{p['key']:p['sha256']for p in parts},'pairCount':len(rows),'exactCount':sum(r['method'].startswith('valid')for r in rows),'rows':rows,'scope':'Only newly combined distinct-route static pairs. Existing within-route and original rigid-obstacle receipts are inherited, not re-run.'};f=D/'leg-cross-route-static.json';f.write_text(json.dumps(out,indent=2)+'\n');print(passed,out['pairCount'],out['exactCount'])
if passed:
 x['status']='SIX LOCAL LEG CABLES NEUTRAL STATIC CLEAR';x['localStaticPassed']=True;x['crossRouteReceipt']=str(f);x['sourceHashes'][str(f.resolve())]=sha(f);P.write_text(json.dumps(x,indent=2)+'\n')
