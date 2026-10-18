"""Recheck revised fasteners/seat meshes in exact torso service and curved-head context."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh,re,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parent;G=R/'leg-guide-20261006';N=G/'non-head-review';H=R/'head-redesign-20261008'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();p=H/'head-fit-investigation.py';n={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],n)
raw=n['raw'];data=n['data'];source_solid=n['solid'];solidcache={k:n['man'](trimesh.load(D/(k+'-m2x6-seat-world.stl'),force='mesh')) for k in ['neck_pitch','lower','right_lower']}
def solid(k):return solidcache[k] if k in solidcache else source_solid(k)
# Derive the identical prospective screws used by the UI overlay.
for s in data['screws']:
 if s['spec']=='M2 x 5 TAP':
  s['spec']='M2 x 6 TAP';s['length_mm']=6;s['world_center_mm']=(np.array(s['world_center_mm'])+np.array(s['world_axis'])).tolist();s['stack_mm']=[x+1 for x in s['stack_mm']]
 if s.get('groupId')=='imu_clamp':
  s['spec']='M2 x 6 TAP pressure screw';s['length_mm']=6;s['world_center_mm']=(np.array(s['world_center_mm'])+np.array(s['world_axis'])).tolist()
payload=json.loads((N/'torso-service-steps.json').read_text());oldreport=json.loads((N/'torso-service-verification.json').read_text());assert payload['integrationReady'] and oldreport['passed'];assert payload['verificationSha256']==sha(N/'torso-service-verification.json');assert payload['sourceDataSha256']==hashlib.sha256(raw).hexdigest()
# Execute unchanged source motion/contact contracts with prospective real full geometry.
source=(N/'verify_torso_service.py').read_text();e={'np':np,'trimesh':trimesh,'re':re,'n':n,'data':data,'solid':solid,'sample':n['samples'],'payload':payload,'ss':{s['id']:s for s in data['screws']},'installed':{s['id'] for s in data['screws'] if s['moduleId'] in ['left-leg','right-leg']},'errors':[],'paths':[],'toolrows':[],'accepted':[]}
exec(source[source.index('def cyl('):source.index('removed=')],e)
print('torso service',len(e['paths']),len(e['toolrows']),'errors',e['errors'],flush=True)
# Actual curved head includes replacement meshes, transformed boards, additional mounts/hardware/envelopes.
p=H/'verify_integrated_review.py';h={'__file__':str(p)};exec(p.read_text().split('solids={k:man(v)')[0],h);headsolids={k:n['man'](v) for k,v in h['meshes'].items()};heads={};cyl=e['cyl'];rows=[]
for k in ['neck_pitch','lower','right_lower']:headsolids[k]=solid(k)
for s in data['screws']:
 if s['id'].startswith('S13-horn-'):
  a=np.array(s['world_center_mm']);v=np.array(s['world_axis']);heads[s['id']]=cyl(a+v*.001,a+v*1.72,2)
for key,shape in {'neck_pitch_added_seats':solid('neck_pitch')-source_solid('neck_pitch'),**heads}.items():
 hits={};bb=np.array(shape.bounding_box()).reshape(2,3)
 for q,other in headsolids.items():
  if q=='neck_pitch':continue
  ob=np.array(other.bounding_box()).reshape(2,3)
  if np.any(bb[1]<ob[0]) or np.any(ob[1]<bb[0]):continue
  vol=float((shape^other).volume())
  if vol>1e-6:hits[q]=vol
 rows.append({'moving':key,'fixed':sorted(headsolids),'contactsMm3':hits})
 if hits:e['errors'].append({'curvedHead':key,'hits':hits})
extra_inputs=list(D.glob('*-m2x6-seat-*.stl'))+[H/f for f in h['c']['replacementMeshes'].values()]+[H/p['mesh'] for p in h['c']['additionalParts']]
assert all(sha(H/f)==v for f,v in h['c']['meshHashes'].items()),'Curved-head mesh drift'
report={'passed':not e['errors'],'errors':e['errors'],'sourceDataSha256':hashlib.sha256(raw).hexdigest(),'sourceHashes':{str(p.resolve()):sha(p) for p in [Path(__file__),N/'verify_torso_service.py',N/'torso-service-steps.json',N/'torso-service-verification.json',H/'verify_integrated_review.py',H/'viewer-candidate.json']+extra_inputs},'torsoServiceFullGeometry':{'partPaths':e['paths'],'driverPaths':e['toolrows'],'acceptedSpecificContacts':e['accepted'],'ringEndpointRefinement':e['refined'],'sameStrictContractsAsOriginal':True},'curvedHeadFinalContext':rows,'curvedCandidateMeshHashes':h['c'].get('meshHashes'),'scope':'Complete prospective torso moving/fixed parts and retained screw envelopes; unchanged exact source contact contracts. New neck seats/heads in actual integrated curved head at source pose. Complete operational joint range and physical strength remain separate.','physicalFitVerified':False}
assert sha(G/'full-build-data.json')==report['sourceDataSha256']
(D/'fastener-context-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'errors':report['errors'],'partPaths':len(e['paths']),'toolPaths':len(e['toolrows']),'headRows':len(rows)}));raise SystemExit(bool(e['errors']))
