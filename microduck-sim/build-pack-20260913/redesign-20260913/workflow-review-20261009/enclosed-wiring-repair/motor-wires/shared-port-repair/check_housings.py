from pathlib import Path
import json,hashlib,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;O=M.parents[1]/'roof-wiring-stage/motor-wires/obstacles';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();top=json.loads((M/'active-topology.json').read_text());nmfile=M.parent/'ankle-wires/native-motors/manifest.json';native=[r for r in json.loads(nmfile.read_text())['parts']if r['motor']==2];portkeys=set()
for side in ['right','left']:
 for w in json.loads((D/f'joint-{side}.json').read_text())['strands']:
  for e in['source','target']:portkeys.add(f'motor-{w[e]["motor"]}-socket-{w[e]["sourceSocket"]}')
def solid(m):
 assert m.is_volume;s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
rows=[];sources={str(nmfile):sha(nmfile)};culled=[]
for pk in sorted(portkeys):
 p=top['ports'][pk];bb=np.array(p['housingLocalBounds']);a=trimesh.creation.box(bb[1]-bb[0]);a.apply_translation(bb.mean(axis=0));a.apply_transform(p['transform']);sa=solid(a)
 for of in O.glob('*.json'):
  ob=json.loads(of.read_text());b=np.array(ob['expectedFinalBoundsMm']);key=ob['key'];sources[str(of)]=sha(of)
  if np.any(a.bounds[1]<b[0])or np.any(b[1]<a.bounds[0]):culled.append([pk,key]);continue
  sources[ob['file']]=sha(ob['file']);assert sources[ob['file']]==ob['sha256']
  if key.startswith('motor')and key[5:].isdigit():
   T=np.array(top['ports'][f'motor-{int(key[5:])}-socket-13']['transform'])
   def motors():
    for r in native:
     assert sha(r['file'])==r['sha256'];m=trimesh.load_mesh(r['file']);m.apply_transform(T@np.linalg.inv(r['worldTransform']));yield key+'-solid'+str(r['solid']),m
   meshes=motors()
  else:
   m=trimesh.load_mesh(ob['file']);m.apply_translation(ob.get('importTranslationMm',[0,0,0]));meshes=[(key,m)]
  for label,m in meshes:
   if np.any(a.bounds[1]<m.bounds[0])or np.any(m.bounds[1]<a.bounds[0]):culled.append([pk,label]);continue
   c=sa^solid(m);assert c.status()==mf.Error.NoError;v=c.volume();row={'port':pk,'obstacle':label,'volumeMm3':v,'bounds':list(c.bounding_box())if v>1e-7 else None,'ownCatalogueMating':key==f'motor{p["motor"]}'};rows.append(row)
   if v>1e-7:print(row,flush=True)
  gc.collect()
out={'sourceHashes':sources,'checks':rows,'separated':culled,'externalClear':all(r['volumeMm3']<1e-7 or r['ownCatalogueMating']for r in rows),'ownEnvelopeContactNotDetailedPlastic':True};(D/'housing-static.json').write_text(json.dumps(out,indent=2));print('externalClear',out['externalClear'])
