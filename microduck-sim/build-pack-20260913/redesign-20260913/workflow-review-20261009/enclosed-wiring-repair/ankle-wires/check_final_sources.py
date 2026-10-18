from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent/'motor-wires';W=D.parents[1];O=W/'roof-wiring-stage/motor-wires/obstacles'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 assert m.is_volume
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert a.status()==mf.Error.NoError and a.volume()>0;return a
rp=D/'ankle-route-check.json';r=json.loads(rp.read_text());assert r['complete'] and r['passedStatic'];top=json.loads((M/'active-topology.json').read_text());nmp=D/'native-motors/manifest.json';nm=json.loads(nmp.read_text());native=[q for q in nm['parts']if q['motor']==2];gp=W.parent/'leg-guide-20261006/full-build-data.json';gg=json.loads(gp.read_text());Ts={p['key']:p.get('sourceTransformWorld')for p in gg['parts']};del gg
entities=[]
for w in r['strands']:
 assert sha(w['file'])==w['sha256'];m=trimesh.load_mesh(w['file']);entities.append((w['key'],m,solid(m),None))
for rid in ['ttl-02-01','ttl-07-06']:
 rr=next(q for q in top['routes']if q['id']==rid)
 for end in ['fromPort','toPort']:
  p=top['ports'][rr[end]];m=trimesh.load_mesh(D/(rr[end]+'-housing.stl'));entities.append((rr[end],m,solid(m),p))
checks=[];coverage=[]
for f in O.glob('*.json'):
 ob=json.loads(f.read_text());key=ob['key'];assert sha(ob['file'])==ob['sha256'];bb=np.array(ob['expectedFinalBoundsMm']);near=[]
 for name,m,a,port in entities:
  if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):coverage.append({'entity':name,'obstacle':key,'status':'BOUNDS_SEPARATE'})
  else:near.append((name,m,a,port));coverage.append({'entity':name,'obstacle':key,'status':'EXACT_SOURCE_BODIES'})
 if not near:continue
 if key.startswith('motor') and key[5:].isdigit():
  def meshes():
   for q in native:
    assert sha(q['file'])==q['sha256'];m=trimesh.load_mesh(q['file']);m.apply_transform(np.array(Ts[key])@np.linalg.inv(q['worldTransform']));yield(str(q['solid']),m,q['sha256'],q['sourceBody'])
  iterable=meshes()
 else:
  m=trimesh.load_mesh(ob['file']);m.apply_translation(ob.get('importTranslationMm',[0,0,0]));iterable=[('single',m,ob['sha256'],None)]
 for sub,m,h,sourcebody in iterable:
  b=solid(m)
  for name,em,a,port in near:
   if port is not None and key=='motor'+str(port['motor']) and sourcebody==port['sourceSocket']:
    checks.append({'entity':name,'obstacle':key+'-'+sub,'status':'NAMED_HEADER_MATING','reason':'Full catalogue envelope intentionally seats around the selected manufacturer male header; not latch/terminal detailed fit proof'});continue
   if np.any(em.bounds[1]<m.bounds[0])or np.any(m.bounds[1]<em.bounds[0]):continue
   c=a^b;assert c.status()==mf.Error.NoError;v=c.volume();checks.append({'entity':name,'obstacle':key+'-'+sub,'sourceSha256':h,'status':'CLEAR' if v<1e-7 else 'INTERSECTION','volumeMm3':v,'boundsMm':list(c.bounding_box())if v>1e-7 else None})
expected=len(list(O.glob('*.json')))*len(entities);out={'scope':'Neutral full strand/housing checks against all source references; invalid aggregate motors replaced by12 manufacturer native solids. Selected header mating alone named and retained.','expectedPairs':expected,'complete':len(coverage)==expected,'coverage':coverage,'rows':checks,'passed':not any(q['status']=='INTERSECTION'for q in checks),'sourceHashes':{str(rp):sha(rp),str(nmp):sha(nmp),str(gp):sha(gp),str(M/'active-topology.json'):sha(M/'active-topology.json'),str(Path(__file__)):sha(__file__)}};(D/'final-source-check.json').write_text(json.dumps(out,indent=2));print('complete',out['complete'],'hits',[q for q in checks if q['status']=='INTERSECTION'])
