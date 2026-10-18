from pathlib import Path
import json,hashlib,struct
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(f):return json.loads((D/f).read_text())
def bounds(p):
 b=p.read_bytes();n=struct.unpack_from('<I',b,80)[0];assert len(b)==84+50*n
 lo=[float('inf')]*3;hi=[-float('inf')]*3
 for i in range(n):
  vv=struct.unpack_from('<9f',b,84+50*i+12)
  for j in range(3):
   for k in range(3):lo[k]=min(lo[k],vv[j*3+k]);hi[k]=max(hi[k],vv[j*3+k])
 return [lo,hi]
valid=load('hip-valid-source-static.json');selfcheck=load('hip-centerline-audit.json');assert valid['passed'] and selfcheck['passed']
parts=[];routes=[];inputs=['active-topology.json','hip_coiled.py','check_hip_valid_sources.py','audit_hip_centerlines.py','check_hip_plug_access.py','hip-valid-source-static.json','hip-centerline-audit.json','hip-plug-access.json']
for side in ['right','left']:
 f=f'hip-coiled-{side}.json';x=load(f);assert x['staticPassed'];inputs.append(f)
 v=next(v for v in valid['routes']if v['side']==side);assert v['inputSha256']==sha(D/f)
 for a in selfcheck['rows']:
  if a['side']==side:assert a['sourceSha256']==sha(D/f)
 for w in x['strands']:
  p=Path(w['file']);p=p if p.is_absolute()else D/p;assert w['sha256']==sha(p)
  parts.append({'key':f'{x["routeId"]}-conductor-{w["id"]}','name':f'{x["routeId"]} conductor {w["id"]} — complete 180 mm receiving route','file':str(p),'sha256':sha(p),'color':'#bda356','group':'Hip motor harness — static checked','kind':'wire','role':'TTL three-conductor harness; terminal pin order not encoded by colour','routeId':x['routeId'],'expectedFinalBoundsMm':bounds(p),'coordinates':'world mm; identity transform','validationStatus':'Neutral static and self-clear; flexible movement/physical seating not commissioned'})
 for label in ['fromHousing','toHousing']:
  p=D/f'hip-{side}-{label}.stl';parts.append({'key':f'{x["routeId"]}-{label}','name':f'{x["routeId"]} {label} full receiving envelope','file':str(p),'sha256':sha(p),'color':'#eee8dd','group':'Hip motor harness — registered connectors','kind':'connector','routeId':x['routeId'],'expectedFinalBoundsMm':bounds(p),'coordinates':'world mm; identity transform','validationStatus':'Mated receiving envelope; own-socket internal mating features not represented'})
 gaps=[a['gapMmCappedAt1']for a in v['checked']if a['gapMmCappedAt1'] is not None]
 routes.append({'id':x['routeId'],'neutralStaticPassed':True,'selfClear':True,'strandLengthMm':[w['computedLengthMm']for w in x['strands']],'diameterReceivingMm':1.5,'minimumActualObstacleGapMm':min(gaps),'newPrintedParts':0,'physicalCommissioned':False,'receivingAssumptions':['Nominal 180 mm flexible length modeled per strand; stock shoulder-to-shoulder length/tolerance not measured.','R2 entry fillets; coil radius 3.55–4.05 mm, manufacturer fatigue/bend limit not available.','Receiving plug EHR-3 dimensions bound official source, not detailed latch geometry.']})
manifest={'status':'TWO HIP ROUTES NEUTRAL STATIC CLEAR','wholeHarnessAccepted':False,'units':'mm','coordinateTransform':'identity','parts':parts,'routes':routes,'replaceRouteIds':['ttl-05-04','ttl-09-10'],'activeTopology':'active-topology.json','sourceHashes':{str(D/f):sha(D/f)for f in inputs},'remainingScope':['Soft service-loop adjustment under actual joint travel; no fixed-shape flexible sweep claim.','Retention material inventory and final physical seating remain unverified.','Remaining bus routes are separate work; cross-foot 1→6 is removed by active topology.']}
(D/'hip-fusion-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'parts':len(parts),'routes':routes,'manifestSha256':sha(D/'hip-fusion-manifest.json')},indent=2))
