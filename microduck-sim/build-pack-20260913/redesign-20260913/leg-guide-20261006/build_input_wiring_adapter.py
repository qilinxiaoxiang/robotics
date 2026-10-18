"""Exact local 20 V inlet overlay; no remote charger or full-tether geometry."""
import copy
from pathlib import Path
from build_body_wiring_adapter import G,I,read,sha,require,verify_file,verify_hashes,packed_mesh

MANIFEST=I/'input20v-manifest.json'
ACCEPTED_SHA='3d837b194bd6936e194b9a501c2cb62d165ab235dedc535607d731145c3f7d9c'
BASE_SHA='41d7e8f1f0c0a1c5734fa965b367270d13c86859820e15ddcddd92aaa9b1b66d'
CID='input20v-body-entry'
KEYS={'input20v_vin','input20v_gnd','input20v_gnd_joint','input20v_vin_pad'}
RETIRED={'charger-usb','input-return','regulator-input'}


def load_verified_manifest(path=MANIFEST,expected=ACCEPTED_SHA):
 verify_file(path,expected);m=read(path)
 require(m.get('integrationReady') is True and m.get('wholeHarnessAccepted') is False,'20 V manifest not ready or scope changed')
 require(m['basePowerManifestSha256']==BASE_SHA,'20 V base power revision differs')
 verify_file(m['basePowerManifest'],BASE_SHA);verify_file(m['receipt'],m['receiptSha256'])
 r=read(m['receipt'])
 require(r.get('passed') is True and r.get('selfClear') is True,'20 V static/self receipt failed')
 for key in ['wholeHarnessAccepted','physicalFitVerified','externalXT30MouldModelAccepted','externalTetherRetentionLoadTested']:
  require(r.get(key) is False,'20 V acceptance boundary changed: '+key)
 verify_hashes(m);verify_hashes(r)
 require({p['key'] for p in m['additionalParts']}==KEYS and len(m['additionalParts'])==4,'20 V geometry inventory changed')
 require([c['id'] for c in m['connections']]==[CID],'20 V connection inventory changed')
 for p in m['additionalParts']:
  verify_file(p['file'],p['sha256'])
  check_path=I/('input20v-check-'+p['key']+'.json')
  require(str(check_path) in m['sourceHashes'],'20 V mesh check not source bound')
  check=read(check_path);verify_hashes(check)
  require(check.get('complete') is True and check.get('passedStatic') is True and check.get('failures')==[],'20 V individual geometry check failed')
  corridor_path=I/'input20v-corridor.json'
  require(check['sourceHashes'].get(str(corridor_path))==sha(corridor_path),'20 V individual check corridor differs')
  corridor=read(corridor_path);verify_hashes(corridor)
  match=[x for x in corridor['parts'] if x['key']==p['key']]
  require(len(match)==1 and match[0]['file']==p['file'] and match[0]['sha256']==p['sha256'],'20 V individual check mesh differs')
  if p['key'] in ['input20v_vin','input20v_gnd']:
   require(p.get('selfClearance',{}).get('passed') is True,'20 V conductor self check failed')
 require(m.get('newPrintedParts')==[],'unexpected new printed part')
 return m,r


def display_tutorial():
 return {
  'prepare':[
   'Disconnect the charger and all robot power. Keep the torso covers off and the converter accessible.',
   'Use the MDY-14-ED with its original USB-A-to-C cable and the 20 V trigger. Keep the existing two-metre paired 18 AWG tether; the short section shown here is not a cutting guide.',
   'Thread both unterminated leads through the existing lower rear opening. Slide heat-shrink tubing onto the leads before making any joints.',
   'Prepare the existing common-ground lead and suitable insulation. Confirm a padded tie or strap is available to secure the cable to the lower bracket.'
  ],
  'assemble':[
   'With the converter accessible, solder the positive input lead to the VIN pad shown. Take it over the board edge, then behind the board and down through the lower opening. Keep it separate from the 5 V output.',
   'Join the incoming return to the existing common-ground lead at the highlighted junction. Interlock and solder the conductors, inspect the joint, and cover every exposed strand with insulation. Do not stack the branch wires on the PCB pad.',
   'Keep the insulated ground junction compact: no more than about 5.6 mm across and 10 mm long. Arrange it clear of the adjacent positive lead.',
   'Secure the external cable to the existing lower bracket with a padded tie or strap so pulling the cable cannot tug the solder joints. Do not put a screw through the cable.',
   'Finish the external connector only after threading the leads. Keep the trigger and XT30 outside the body and accessible for disconnection.'
  ],
  'check':[
   'With power disconnected, check VIN-to-GND polarity, absence of a short, continuity of the return, and complete insulation at both solder joints.',
   'Check the leads clear the opening and will not be pinched by the converter insert or torso covers. Gently pull the external cable; the solder joints must remain still.',
   'Before connecting the Pi or motors, measure 20 V at the trigger output and 5 V at the converter output. Do not infer the voltage from the charger label. Loaded-voltage checks remain part of commissioning.'
  ]}


def apply_input_wiring_adapter(data,wiring,spatial,manifest_path=MANIFEST):
 m,r=load_verified_manifest(manifest_path);d,w,s=copy.deepcopy((data,wiring,spatial))
 require(w.get('bodyWiringAdapter',{}).get('manifestSha256')==BASE_SHA,'apply body adapter before 20 V inlet')
 require(w.get('bodyDataAdapter') and w.get('imuWiringAdapter'),'apply DATA and IMU adapters before 20 V inlet')
 require(not w.get('inputWiringAdapter'),'20 V overlay already applied')
 c=m['connections'][0];tutorial=display_tutorial();parts={p['key']:p for p in m['additionalParts']}
 payload=[packed_mesh(p) for p in m['additionalParts']]
 existing={p['key'] for p in s['checkedHarnessMeshes']}
 require(not KEYS&existing,'duplicate 20 V geometry')
 s['checkedHarnessMeshes']+=payload
 # The prior rows drew an unverified remote source/full cable. The new local tutorial
 # retains the external electrical sequence, without asserting a fixed two-metre shape.
 for obj in [w,s]:obj['connections']=[x for x in obj['connections'] if x['id'] not in RETIRED]
 for step in w['steps']:step['connections']=[x for x in step.get('connections',[]) if x['id'] not in RETIRED]
 for group in w['groups']:group['connectionIds']=[x for x in group['connectionIds'] if x not in RETIRED]
 entry={'id':CID,'from':'External tether · two free leads below the bay','to':'DFR1202 VIN land and insulated ground T-splice',
  'purpose':'Thread the input leads, then terminate and inspect',
  'wire':'Paired 18 AWG input · the view shows the section inside the body',
  'pins':[],'fromNodeIds':[],'toNodeIds':[], 'groupIds':['torso-power'],'moduleId':'torso-power',
  'notes':['Keep the existing two-metre external tether. Dress its spare length outside the robot; do not cut it to the short section shown.'], 'tutorial':tutorial,
  'sourceTutorial':copy.deepcopy(c['tutorial']),'sourceWireSpecification':copy.deepcopy(c['wire']),'externalValidationBoundary':m['externalConnectorBoundary'],
  'assemblyOrder':{'powerDisconnected':True,'connectorBeforeClosure':True,'threadBeforeTermination':True,'sequence':copy.deepcopy(tutorial['assemble'])},
  'sourceManifestSha256':sha(manifest_path)}
 def end(key,role,label,position,illustrative):
  return {'id':CID+'-'+key,'role':role,'label':label,'position':copy.deepcopy(position),
   'outwardAxis':None,'illustrativeOnly':illustrative,'sourcePartKey':key}
 endpoints=[end('input20v_vin','from','VIN lead · external free end',parts['input20v_vin']['end'],True),
            end('input20v_gnd','from','GND lead · external free end',parts['input20v_gnd']['end'],True),
            end('input20v_vin_pad','to','DFR1202 · VIN solder pad',parts['input20v_vin_pad']['padWorldMm'],False),
            end('input20v_gnd_joint','to','Insulated return T-splice · branch entry',parts['input20v_gnd']['start'],True)]
 context=[p['key'] for p in s['checkedHarnessMeshes'] if p['key'].startswith('body_context_')]
 context += [p['key'] for p in read(m['basePowerManifest'])['additionalParts']]
 require(set(context)<=existing,'missing existing body/splice context')
 s['connections'].append({'id':CID,'segments':[],'checkedHarnessRoute':{
  'partKeys':[],'meshKeys':c['partKeys'],'contextMeshKeys':context,
  'coverPartKeys':[],'coverMeshKeys':['body_context_shell_left','body_context_shell_right'],
  'endpoints':endpoints,'manifestSha256':sha(manifest_path),
  'displayNote':'Thread both unterminated leads through the existing lower opening. Make and insulate the joints while the converter is accessible; inspect before closing the body.',
  'legend':['Local 20 V input section','Insulated common-ground T-splice','External cable remains flexible and unmodeled'],
  'neutralOnly':True,'wholeHarnessAccepted':False}})
 w['connections'].append(entry)
 step=next((x for x in w['steps'] if x['id']=='input20'),None)
 require(step is not None,'missing input20 stage')
 step.update(title='Thread and terminate the body input',connections=[copy.deepcopy(entry)],connectionIds=[CID],
             actions=copy.deepcopy(tutorial['assemble']),check=' '.join(tutorial['check']),powered=False)
 for x in w['steps']:x['connectionIds']=[a['id'] for a in x.get('connections',[])]
 group=next(x for x in w['groups'] if x['id']=='torso-power');group['connectionIds'].insert(0,CID)
 power=next(x for x in d['modules'] if x['id']=='power');ops={x['id']:x for x in power['operations']}
 require(all(k in ops for k in ['body-power-01','body-power-02','body-power-03','body-power-06']),'missing body sequence')
 op=ops['body-power-01'];op.update(title='Thread the disconnected input leads',tutorial={
  'prepare':copy.deepcopy(tutorial['prepare']),
  'assemble':['Keep the charger disconnected. Pass the unterminated VIN and return leads through the original lower opening; leave the converter and both ends accessible.',
              'Preload insulation. Leave the external connector unterminated until the leads have passed the opening.'],
  'check':['Confirm both leads reach the exposed converter without bearing on the opening edge. Keep both body covers off.']})
 # The return lead is established by power-02; complete its input T-joint before
 # power-03 seats the prewired converter. No new insertion motion is claimed.
 op=ops['body-power-03'];op['tutorial']['prepare'] += ['Confirm the input leads were threaded in the first step and the common-ground lead is now present. Keep all power disconnected.']
 op['tutorial']['assemble']=copy.deepcopy(tutorial['assemble'])+op['tutorial']['assemble']
 op['tutorial']['check']=tutorial['check'][:2]+op['tutorial']['check']
 ops['body-power-06']['tutorial']['check']+=copy.deepcopy(tutorial['check'])
 for op in [ops['body-power-01'],ops['body-power-03'],ops['body-power-06']]:op['text']=' '.join(op['tutorial']['assemble'])
 dependencies=[]
 for mod in d['modules']:
  for op in mod['operations']:
   shell=bool({'shell_left','shell_right'}&set(op.get('add',[])))
   if not shell and op['id'] not in ['body-power-01','body-power-03','body-power-06']:continue
   text=('Inspect the input insulation and strain relief before closing either body shell.' if shell else
         'Thread the input leads before terminating them; finish and inspect the input joints before seating the converter or closing the body.')
   dep={'id':'input20v-before-closure-'+op['id'],'text':text,'connectionIds':[CID],'ports':[],'motorIds':[]}
   w.setdefault('assemblyCablePrerequisites',{}).setdefault(op['id'],[]).append(dep)
   dependencies.append({'operationId':op['id'],'closure':shell})
 require(any(x['closure'] for x in dependencies),'20 V shell-closure deadline missing')
 binding={'manifestFile':str(manifest_path),'manifestSha256':sha(manifest_path),'receiptSha256':m['receiptSha256'],
  'adapterSha256':sha(__file__),'retiredUnverifiedSpatialConnections':sorted(RETIRED),
  'projectedAssemblyDependencies':dependencies,'scope':r['scope'],
  'normalGeometryChanged':False,'wholeHarnessAccepted':False,'physicalFitVerified':False,
  'sourcingHoldsChanged':False,'newPrintedParts':[]}
 for obj in [d,w,s]:obj['inputWiringAdapter']=copy.deepcopy(binding)
 s['connectionCount']=len(s['connections']);s['segmentCount']=sum(len(x.get('segments',[])) for x in s['connections'])
 return d,w,s
