from pathlib import Path
import json,hashlib,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();top=json.loads((M/'active-topology.json').read_text());rows=[];sources={}
for side in ['right','left']:
 f=D/f'joint-{side}.json';x=json.loads(f.read_text());sources[str(f)]=sha(f)
 for w in x['strands']:
  assert sha(w['file'])==w['sha256'];rows.append({'key':w['key'],'routeId':w['routeId'],'file':w['file'],'sha256':w['sha256'],'bounds':w['boundsMm'],'kind':'wire','ownPorts':[f'motor-{w[e]["motor"]}-socket-{w[e]["sourceSocket"]}'for e in['source','target']]})
  for end in['source','target']:
   p=w[end];key=f'motor-{p["motor"]}-socket-{p["sourceSocket"]}'
   if any(r['key']==key for r in rows):continue
   bb=np.array(p['housingLocalBounds']);m=trimesh.creation.box(bb[1]-bb[0]);m.apply_translation(bb.mean(axis=0));m.apply_transform(p['transform']);of=D/f'{key}-housing.stl';m.export(of);rows.append({'key':key,'routeId':w['routeId'],'file':str(of),'sha256':sha(of),'bounds':m.bounds.tolist(),'kind':'housing','port':p})
 f=M/f'hip-coiled-{side}.json';x=json.loads(f.read_text());sources[str(f)]=sha(f)
 for w in x['strands']:
  m=trimesh.load_mesh(w['file']);rows.append({'key':x['routeId']+'-'+str(w['id']),'routeId':x['routeId'],'file':w['file'],'sha256':w['sha256'],'bounds':m.bounds.tolist(),'kind':'wire','ownPorts':[]})
 rr=next(r for r in top['routes']if r['id']==x['routeId'])
 for pk in[rr['fromPort'],rr['toPort']]:
  p=top['ports'][pk];bb=np.array(p['housingLocalBounds']);m=trimesh.creation.box(bb[1]-bb[0]);m.apply_translation(bb.mean(axis=0));m.apply_transform(p['transform']);of=D/f'{pk}-housing.stl';m.export(of);rows.append({'key':pk,'routeId':x['routeId'],'file':str(of),'sha256':sha(of),'bounds':m.bounds.tolist(),'kind':'housing','port':p})
 for r in rows:
  if r['routeId']==x['routeId']and r['kind']=='wire':r['ownPorts']=[rr['fromPort'],rr['toPort']]
def solid(r):
 assert sha(r['file'])==r['sha256'];m=trimesh.load_mesh(r['file']);assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
checks=[]
for i,p in enumerate(rows):
 a=None
 for q in rows[i+1:]:
  bb=np.array(p['bounds']);cc=np.array(q['bounds']);v=0.;bounds=None;culled=np.any(bb[1]<cc[0])or np.any(cc[1]<bb[0])
  if not culled:
   if a is None:a=solid(p)
   b=solid(q);c=a^b;assert c.status()==mf.Error.NoError;v=c.volume();bounds=list(c.bounding_box())if v>1e-7 else None
  own=(p['kind']=='wire'and q['key']in p['ownPorts'])or(q['kind']=='wire'and p['key']in q['ownPorts'])
  row={'a':p['key'],'b':q['key'],'volumeMm3':v,'bounds':bounds,'ownWireReceivingShoulder':own,'aabbSeparated':bool(culled)};checks.append(row)
  if v>1e-7:print(row,flush=True)
 del a;gc.collect()
report={'sourceHashes':sources,'entityCount':len(rows),'parts':rows,'checks':checks,'crossInterfaceClear':all(r['volumeMm3']<1e-7 or r['ownWireReceivingShoulder']for r in checks),'ownShoulderContactsUnconditionallyAccepted':False};(D/'all-interfaces.json').write_text(json.dumps(report,indent=2));print('crossInterfaceClear',report['crossInterfaceClear'],len(rows),len(checks))
