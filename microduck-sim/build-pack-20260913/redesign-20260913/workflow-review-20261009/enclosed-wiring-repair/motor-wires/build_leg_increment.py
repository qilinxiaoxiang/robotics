from pathlib import Path
import json,hashlib,copy,math
D=Path(__file__).resolve().parent;A=D.parent/'ankle-wires';OLD=D.parents[1]/'roof-wiring-stage/motor-wires'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def bind_manifest(p):
 x=read(p)
 for f,h in x['sourceHashes'].items():assert sha(Path(f))==h,(f,'stale source')
 for r in x['parts']:assert sha(Path(r['file']))==r['sha256'],r['key']
 return x
hip=bind_manifest(D/'hip-fusion-manifest.json');ankle=bind_manifest(A/'ankle-fusion-manifest.json');top=read(D/'active-topology.json');old=read(OLD/'manifest.json');parts=hip['parts']+ankle['parts'];paths=[];sources={str(D/'hip-fusion-manifest.json'):sha(D/'hip-fusion-manifest.json'),str(A/'ankle-fusion-manifest.json'):sha(A/'ankle-fusion-manifest.json'),str(D/'active-topology.json'):sha(D/'active-topology.json')}
for f,rid,reverse in [('local-route.json','ttl-04-03',False),('mirror-route.json','ttl-09-08',True)]:
 p=D/f;x=read(p);assert x['allStaticClear'];sources[str(p)]=sha(p)
 for w in x['strands']:
  fp=Path(w['file']);fp=fp if fp.is_absolute()else D/fp;assert sha(fp)==w['sha256'];key=f'{rid}-conductor-{w["id"]}'
  parts.append({'key':key,'name':f'{rid} conductor {w["id"]} — complete 180 mm route','file':str(fp),'sha256':sha(fp),'color':'#bda356','group':'Knee harness — static checked','kind':'wire','routeId':rid,'coordinates':'world mm; identity transform','expectedFinalBoundsMm':w['meshBoundsMm'],'validationStatus':'Neutral mesh clear; ttl-04-03 also native Fusion sweep/interference clear'})
  pr=copy.deepcopy(w['primitives'])
  if reverse:
   pr.reverse()
   for q in pr:
    q['start'],q['end']=q['end'],q['start']
    if 'normal'in q:q['normal']=[-v for v in q['normal']]
  paths.append({'key':key,'routeId':rid,'sourceFile':str(p),'sourceSha256':sha(p),'pathFormat':'ordered-world-line-arc-v1','orderedPrimitives':pr,'nominalFlexibleLengthMm':180,'radiusMm':.75,'traversalReversedFromSource':reverse})
 rr=next(r for r in top['routes']if r['id']==rid)
 for pk in [rr['fromPort'],rr['toPort']]:
  pt=top['ports'][pk];oldkey=f'motor-{pt["motor"]:02d}-socket-{pt["sourceSocket"]}-housing';op=copy.deepcopy(next(q for q in old['parts']if q['key']==oldkey));assert sha(Path(op['file']))==op['sha256'];op.update(key=f'{rid}-{pk}-housing',routeId=rid,group='Knee harness — registered connectors',validationStatus='Catalogue receiving housing; own socket mating is not detailed female plastic CAD');parts.append(op)
for side in ['right','left']:
 p=D/f'hip-coiled-{side}.json';x=read(p)
 for w in x['strands']:
  # Keep canonical analytic curve plus an explicit placement. Reflection flips arc normal as a pseudovector; importer should use start/mid/end.
  trans=[[1,0,0,0],[0,-1 if w['reflectY']else 1,0,0],[0,0,1,0],[0,0,0,1]]
  hel=dict(w['coil'],kind='smooth-pitch-helix',pitchRampFunction='raised cosine derivative; integral formula in NATIVE-PATHS.md')
  seq=copy.deepcopy(w['prefixPrimitivesCanonical'])+[hel,{'kind':'cubic-bezier','controlPoints':w['exitBezierCanonical']},{'kind':'line','start':w['exitLineCanonical'][0],'end':w['exitLineCanonical'][1]}]
  paths.append({'key':f'{x["routeId"]}-conductor-{w["id"]}','routeId':x['routeId'],'sourceFile':str(p),'sourceSha256':sha(p),'pathFormat':'ordered-line-arc-analytic-helix-bezier-v1','canonicalToWorld':trans,'orderedPrimitives':seq,'worldSamples':w['centerlineMm'],'nominalFlexibleLengthMm':180,'radiusMm':.75})
p=A/'ankle-route-check.json';x=read(p)
for w in x['strands']:paths.append({'key':w['key'],'routeId':w['routeId'],'sourceFile':str(p),'sourceSha256':sha(p),'pathFormat':'ordered-world-line-arc-v1','orderedPrimitives':w['primitives'],'nominalFlexibleLengthMm':180,'radiusMm':.75})
for f in ['fusion-native-interference.json','fusion-resume-readback.json','analytic-route-audit.json','mirror-metadata-correction.json','retention-plan.json','retention-motion.json']:
 sources[str(D/f)]=sha(D/f)
assert read(D/'fusion-native-interference.json')['nativeStaticPassed'];assert read(D/'fusion-native-interference.json')['routeSha256']==sha(D/'local-route.json')
assert len(parts)==30 and len(paths)==18 and len(set(r['key']for r in parts))==30
pc={'schemaVersion':1,'units':'mm','curveCount':18,'paths':paths,'sourceHashes':sources};(D/'leg-centerlines.json').write_text(json.dumps(pc,indent=2)+'\n');sources[str(D/'leg-centerlines.json')]=sha(D/'leg-centerlines.json')
ids=['ttl-05-04','ttl-04-03','ttl-02-01','ttl-10-09','ttl-09-08','ttl-07-06']
manifest={'schemaVersion':1,'status':'SIX LOCAL LEG CABLES; inherited per-route static clear; cross-route verification required','wholeHarnessAccepted':False,'physicalFitVerified':False,'units':'mm','coordinateTransform':'identity','parts':parts,'activeTopology':str(D/'active-topology.json'),'routes':[next(r for r in top['routes']if r['id']==rid)for rid in ids],'centerlineInput':str(D/'leg-centerlines.json'),'centerlineSha256':sha(D/'leg-centerlines.json'),'sourceHashes':sources,'replaceRouteIds':['ttl-05-04','ttl-04-03','ttl-02-01','ttl-09-10','ttl-08-09','ttl-06-07'],'excludedRemovedTopology':['ttl-01-06'],'retentionIncrement':str(D/'retention-fusion-manifest.json'),'retentionNote':'Already imported case anchors are not duplicated among the 30 cable objects.','scope':'Six corrected local cables only, not complete bus; unchanged 3→2/8→7 and torso/head branches are outside this increment. All contacts/limitations inherited from route receipts.'}
(D/'leg-local-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('30 cable objects; 18 native curve inputs; six routes')
