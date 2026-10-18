"""Independent DATA-boundary and keyed zone-housing overlay, after body wiring."""
import copy
from pathlib import Path
from build_body_wiring_adapter import G,I,read,sha,require,verify_file,verify_hashes,packed_mesh,LEG_IDS

DATA_MANIFEST=I/'data-boundary-manifest.json'
HOUSING_MANIFEST=I/'zone-housing-manifest.json'
PINS={str(DATA_MANIFEST):'26584f7af1f4c226cccda9613575dce325ef4b1a0dd45c0ce042b1cbfb622c89',
      str(HOUSING_MANIFEST):'7c020eaefac972c4c6410bff55af4061835e7b2fb251486f12f818c9a8073a47'}
BASE_SHA='41d7e8f1f0c0a1c5734fa965b367270d13c86859820e15ddcddd92aaa9b1b66d'
DATA_IDS={'ttl-12-05-data-only','ttl-openrb-10-data-body'}
HOUSING_IDS={'zone-05-three-contact-termination','zone-10-three-contact-termination'}


def load_verified_manifest(path,expected):
 verify_file(path,expected);m=read(path)
 require(m.get('integrationReady') is True and m.get('wholeHarnessAccepted') is False,'DATA/housing manifest not ready or scope changed')
 require(m['basePowerManifestSha256']==BASE_SHA,'DATA/housing power revision differs')
 verify_file(m['basePowerManifest'],BASE_SHA);verify_file(m['receipt'],m['receiptSha256'])
 r=read(m['receipt'])
 require(r.get('passed') is True and r.get('wholeHarnessAccepted') is False and r.get('physicalFitVerified') is False,'DATA/housing receipt failed or scope changed')
 verify_hashes(m);verify_hashes(r)
 for p in m['additionalParts']:verify_file(p['file'],p['sha256'])
 require(len(m['additionalParts'])==2 and len(m['connections'])==2,'DATA/housing inventory incomplete')
 if {c['id'] for c in m['connections']}==DATA_IDS:
  require(r.get('complete') is True and r.get('selfClear') is True,'DATA route self/static check incomplete')
  for p in m['additionalParts']:require(p.get('selfClearance',{}).get('passed') is True,'DATA primitive self-check failed')
 else:
  require({c['id'] for c in m['connections']}==HOUSING_IDS,'unexpected housing IDs')
  check=read(I/'zone-housing-check.json')
  require(check.get('complete') is True,'housing swept check incomplete')
  require(r['approachMm']==12 and r['sampleSpacingMm']==.25 and r['ownMatingMaterialVerified'] is False,'housing insertion scope differs')
 return m,r


def endpoint(e,cid,role,label):
 return {'id':cid+'-'+role,'role':role,'label':label,'position':copy.deepcopy(e['position']),
         'outwardAxis':copy.deepcopy(e.get('outwardAxis')), 'sourceEndpoint':copy.deepcopy(e),
         'illustrativeOnly':e.get('illustrativeOnly',False)}


def apply_body_data_adapter(data,wiring,spatial,data_manifest=DATA_MANIFEST,housing_manifest=HOUSING_MANIFEST):
 dm,dr=load_verified_manifest(data_manifest,PINS[str(DATA_MANIFEST)])
 hm,hr=load_verified_manifest(housing_manifest,PINS[str(HOUSING_MANIFEST)])
 d,w,s=copy.deepcopy((data,wiring,spatial))
 require(w.get('bodyWiringAdapter',{}).get('manifestSha256')==BASE_SHA,'apply body adapter first')
 require(not w.get('bodyDataAdapter'),'DATA overlay already applied')
 old_leg={c['id']:c for c in w['connections'] if c['id'] in LEG_IDS}
 payload=[packed_mesh(p) for p in dm['additionalParts']+hm['additionalParts']]
 require(not {p['key'] for p in payload}&{p['key'] for p in s['checkedHarnessMeshes']},'duplicate DATA/housing mesh')
 s['checkedHarnessMeshes']+=payload
 context=[p['key'] for p in s['checkedHarnessMeshes'] if p['key'].startswith('body_context_')]
 covers=['body_context_shell_left','body_context_shell_right']
 power_wire_keys=[p['key'] for p in read(hm['basePowerManifest'])['additionalParts']]
 # The old motor12-to5 curve is superseded. Other unaccepted head segments remain accessible.
 for obj in [w,s]:obj['connections']=[c for c in obj['connections'] if c['id']!='data-06']
 for step in w['steps']:
  step['connections']=[c for c in step.get('connections',[]) if c['id']!='data-06']
 for group in w['groups']:group['connectionIds']=[cid for cid in group['connectionIds'] if cid!='data-06']
 entries=[];spentries=[]
 part_by_key={p['key']:p for p in dm['additionalParts']}
 labels={'ttl-12-05-data-only':('Motor ID12 · DATA pin3','Motor ID5 · DATA pin3'),
         'ttl-openrb-10-data-body':('Neck base · leave DATA end free','Motor ID10 · DATA pin3')}
 for c in dm['connections']:
  cid=c['id'];a,b=labels[cid];part=part_by_key[c['partKeys'][0]];motor=5 if cid=='ttl-12-05-data-only' else 10
  entries.append({'id':cid,'from':a,'to':b,'purpose':a+' → '+b,
    'wire':'One DATA conductor · independent receiving-side 5 V and ground',
    'pins':[],'fromNodeIds':[],'toNodeIds':[],'notes':[dr['materialLengthScope']],
    'tutorial':copy.deepcopy(c['tutorial']),'groupIds':['data','torso-power'],'moduleId':'data',
    'assemblyOrder':{'powerDisconnected':True,'connectorBeforeClosure':True,'sequence':copy.deepcopy(c['tutorial']['assemble'])},
    'neutralCenterlineLengthMm':part['lengthMm'],'stockCableLengthAccepted':False})
  spentries.append({'id':cid,'segments':[],'checkedHarnessRoute':{
    'partKeys':[],'meshKeys':c['partKeys'],
    'contextMeshKeys':context+power_wire_keys+[f'zone_{motor:02d}_receiving_housing'],
    'coverMeshKeys':covers,'coverPartKeys':[],
    'endpoints':[endpoint(c['fromEndpoint'],cid,'from',a),endpoint(c['toEndpoint'],cid,'to',b)],
    'displayNote':('Dress the DATA lead beside the power corridor. Leave the neck end free.' if motor==10 else 'Connect only DATA across this boundary. Keep each zone’s supply and return separate at the source plug.'),
    'legend':['DATA-only body route','Independent zone power','Actual spare length needs unpowered dressing'],
    'manifestSha256':sha(data_manifest),'additionalSourceBindings':{'housingManifestSha256':sha(housing_manifest)},
    'neutralOnly':True,'wholeHarnessAccepted':False}})
 for c in hm['connections']:
  cid=c['id'];motor=5 if cid.startswith('zone-05') else 10;housing=c['partKeys'][0]
  wire_key='data_12_05' if motor==5 else 'data_openrb_10'
  a=f'Keyed 3-contact plug for motor {motor}';b=f'Motor ID{motor} · highlighted socket'
  entries.append({'id':cid,'from':a,'to':b,'purpose':c['name'],
   'wire':'One JST-EH housing: pin1 GND, pin2 VDD, pin3 DATA','pins':[],
   'fromNodeIds':[],'toNodeIds':[],'notes':['Use the connector key and verify continuity with power disconnected.'],
   'tutorial':copy.deepcopy(c['tutorial']),'groupIds':['torso-power'],'moduleId':'torso-power',
   'relatedConnectionIds':copy.deepcopy(c['relatedConnectionIds']),
   'assemblyOrder':{'powerDisconnected':True,'connectorBeforeClosure':True,'sequence':copy.deepcopy(c['tutorial']['assemble'])}})
  ends=[endpoint(c['endpoint'],cid,'from',a),endpoint(c['endpoint'],cid,'to',b)]
  bench={'port':c['endpoint']['connectorId'],'endpointIndex':1,'movingMeshKeys':[housing],
   'fixedMeshKeys':[f'body_context_motor{motor}'],'axis':copy.deepcopy(c['endpoint']['outwardAxis']),
   'approachMm':12,'seatedOffsetMm':[0,0,0],
   'housingSha256':next(p['sha256'] for p in hm['additionalParts'] if p['key']==housing),
   'receiptSha256':hm['receiptSha256'],'openAssemblyOnly':True,
   'scope':hr['scope'],'ownMatingMaterialVerified':False}
  spentries.append({'id':cid,'segments':[],'checkedHarnessRoute':{
   'partKeys':[],'meshKeys':[housing],'contextMeshKeys':context+power_wire_keys+[wire_key],
   'coverMeshKeys':covers,'coverPartKeys':[],'endpoints':ends,'benchInsertion':[bench],
   'matingAnimation':copy.deepcopy(c['matingAnimation']),
   'displayNote':'Connect before closing the body shells. Hold the plug housing and dress the flexible leads by hand.',
   'legend':['Registered keyed port','12 mm open-socket approach','Catalogue housing; fine mating details not modeled'],
   'manifestSha256':sha(housing_manifest),'additionalSourceBindings':{'dataManifestSha256':sha(data_manifest)},
   'wholeHarnessAccepted':False,'neutralOnly':True}})
 # Keep the five stable body route IDs. Include their real receiving housing in installed views.
 for c in s['connections']:
  if c['id'] in ['power-zone-05-feed','power-zone-10-feed']:
   motor=5 if c['id']=='power-zone-05-feed' else 10;r=c['checkedHarnessRoute']
   r['contextMeshKeys']+= [f'zone_{motor:02d}_receiving_housing','data_12_05' if motor==5 else 'data_openrb_10']
   r['additionalSourceBindings']={'housingManifestSha256':sha(housing_manifest),'dataManifestSha256':sha(data_manifest)}
 w['connections']+=entries;s['connections']+=spentries
 w['steps'].append({'id':'body-data-and-plugs','title':'Body DATA boundaries and keyed plugs','connections':copy.deepcopy(entries),'connectionIds':[c['id'] for c in entries],'powered':False})
 for group in w['groups']:
  if group['id']=='data':group['description']='Connect the body DATA links and motion sensor before closing their covers. Each leg keeps its own local motor chain; there is no cable between the ankles.'
  group['connectionIds'] += [c['id'] for c in entries if group['id'] in c['groupIds'] and c['id'] not in group['connectionIds']]
 for step in w['steps']:step['connectionIds']=[c['id'] for c in step.get('connections',[])]
 # Source operation IDs, not numeric page indices: connect before the actual closure.
 dependencies=[
  {'id':'zone-plugs-before-body-shells','whenPartAdded':['shell_left','shell_right'],
   'text':'Seat both motor5 and motor10 incoming plugs and inspect their DATA and paired supply leads before closing either torso shell.',
   'connectionIds':sorted(HOUSING_IDS|DATA_IDS),'ports':['motor-5-socket-13','motor-10-socket-13'],'motorIds':[5,10]},
  {'id':'motor12-data-preparation-on-open-neck-bench','whenOperationIds':['neck-01'],
   'text':'Prepare the motor12 DATA-only outgoing connection on the open neck bench. Keep its source VDD and GND contacts isolated; dress the free end toward motor5 before fitting body shells.',
   'connectionIds':['ttl-12-05-data-only'],'ports':['motor-12-socket-14'],'motorIds':[12,5]},
  {'id':'zone-plugs-with-distribution-feed','whenOperationIds':['body-power-04'],
   'text':'Use these keyed plug views to connect the dedicated zone feeds. Preserve the eight existing three-conductor leg cables.',
   'connectionIds':sorted(HOUSING_IDS|DATA_IDS),'ports':['motor-5-socket-13','motor-10-socket-13'],'motorIds':[5,10]}]
 projected=[]
 for module in d['modules']:
  for op in module['operations']:
   for dep in dependencies:
    if op['id'] not in dep.get('whenOperationIds',[]) and not set(dep.get('whenPartAdded',[]))&set(op.get('add',[])):continue
    item={k:copy.deepcopy(v) for k,v in dep.items() if k not in ['whenOperationIds','whenPartAdded']}
    w.setdefault('assemblyCablePrerequisites',{}).setdefault(op['id'],[]).append(item)
    projected.append({'operationId':op['id'],'dependencyId':dep['id']})
 require(any(x['operationId']=='neck-13' for x in projected),'actual torso-shell closure dependency missing')
 binding={'dataManifestSha256':sha(data_manifest),'housingManifestSha256':sha(housing_manifest),
  'dataReceiptSha256':dm['receiptSha256'],'housingReceiptSha256':hm['receiptSha256'],
  'adapterSha256':sha(__file__),'removedLegacyConnectionIds':['data-06'],
  'projectedAssemblyDependencies':projected,'wholeHarnessAccepted':False,'physicalFitVerified':False}
 for obj in [d,w,s]:obj['bodyDataAdapter']=copy.deepcopy(binding)
 s['connectionCount']=len(s['connections']);s['segmentCount']=sum(len(c.get('segments',[])) for c in s['connections'])
 require(old_leg=={c['id']:c for c in w['connections'] if c['id'] in LEG_IDS},'local leg instructions changed')
 return d,w,s
