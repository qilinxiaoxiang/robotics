from context import *
files=[D/'lower-entry-check.json',D/'imu-extension-check.json'];parts=[];sources={}
for f in files:
 sources[str(f)]=sha(f)
 for r in read(f)['rows']:
  if 'file' not in r:raise ValueError(r)
  parts.append(r)
  if r.get('splice'):parts.append(r['splice'])
solids=[]
for p in parts:
 assert sha(p['file'])==p['sha256'];m=trimesh.load_mesh(p['file']);solids.append((p,m.bounds,solid(m)))
rows=[]
for i,(a,A,ma) in enumerate(solids):
 for b,B,mb in solids[i+1:]:
  if np.any(A[1]<B[0])or np.any(B[1]<A[0]):v=0;cb=None
  else:
   c=ma^mb;assert c.status()==mf.Error.NoError;v=max(c.volume(),0);cb=list(c.bounding_box())if v>1e-6 else None
  own=a.get('splice',{}).get('key')==b['key'] or b.get('splice',{}).get('key')==a['key']
  rows.append({'a':a['key'],'b':b['key'],'volume':v,'bounds':cb,'sameNetInsideOwnSplice':own,'passed':v<=1e-6 or own})
hits=[r for r in rows if not r['passed']];print(json.dumps(hits,indent=2));(D/'bridge-pair-check.json').write_text(json.dumps({'sourceHashes':sources|{str(Path(__file__)):sha(__file__)},'parts':len(parts),'pairs':len(rows),'passed':not hits,'rows':rows,'hits':hits},indent=2))
