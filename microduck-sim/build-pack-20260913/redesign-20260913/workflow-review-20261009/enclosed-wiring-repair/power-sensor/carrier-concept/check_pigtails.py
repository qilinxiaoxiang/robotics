from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];R=W.parent;O=W/'roof-wiring-stage/motor-wires/obstacles'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 m=trimesh.load_mesh(p);assert m.is_volume,p;s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
rows=[];cfg=json.loads((D/'native-carrier.json').read_text());carrier=load(D/'power-support-controller-concept-world.stl');board=mf.Manifold.cube([30,26,8]).translate([-40,-13,-50]);j=json.loads((W/'enclosed-wiring-repair/head-layout/native-fusion-repair-inputs.json').read_text());T=np.array([[0,0,1,-29.5],[1,0,0,0],[0,1,0,-1],[0,0,0,1]],float);delta=T@np.linalg.inv(j['openrb']['nativeToCurrentWorld']);ep=R/'head-redesign-20261008/usb-access/usb-repair/openrb-component-enclosures/manifest.json';elec=json.loads(ep.read_text())['components'];expected=[]
for p in cfg['pigtails']:
 a=load(p['stl']);checks=[]
 for key,b in [('new_carrier',carrier),('DFR',board)]:
  cut=a^b;assert cut.status()==mf.Error.NoError;checks.append({'key':key,'intersectionMm3':cut.volume(),'gapSearch5mm':a.min_gap(b,5)})
 for f in sorted(O.glob('*.json')):
  ob=json.loads(f.read_text());key=ob['key']
  if key in ['regulator','regulator_insert','power_support','openrb','curved_cap_hardware']:continue
  bb=np.array(ob['expectedFinalBoundsMm']);ab=np.array(a.bounding_box()).reshape(2,3)
  if np.any(ab[1]<bb[0])or np.any(bb[1]<ab[0]):checks.append({'key':key,'intersectionMm3':0,'method':'AABB-separated'});continue
  assert sha(ob['file'])==ob['sha256'];b=load(ob['file']).translate(ob.get('importTranslationMm',[0,0,0]));cut=a^b;assert cut.status()==mf.Error.NoError;checks.append({'key':key,'intersectionMm3':cut.volume(),'bounds':list(cut.bounding_box())if cut.volume()>1e-6 else None})
 for q in elec:
  assert sha(q['mesh'])==q['meshSha256'];b=load(q['mesh']).transform(delta[:3]);cut=a^b;assert cut.status()==mf.Error.NoError;checks.append({'key':'openrb-'+str(q['index']),'intersectionMm3':cut.volume(),'bounds':list(cut.bounding_box())if cut.volume()>1e-6 else None})
 rows.append({'net':p['net'],'file':p['stl'],'sha256':sha(p['stl']),'expectedChecks':2+len(list(O.glob('*.json')))-5+len(elec),'checks':checks,'passed':all(x['intersectionMm3']<1e-6 for x in checks),'complete':len(checks)==2+len(list(O.glob('*.json')))-5+len(elec)})
out={'scope':'Two short J4 terminal-exit receivers only: 2mm outward straight,R4 bend,diameter1.6; not electrical sizing or full power harness. New DFR5mm lower; no intentional interface overlap waived.','sourceHashes':{str(p):sha(p)for p in [D/'native-carrier.json',D/'power-support-controller-concept-world.stl',ep,Path(__file__)]},'rows':rows,'passed':all(r['passed']and r['complete']for r in rows)};f=D/'pigtail-check.json';f.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'passed':out['passed'],'hits':[x for r in rows for x in r['checks']if x['intersectionMm3']>1e-6],'gaps':[r['checks'][:2]for r in rows]},indent=2))
