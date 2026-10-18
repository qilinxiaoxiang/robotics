from pathlib import Path
import json,hashlib,gc
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];M=D.parents[1]/'motor-wires';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
j=json.loads((W/'original-body-converter/fusion-import-manifest.json').read_text());top=json.loads((M/'active-topology.json').read_text());parts=[];rows=[];sources={str(p):sha(p)for p in [Path(__file__),M/'active-topology.json',W/'original-body-converter/fusion-import-manifest.json',D/'socket13-pin-order.json']}
for num in [5,10]:
 p=top['ports'][f'motor-{num}-socket-13'];bb=np.array(p['housingLocalBounds']);a=trimesh.creation.box(bb[1]-bb[0]);a.apply_translation(bb.mean(axis=0));a.apply_transform(p['transform']);sa=solid(a);f=D/f'zone-{num:02d}-socket13-housing-world.stl';a.export(f);sources[str(f)]=sha(f)
 part={'key':f'zone_{num:02d}_receiving_housing','name':f'Motor {num} dedicated power + DATA JST-EH housing','file':str(f),'sha256':sha(f),'color':'#ded7bc','port':p,'expectedFinalBoundsMm':a.bounds.tolist(),'geometryMeaning':'Official catalogue maximum receiving body, not detailed female contact/latch geometry'};parts.append(part)
 for o in j['parts']:
  if o['key']==f'motor{num}':continue
  b=trimesh.load(o['file'],force='mesh');b.apply_translation(o.get('importTranslationMm',[0,0,0]));sources[o['file']]=sha(o['file']);sweepmax=a.bounds[1]+np.array(p['outward'])*12;sweepmin=a.bounds[0]
  if np.any(sweepmax<b.bounds[0]) or np.any(b.bounds[1]<sweepmin):rows.append({'housing':part['key'],'obstacle':o['key'],'status':'FULL_SWEEP_BOUNDS_SEPARATE'});continue
  enclosure=not b.is_volume
  if enclosure:b=b.convex_hull
  sb=solid(b);vs=[]
  for k in range(49):
   v=(sa.translate((np.array(p['outward'])*k*.25).tolist())^sb).volume();vs.append(v)
  rows.append({'housing':part['key'],'obstacle':o['key'],'sourceConvexEnclosure':enclosure,'seatedVolumeMm3':vs[0],'sampleSpacingMm':.25,'withdrawalMm':[0,12],'maximumVolumeMm3':max(vs),'failedWithdrawalSamplesMm':[k*.25 for k,v in enumerate(vs)if v>1e-7],'status':'CLEAR'if max(vs)<=1e-7 else'BLOCKED'})
  del b,sb;gc.collect()
 report={'complete':True,'parts':parts,'rows':rows,'sourceHashes':sources,'scope':'External original-body obstacles only, full closed neutral assembly first; own keyed socket is a catalogue mating interface and is checked separately','integrationReady':False};(D/'zone-housing-check.json').write_text(json.dumps(report,indent=2)+'\n')
print([(r['housing'],r['obstacle'],r.get('seatedVolumeMm3'),r.get('failedWithdrawalSamplesMm'))for r in rows if r['status']=='BLOCKED'])
