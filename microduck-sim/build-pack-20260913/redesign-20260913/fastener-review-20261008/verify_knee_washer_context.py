"""Bind exact native/service visibility and recheck complete repaired leg geometry."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh,re,copy
D=Path(__file__).resolve().parent;R=D.parent;G=R/'leg-guide-20261006';N=G/'non-head-review';H=R/'head-redesign-20261008';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();repair=json.loads((D/'knee-washer-repair.json').read_text());assert repair['passed']
p=H/'head-fit-investigation.py';n={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],n);data=n['data'];source_solid=n['solid'];ss={s['id']:s for s in data['screws']};source_hash=hashlib.sha256(n['raw']).hexdigest();assert source_hash==repair['sourceDataSha256']
parts={x['key']:n['man'](trimesh.load(D/x['mesh'],force='mesh')) for x in repair['additionalParts']};belongs={'lower':[],'right_lower':[]}
for x in repair['additionalParts']:
 s=ss[x['fastenerId']];host='lower' if s['moduleId']=='left-leg' else 'right_lower';belongs[host].append(x['key'])
for r in repair['rows']:
 s=ss[r['id']];s.update(spec=r['repairSpec'],length_mm=6,world_center_mm=r['newWorldCenterMm'],washer_mm=.5,engagement_mm=r['newEntryMm'],penetration_mm=r['newEntryMm'])
def solid(k):return parts[k] if k in parts else source_solid(k)
def append_unique(a,b):return list(dict.fromkeys(a+b))
def derived_op(op,installed=True):
 out=copy.deepcopy(op)
 for field in ['isolatedPartKeys','visiblePartKeys','moveKeys']:
  if field not in out:continue
  for host,keys in belongs.items():
   if installed and host in out[field]:out[field]=append_unique(out[field],keys)
 if 'motionWaypoints' in out:out['motionWaypoints']['movingKeys']=out.get('moveKeys',out['motionWaypoints']['movingKeys'])
 return out
native=[];native_paths=[]
for module in data['modules']:
 if module['id'] not in ['left-leg','right-leg']:continue
 host='lower' if module['id']=='left-leg' else 'right_lower';keys=belongs[host];ops=[];installed=False;prior=set()
 for op in module['operations']:
  prior.update(op['add'])
  if op['id'].endswith('-10'):installed=True
  o=derived_op(op,installed)
  if op['id'].endswith('-10'):
   o['add']=append_unique(o['add'],keys);o.setdefault('partApproachVectors',{})
   for k in keys:
    sid=next(x['fastenerId'] for x in repair['additionalParts'] if x['key']==k);o['partApproachVectors'][k]=(np.array(ss[sid]['world_axis'])*12).tolist()
   o['title']='Fasten the knee output with four small metal washers'
   o['text']='Use four M2×6 TAP screws with one correctly dimensioned small-OD metal washer under each head (ID2.2, OD4, nominal thickness0.5 mm). Keep the original lower link. If the leg is already assembled with M2×6, add washers one screw at a time while the complete leg is supported; leave the other three output screws and every ankle/foot fastener installed. Confirm washer dimensions before use; OD5 washers do not fit these seats.'
  patch={k:v for k,v in o.items() if op.get(k)!=v}
  if patch:ops.append({'id':o['id'],'patch':patch})
  # New washers follow every later native motion, or remain as real obstacles.
  if installed:
   prior.update(keys);visible=set(o.get('isolatedPartKeys',prior))&prior;moving=o.get('moveKeys',[])
   if moving:
    fixed=visible-set(moving);affected=(set(moving)&set(parts));v=o.get('approachVector',[0,0,0]);res=n['samples']({k:solid(k) for k in affected},{k:solid(k) for k in fixed},v,step=.25) if affected else {'peakContactsMm3':{},'samples':[]}
    # Independently sweep original whole moving geometry against stationary new washers.
    other=n['samples']({k:solid(k) for k in moving if k in visible},{k:solid(k) for k in fixed&set(parts)},v,step=.25) if fixed&set(parts) else {'peakContactsMm3':{},'samples':[]}
    native_paths.append({'operation':o['id'],'newMovingWashers':res,'movingGroupVsStationaryWashers':other,'movingKeys':moving,'fixedKeys':sorted(fixed)})
 native.append({'moduleId':module['id'],'partKeys':append_unique(module['partKeys'],keys),'ownedPartKeys':append_unique(module['ownedPartKeys'],keys),'operations':ops})
base=json.loads((N/'torso-service-steps.json').read_text());assert base['integrationReady'];payload=copy.deepcopy(base);serviceops=[]
for i,op in enumerate(base['module']['operations']):
 o=derived_op(op);payload['module']['operations'][i]=o;patch={k:v for k,v in o.items() if op.get(k)!=v}
 if patch:serviceops.append({'id':op['id'],'patch':patch})
payload['module']['partKeys']=append_unique(payload['module']['partKeys'],list(parts));payload['module']['contextPartKeys']=append_unique(payload['module']['contextPartKeys'],list(parts))
source=(N/'verify_torso_service.py').read_text();e={'np':np,'trimesh':trimesh,'re':re,'n':n,'data':data,'solid':solid,'sample':n['samples'],'payload':payload,'ss':ss,'installed':{s['id'] for s in data['screws'] if s['moduleId'] in ['left-leg','right-leg']},'errors':[],'paths':[],'toolrows':[],'accepted':[]}
exec(source[source.index('def cyl('):source.index('removed=')],e)
for row in native_paths:
 for k in ['newMovingWashers','movingGroupVsStationaryWashers']:
  if row[k]['peakContactsMm3']:e['errors'].append({'nativeOperation':row['operation'],'check':k,'hits':row[k]['peakContactsMm3']})
# Nominal washer fit and all maximal-source tolerance endpoints; no silent relaxation of seat collisions.
tol=[]
for r in repair['rows']:
 a=np.array(r['newWorldCenterMm']);v=np.array(ss[r['id']]['world_axis']);host=r['partKey'];T=trimesh.geometry.align_vectors([0,0,1],v);cyl=e['cyl'];fixed={k:solid(k) for k in r['completeRetainedLegPartKeys']}
 for th in [.4,.6]:
  # MaxOD4 and minID2.2 gives the largest conservative washer material volume.
  wash=cyl(a,a+v*th,2)-cyl(a-v*.1,a+v*(th+.1),1.1);head=cyl(a+v*(th+.0001),a+v*(th+1.72),2)
  for theta in np.linspace(0,2*np.pi,17)[:-1]:
   offset=(T[:3,0]*np.cos(theta)+T[:3,1]*np.sin(theta))*.1;shape=wash.translate(offset);hits={k:float((shape^s).volume()) for k,s in fixed.items() if (shape^s).volume()>1e-5};tol.append({'id':r['id'],'thicknessMm':th,'offsetWorldMm':offset.tolist(),'hits':hits})
   if hits:e['errors'].append({'washerTolerance':tol[-1]})
  hp=n['samples']({'head':head},fixed,v*12,step=.25)
  if hp['peakContactsMm3']:e['errors'].append({'toleranceHeadRoute':r['id'],'thickness':th,'hits':hp['peakContactsMm3']})
assert source_hash==sha(G/'full-build-data.json')
report={'passed':not e['errors'],'errors':e['errors'],'sourceDataSha256':source_hash,'sourceHashes':{str(p.resolve()):sha(p) for p in [Path(__file__),D/'verify_knee_washer_repair.py',D/'knee-washer-repair.json',N/'verify_torso_service.py',N/'torso-service-steps.json',N/'torso-service-verification.json',G/'full-build-data.json']+[D/p['mesh'] for p in repair['additionalParts']]},'baseTorsoServiceSha256':sha(N/'torso-service-steps.json'),'torsoPartPaths':e['paths'],'torsoDriverPaths':e['toolrows'],'acceptedSpecificContacts':e['accepted'],'ringEndpointRefinement':e['refined'],'nativeWasherPaths':native_paths,'washerToleranceChecks':tol,'integrationReady':False,'adoption':'Independent conditional review; main guide remains integral-seat NEW BUILD. Flat recessed seating is required, arbitrary0.17mm eccentricity is rejected.','viewerIntegration':{'baseTorsoServiceSha256':sha(N/'torso-service-steps.json'),'nativeModules':native,'torsoModule':{'partKeys':payload['module']['partKeys'],'contextPartKeys':payload['module']['contextPartKeys'],'operations':serviceops}},'physicalFitVerified':False,'scope':'Original completed lower links plus washer repair; all torso routes/tools recomputed with real washer parts and corrected screw heads. Native whole groups include attached washers only after installation, under exact bench visibility.'}
(D/'knee-washer-context.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'errors':report['errors'],'torsoPaths':len(e['paths']),'torsoTools':len(e['toolrows']),'nativeContexts':len(native_paths),'toleranceChecks':len(tol)},indent=2));raise SystemExit(bool(e['errors']))
