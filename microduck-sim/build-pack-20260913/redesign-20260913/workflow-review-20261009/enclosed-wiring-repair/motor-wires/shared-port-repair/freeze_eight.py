from pathlib import Path
import json,hashlib,copy,math
D=Path(__file__).resolve().parent;M=D.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text());sources={}
def bind(p):sources[str(p)]=sha(p);return read(p)
for f in ['build_joint.py','mirror_joint.py','check_valid.py','check_self.py','check_all_interfaces.py','check_housings.py','INSTALL-SEQUENCE.md','operation-dependencies.json','complete-interface-inventory.json']:bind(D/f) if f.endswith('.json') else sources.update({str(D/f):sha(D/f)})
right=bind(D/'joint-right.json');left=bind(D/'joint-left.json');top=bind(M/'active-topology.json');prev=bind(D/'active-topology-before-shared-port.json');assert top['ports']==prev['ports']and top['branches']==prev['branches']
unchanged=[r['id']for r in top['routes']if r==next(q for q in prev['routes']if q['id']==r['id'])];assert 'ttl-05-04'in unchanged and'ttl-10-09'in unchanged
compat={'passed':True,'oldTopologySha256':sha(D/'active-topology-before-shared-port.json'),'currentTopologySha256':sha(M/'active-topology.json'),'allPortGeometryExactlyEqual':True,'allMotorIdsAndBranchesExactlyEqual':True,'unchangedRoutes':unchanged,'changedRoutes':[r['id']for r in top['routes']if r['id']not in unchanged]};(D/'topology-compatibility.json').write_text(json.dumps(compat,indent=2));bind(D/'topology-compatibility.json')
for f in ['valid-right.json','valid-left.json','self-check.json','retention-delta.json']:
 r=bind(D/f);assert r['passed'],f
 for p,h in r.get('sourceHashes',{}).items():assert sha(p)==h,(f,p)
assert read(D/'self-check.json')['sourceSha256']==sha(D/'joint-right.json')
interfaces=bind(D/'all-interfaces.json');housing=bind(D/'housing-static.json');assert interfaces['crossInterfaceClear']and housing['externalClear'];assert len(interfaces['parts'])==40 and len(interfaces['checks'])==780
for p,h in interfaces['sourceHashes'].items():assert sha(p)==h,p
# Limit receiving-shoulder contacts to six named ankle terminations and exactly the documented 0.6 mm axial strip.
contacts=[]
for r in interfaces['checks']:
 if r['volumeMm3']<1e-7:continue
 assert r['ownWireReceivingShoulder']and r['volumeMm3']<1.09
 wire=next(k for k in [r['a'],r['b']]if k.startswith('ttl-'));pk=next(k for k in [r['a'],r['b']]if k.startswith('motor-'));assert(wire.startswith('ttl-02-01-')and pk=='motor-1-socket-13')or(wire.startswith('ttl-07-06-')and pk=='motor-6-socket-14')
 assert abs(r['bounds'][4]-r['bounds'][1]-.6)<1e-4;contacts.append(r)
assert len(contacts)==6
# Manufacturer socket solids overlap the full rectangular mating envelope. Keep numbers visible; only exact own-interface identities are classified.
for r in housing['checks']:
 if r['volumeMm3']<1e-7:continue
 mid=int(r['port'].split('-')[1]);sid=int(r['port'].split('-')[-1]);assert r['ownCatalogueMating']
 assert r['obstacle']in[f'motor{mid}-solid2',f'motor{mid}-solid{10 if sid==13 else 11}'];assert r['volumeMm3']<(.641 if r['obstacle'].endswith('solid2')else 57.625)
# Native curve topology and exact reflection proof, not just mesh closure.
def sub(a,b):return[x-y for x,y in zip(a,b)]
def norm(a):return math.sqrt(sum(x*x for x in a))
def cross(a,b):return[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def tangent(p,end=False):
 v=sub(p['end'],p['start'])if p['kind']=='line'else cross(p['normal'],sub(p['end'if end else'start'],p['center']));return[x/norm(v)for x in v]
paths=[];audits=[]
for side,data in [('right',right),('left',left)]:
 for w in data['strands']:
  assert sha(w['file'])==w['sha256'];pr=w['primitives'];assert abs(sum(p['lengthMm']for p in pr)-180)<1e-6
  joins=[]
  for a,b in zip(pr,pr[1:]):
   gap=norm(sub(a['end'],b['start']));dot=sum(x*y for x,y in zip(tangent(a,True),tangent(b)));assert gap<1e-6 and dot>1-1e-7,(w['key'],gap,dot);joins.append({'gapMm':gap,'tangentDot':dot})
  paths.append({'key':w['key'],'routeId':w['routeId'],'pathFormat':'ordered-world-line-arc-v1','orderedPrimitives':pr,'nominalFlexibleLengthMm':180,'radiusMm':.75,'sourceFile':str(D/f'joint-{side}.json'),'sourceSha256':sha(D/f'joint-{side}.json')});audits.append({'wire':w['key'],'primitiveCount':len(pr),'lengthMm':180,'joins':joins})
for a,b in zip(right['strands'],left['strands']):
 assert len(a['primitives'])==len(b['primitives'])
 for p,q in zip(a['primitives'],b['primitives']):
  assert p['kind']==q['kind']
  for k in['start','end','mid','center']:
   if k in p:assert q[k]==[p[k][0],-p[k][1],p[k][2]]
  if 'normal'in p:assert q['normal']==[-p['normal'][0],p['normal'][1],-p['normal'][2]]
# Frozen hip geometry remains byte-for-byte unchanged; current graph's two hip edges and all registered transforms are exactly equal.
oldpaths=bind(M/'leg-centerlines.json')
for rid in['ttl-05-04','ttl-10-09']:paths.extend(p for p in oldpaths['paths']if p['routeId']==rid)
hip=bind(M/'hip-valid-source-static.json');assert hip['passed'];bind(M/'hip-centerline-audit.json');bind(M/'hip-plug-access.json')
for side in['right','left']:bind(M/f'hip-coiled-{side}.json')
assert len(paths)==24
routeids=['ttl-05-04','ttl-04-03','ttl-03-02','ttl-02-01','ttl-10-09','ttl-09-08','ttl-08-07','ttl-07-06'];routes=[next(r for r in top['routes']if r['id']==rid)for rid in routeids]
for w in right['strands']+left['strands']:
 r=next(r for r in routes if r['id']==w['routeId'])
 for e,pk in [('source',r['fromPort']),('target',r['toPort'])]:assert w[e]==top['ports'][pk]
curves={'schemaVersion':1,'curveCount':24,'units':'mm','paths':paths,'sourceHashes':sources};(D/'eight-leg-centerlines.json').write_text(json.dumps(curves,indent=2)+'\n')
parts=[]
for r in interfaces['parts']:
 assert sha(r['file'])==r['sha256'];q={k:v for k,v in r.items()if k not in['bounds','ownPorts','port']};q.update(name=f'{r["routeId"]} '+('180 mm conductor'if r['kind']=='wire'else'registered JST-EH receiving housing'),color='#bda356'if r['kind']=='wire'else'#ded7bc',group='Eight local leg cables — neutral checked',expectedFinalBoundsMm=r['bounds'],coordinates='world mm; identity',validationStatus='Receiving geometry: neutral external static clear; detailed mating/physical flexible fit pending');parts.append(q)
receipt={'passed':True,'scope':'Eight local leg cables in one original-body neutral scene. Physical socket bodies and neighbouring wires included. This is not powered walking, exact flexible deformation or electrical VDD acceptance.','wireCount':24,'housingCount':16,'allPairCount':780,'newWireObstacleExactPairs':len(read(D/'valid-right.json')['checks'])+len(read(D/'valid-left.json')['checks']),'rightNonAdjacentPrimitivePairs':len(read(D/'self-check.json')['rows']),'leftSelfCheckInheritedByExactReflection':True,'curveAudits':audits,'receivingShoulderContacts':contacts,'catalogueOwnSocketContacts': [r for r in housing['checks']if r['volumeMm3']>1e-7],'sourceHashes':sources,'centerlineSha256':sha(D/'eight-leg-centerlines.json'),'physicalFitVerified':False,'wholeHarnessAccepted':False};(D/'eight-leg-verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
manifest={'schemaVersion':1,'status':'EIGHT LOCAL LEG CABLES — SOURCE-BOUND NEUTRAL RECEIVING GEOMETRY CLEAR','wholeHarnessAccepted':False,'physicalFitVerified':False,'units':'mm','coordinateTransform':'identity','parts':parts,'routes':routes,'activeTopology':str(M/'active-topology.json'),'centerlineInput':str(D/'eight-leg-centerlines.json'),'centerlineSha256':sha(D/'eight-leg-centerlines.json'),'verificationFile':str(D/'eight-leg-verification.json'),'verificationSha256':sha(D/'eight-leg-verification.json'),'sourceHashes':sources,'scopeExclusions':['OpenRB/head/neck/trunk entry cables','Electrical distribution and powered commissioning','Exact flexible motion and physical housing fit'],'inheritedHipBinding':str(D/'topology-compatibility.json'),'replaceRouteIds':['ttl-05-04','ttl-04-03','ttl-03-02','ttl-02-01','ttl-09-10','ttl-08-09','ttl-07-08','ttl-06-07'],'excludedRemovedTopology':['ttl-01-06'],'installSequence':str(D/'INSTALL-SEQUENCE.md'),'completeInventory':str(D/'complete-interface-inventory.json'),'retentionIncrement':str(M/'retention-fusion-manifest.json'),'retentionDelta':str(D/'retention-delta.json'),'stockEvidence':{'source':'https://robotis.us/products/robot-cable-x3p-180mm-10pcs','sku':'903-0249-000','nominalLengthMm':180,'diameterReceivingAssumptionMm':1.5,'minimumBendReceivingAssumptionMm':2,'ODAndBendPublishedByManufacturer':False}}
(D/'eight-leg-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('40 parts, 24 native curve inputs, 8 routes',sha(D/'eight-leg-manifest.json'))
