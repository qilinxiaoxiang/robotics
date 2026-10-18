"""Pure, source-bound body-harness overlay. Does not regenerate old wiring producers."""
from pathlib import Path
import array
import base64
import copy
import hashlib
import json
import math
import struct
import sys
from collections import Counter

G = Path(__file__).resolve().parent
I = G.parent / 'workflow-review-20261009/enclosed-wiring-repair/power-sensor/integrated-harness-20261009'
DEFAULT_MANIFEST = I / 'body-distribution-manifest.json'
# Explicit accepted release, not an integrationReady-only trust decision.
ACCEPTED_MANIFEST_SHA256 = '41d7e8f1f0c0a1c5734fa965b367270d13c86859820e15ddcddd92aaa9b1b66d'
LEG_IDS = {f'ttl-{a:02d}-{a-1:02d}' for a in [10,9,8,7,5,4,3,2]}
TITLES = {
 'power-dfr-5v-distribution': ('DFR1202 VOUT land', 'Insulated 5 V body splice'),
 'power-dfr-gnd-distribution': ('DFR1202 GND land', 'Insulated ground body splice'),
 'power-zone-05-feed': ('Paired body distribution splices', 'Motor ID 5 · highlighted 3-pin socket'),
 'power-zone-10-feed': ('Paired body distribution splices', 'Motor ID 10 · highlighted 3-pin socket'),
 'power-head-trunk': ('Paired body distribution splices', 'Neck base · leave the head leads free'),
}
DISPLAY = {
 'power-dfr-5v-distribution': ('16 AWG insulated lead · VOUT to the 5 V splice', 'Solder with the converter outside its holder. Insulate the splice and secure the insulated lead before closing the body.'),
 'power-dfr-gnd-distribution': ('16 AWG insulated lead · GND to the ground splice', 'Keep the ground lead beside the positive lead. Cover all exposed conductor at the distribution joint.'),
 'power-zone-05-feed': ('Paired 22 AWG leads · 5 V and ground', 'Keep both torso covers open. Feed these leads around the power support without disturbing the existing leg cables.'),
 'power-zone-10-feed': ('Paired 22 AWG leads · 5 V and ground', 'Keep both torso covers open. Feed these leads around the power support without disturbing the existing leg cables.'),
 'power-head-trunk': ('Paired 18 AWG leads · body to neck base', 'Leave the head ends free. This view shows the body section; keep additional wire for the moving neck and head connections.'),
}
LEGACY_CONNECTIONS = {'input-fuse','star-output','motor-main','pi-fuse','audio-fuse',
 'openrb-ground','pi-5v-2','pi-5v-4','audio-vin'} | {f'motor-F{i}' for i in range(1,9)}
FUSE_NODES = {'inputFuse'} | {f'F{i}' for i in range(11)}


def sha(path):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
 return json.loads(Path(path).read_text())


def require(condition, message):
 if not condition:
  raise ValueError('Body wiring adapter: ' + message)


def verify_file(path, expected):
 require(Path(path).is_file(), f'missing source {path}')
 require(sha(path) == expected, f'stale source {path}')


def verify_hashes(record):
 for path, digest in record.get('sourceHashes', {}).items():
  verify_file(path, digest)


def load_verified_manifest(path=DEFAULT_MANIFEST):
 verify_file(path, ACCEPTED_MANIFEST_SHA256)
 m = read(path)
 require(m.get('integrationReady') is True, 'manifest not ready')
 require(m.get('wholeHarnessAccepted') is False, 'local receipt cannot release whole harness')
 verify_file(m['receipt'], m['receiptSha256'])
 r = read(m['receipt'])
 require(r.get('passed') is True and r.get('localGeometry', {}).get('passed') is True,
         'overall or local geometry receipt failed')
 require(r.get('physicalCommissioningPassed') is False and r.get('wholeHarnessAccepted') is False,
         'unexpected commissioning/whole-harness claim')
 require(r.get('acceptanceScope') == m['integrationScope'], 'acceptance scope mismatch')
 verify_hashes(m); verify_hashes(r)
 self_ref = r['selfCheckReceipt']; verify_file(self_ref['file'], self_ref['sha256'])
 self_report = read(self_ref['file'])
 require(self_report.get('passed') is True and self_report.get('complete') is True,
         'wire self-check incomplete or failed')
 require(len(self_report['rows']) == self_report['expectedPaths'], 'self-check inventory incomplete')
 for row in self_report['rows']:
  require(row.get('selfCheck', {}).get('passed') is True, 'failed wire self-check ' + row['key'])
  if row.get('file') and row.get('sha256'):
   verify_file(row['file'], row['sha256'])
 for ref in [m['contextPartsSource'], m['zoneFeedReceipt'], *m['headTrunkReceipts']]:
  verify_file(ref['file'], ref['sha256'])
 for ref in [m['zoneFeedReceipt'], *m['headTrunkReceipts']]:
  dependent=read(ref['file'])
  require(dependent.get('complete') is True and dependent.get('passedStatic') is True, 'failed dependent route receipt')
 require(len(m['additionalParts']) == 12 and len(m['contextParts']) == 10, 'unexpected mesh inventory')
 require({c['id'] for c in m['connections']} == set(TITLES), 'unexpected connection inventory')
 for part in m['additionalParts'] + m['contextParts']:
  verify_file(part['file'], part['sha256'])
 return m, r


def packed_mesh(part, *, context=False):
 """Pack source triangles directly; apply ONLY the declared context translation."""
 verify_file(part['file'], part['sha256'])
 raw = Path(part['file']).read_bytes()
 binary = len(raw) >= 84 and len(raw) == 84 + 50 * struct.unpack_from('<I', raw, 80)[0]
 def vertices():
  if binary:
   for off in range(84, len(raw), 50):
    for n in range(3):
     yield struct.unpack_from('<3f', raw, off + 12 + 12*n)
  else:
   for line in raw.decode('ascii').splitlines():
    fields = line.split()
    if fields and fields[0] == 'vertex':
     require(len(fields) == 4, 'invalid ASCII STL vertex')
     yield tuple(float(x) for x in fields[1:])
 delta = part.get('importTranslationMm', [0.,0.,0.]) if context else [0.,0.,0.]
 require(len(delta) == 3 and all(math.isfinite(v) for v in delta), 'invalid context translation')
 pos = bytearray(); indices = array.array('I'); seen = {}
 bounds = [[float('inf')]*3, [float('-inf')]*3]; rounding = 0.
 for vertex in vertices():
  v = tuple(a+b for a,b in zip(vertex,delta))
  require(all(math.isfinite(x) for x in v), 'nonfinite mesh vertex')
  packed = struct.pack('<3f', *v)
  rendered = struct.unpack('<3f', packed)
  rounding = max(rounding, *(abs(a-b) for a,b in zip(v,rendered)))
  for k in range(3):
   bounds[0][k] = min(bounds[0][k],v[k]); bounds[1][k] = max(bounds[1][k],v[k])
  if packed not in seen:
   seen[packed] = len(seen); pos.extend(packed)
  indices.append(seen[packed])
 require(len(indices) > 0 and len(indices) % 3 == 0, 'invalid triangle inventory')
 require(rounding <= 0.00002, 'unexpected float32 rendering error')
 if part.get('expectedFinalBoundsMm'):
  require(max(abs(a-b) for row,expected in zip(bounds,part['expectedFinalBoundsMm'])
              for a,b in zip(row,expected)) < 0.0001, 'context final bounds mismatch ' + part['key'])
 if sys.byteorder != 'little': indices.byteswap()
 out = {'key': ('body_context_' if context else '') + part['key'],
        'color':part.get('color','#777777'), 'sha256':part['sha256'], 'sourceFile':part['file'],
        'positionB64':base64.b64encode(pos).decode(), 'indexB64':base64.b64encode(indices.tobytes()).decode(),
        'vertexCount':len(seen), 'triangleCount':len(indices)//3,
        'expectedFinalBoundsMm':bounds, 'importTranslationMm':delta,
        'coordinateRule':'Source triangles plus declared translation only; float32 display encoding.',
        'maximumDisplayRoundingMm':rounding, 'noCurveReconstruction':True}
 if context:
  out.update(nativePartKey=part['key'], partKey=part['key'], sourceContext=copy.deepcopy(part))
 return out


def triangle_coordinates(part):
 raw=base64.b64decode(part['positionB64'])
 verts=[raw[i:i+12] for i in range(0,len(raw),12)]
 ids=[x[0] for x in struct.iter_unpack('<I',base64.b64decode(part['indexB64']))]
 return Counter(tuple(sorted(verts[ids[i+j]] for j in range(3))) for i in range(0,len(ids),3))


def endpoints(connection):
 result=[]
 for role in ['from','to']:
  endpoint=connection[role+'Endpoint']; points=endpoint.get('positionsMm')
  if points is None: points=[endpoint['position']]
  for n,point in enumerate(points):
   result.append({'id':connection['id']+'-'+role+'-'+str(n), 'role':role,
     'label':TITLES[connection['id']][0 if role=='from' else 1], 'position':point,
     'outwardAxis':endpoint.get('outwardAxis'), 'illustrativeOnly':endpoint.get('illustrativeOnly',False),
     'sourceEndpoint':copy.deepcopy(endpoint)})
 return result


def apply_body_wiring_adapter(data, wiring, spatial, manifest_path=DEFAULT_MANIFEST):
 """Return three independent copies; never write files or mutate caller objects."""
 m,r=load_verified_manifest(manifest_path)
 d,w,s=copy.deepcopy((data,wiring,spatial))
 require(not w.get('bodyWiringAdapter'), 'overlay already applied')
 preserved={c['id']:c for c in wiring['connections'] if c['id'] in LEG_IDS}
 require(set(preserved)==LEG_IDS, 'eight regional leg routes required')
 removed_parts=set(m['removedParts']+m['supersededLegacyPowerParts'])
 removed_screws=set(m['supersededLegacyPowerScrews'])
 d['parts']=[p for p in d['parts'] if p['key'] not in removed_parts]
 for screw in d['screws']:
  if screw['id'] in removed_screws:
   spec=screw['spec'];d['screwTotals'][spec]-=screw.get('quantity',1)
 d['screwTotals']={k:v for k,v in d['screwTotals'].items() if v}
 d['screws']=[x for x in d['screws'] if x['id'] not in removed_screws]
 for module in d['modules']:
  for field in ['partKeys','contextPartKeys','ownedPartKeys']:
   if field in module: module[field]=[x for x in module[field] if x not in removed_parts]
  for op in module['operations']:
   for field in ['add','highlightKeys','isolatedPartKeys','visiblePartKeys','moveKeys','priorPartKeys']:
    if field in op:op[field]=[x for x in op[field] if x not in removed_parts]
   for field in ['screwIds','movingScrewIds','priorScrewIds']:
    if field in op:op[field]=[x for x in op[field] if x not in removed_screws]
 # Existing body reference is shown for inspection. No fabricated insertion is animated.
 power=next(x for x in d['modules'] if x['id']=='power')
 power.update(title='Body power distribution · prepare and inspect', ownedPartKeys=[],
              partKeys=m['focusPartKeys'], contextPartKeys=m['focusPartKeys'], operations=[],
              checks=[m['integrationScope'],'Keep power disconnected during assembly.'])
 source_steps={x['id']:x for x in r['steps']}
 require(len(source_steps)==6,'expected six source tutorial stations')
 for source in r['steps']:
  op_id='body-'+source['id']
  tutorial={phase:copy.deepcopy(source[phase]) for phase in ['prepare','assemble','check']}
  require(all(tutorial.values()),'empty tutorial phase')
  power['operations'].append({'id':op_id,'sourceTutorialStepId':source['id'],'kind':'inspect',
   'title':source['title'],'text':' '.join(source['assemble']), 'add':[], 'screwIds':[],
   'isolatedPartKeys':m['focusPartKeys'],'visiblePartKeys':m['focusPartKeys'],'tutorial':tutorial,
   'motionEvidence':{'status':'static-reference-inspection','wholeHarnessAccepted':False},
   'beforeClose':['Inspect the actual dressed harness before closing; the flexible handling path is not animated.']})
 removed_connections=set(LEGACY_CONNECTIONS)
 removed_connections|={c['id'] for c in w['connections'] if FUSE_NODES & set(c.get('fromNodeIds',[])+c.get('toNodeIds',[]))}
 require(not removed_connections & LEG_IDS,'attempted leg-route removal')
 for obj in [w,s]:
  obj['connections']=[c for c in obj['connections'] if c['id'] not in removed_connections]
  obj['nodes']=[n for n in obj.get('nodes',[]) if n['id'] not in FUSE_NODES]
 for step in w['steps']:
  step['connections']=[c for c in step.get('connections',[]) if c['id'] not in removed_connections]
 w['steps']=[x for x in w['steps'] if x['id'] not in ['fuses','motor-power']]
 for group in w['groups']:
  group['connectionIds']=[x for x in group['connectionIds'] if x not in removed_connections]
 # Retire old electrical budgets/branch metadata, without claiming a completed head route.
 for field in ['motor_fused_groups','fuse_stage_note']:
  w.pop(field,None)
 w['single_source']='MDY-14-ED with its original cable → 5991 fixed 20 V → 2 m XT30 tether → DFR1202 in the original battery bay → dedicated 5 V supply and return pairs.'
 w['power_stage_note']='Keep the charger disconnected while assembling. Seat each plug before its cover closes access; inspect polarity, insulation and retained slack before applying power.'
 s['historicalSourceAssertionsNotCurrent']=s.pop('assertionsPassed',[])
 s['assertionsPassed']=['Body power overlay is bound to its accepted local mesh and route receipts','Withdrawn external fuse array and its connection records are removed','The eight local leg cable records are preserved; complete head routing is not accepted by this body overlay']
 s['historicalSourceLimitationsNotCurrent']=s.pop('limitations',[])
 s['limitations']=['Checked routes display the native geometry from their linked local CAD receipts. Other routes remain conceptual until replaced by an accepted overlay.',
  'Dedicated supply and return pairs power each zone. Only DATA crosses between the controller and the two leg power zones; there is no cross-ankle cable.',
  'The complete head harness, moving-joint slack and populated closure remain pending.',
  'The external charger and free tether are shown schematically; no physical routing or powered commissioning has been performed.']
 w['powerArchitecture']={'sourceReceiptSha256':m['receiptSha256'],'powerGroups':copy.deepcopy(r['powerGroups']),
   'crossZoneContactPolicy':copy.deepcopy(r['crossZoneContactPolicy']), 'wholeHarnessAccepted':False,
   'remainingEngineeringWork':copy.deepcopy(r['remainingEngineeringWork'])}
 # Replace stale stage-level fuse/old cross-ankle instructions from the accepted source tutorial.
 stage_source={'input20':'power-01','converter':'power-02','motor-data':'power-04',
               'pi-usb':'power-05','audio':'power-05','inspect':'power-06'}
 for step in w['steps']:
  if step['id'] in stage_source:
   src=source_steps[stage_source[step['id']]]
   step['actions']=copy.deepcopy(src['assemble']); step['check']=' '.join(src['check'])
   step['sourceTutorialStepId']=src['id']
 for pin in w.get('pi_header_pins',[]):
  if pin.get('physical_pin') in [2,4]:pin['role']='Dedicated head 5 V distribution → Pi 5 V; route pending'
  if pin.get('physical_pin') in [6,14]:pin['role']='Dedicated head ground return; route pending'
 for c in w['connections']:
  if c['id'] in ['pi-gnd-6','pi-gnd-14']:
   c['tutorial']=copy.deepcopy({k:source_steps['power-05'][k] for k in ['prepare','assemble','check']})
   c['assemblyOrder']={'powerDisconnected':True,'sequence':copy.deepcopy(source_steps['power-05']['assemble'])}
 # DATA-only inter-zone links have no accepted geometry here; retain as explicit conceptual records.
 for obj in [w,s]:
  for c in obj['connections']:
   if c['id'] in ['data-01','data-06']:
    c['geometryStatus']='concept-only; cross-zone receiving route not accepted'
    if obj is s:c['segments']=[];c.pop('checkedHarnessRoute',None)
    else:
     c['wire']='DATA pin 3 only across this power-zone boundary; source-side VDD and GND terminals isolated.'
     c['notes']=['Preserve the internal three-conductor leg chains. Dedicated power and return join at body distribution.', 'This boundary route is not included in the accepted neutral body geometry.']
     c['tutorial']=copy.deepcopy({k:source_steps['power-04'][k] for k in ['prepare','assemble','check']})
 payload=[packed_mesh(p) for p in m['additionalParts']]+[packed_mesh(p,context=True) for p in m['contextParts']]
 require(len({p['key'] for p in payload})==22,'duplicate native mesh key')
 equivalence={}
 for key in ['regulator','regulator_insert','power_support']:
  existing=next(p for p in d['parts'] if p['key']==key)
  context=next(p for p in payload if p.get('nativePartKey')==key)
  require(triangle_coordinates(existing)==triangle_coordinates(context), 'assembly reference differs from checked body context '+key)
  equivalence[key]={'equalTriangleCoordinateMultisets':True,'triangleCount':context['triangleCount'],'contextSourceSha256':context['sha256']}

 s['checkedHarnessMeshes']=payload
 entries=[]; spatial_entries=[]
 contextkeys=['body_context_'+x['key'] for x in m['contextParts']]
 covers=['body_context_shell_left','body_context_shell_right']
 for c in m['connections']:
  tutorial={phase:[text for sid in c['tutorialStepIds'] for text in source_steps[sid][phase]]
            for phase in ['prepare','assemble','check']}
  a,b=TITLES[c['id']]
  entries.append({'id':c['id'],'from':a,'to':b,'purpose':a+' → '+b,
   'wire':DISPLAY[c['id']][0],
   'pins':[],'notes':['Keep power disconnected. Arrange the flexible leads by hand; the illustrated bends are not a folding template.'], 'tutorial':tutorial,
   'groupIds':['torso-power'],'moduleId':'torso-power','fromNodeIds':[],'toNodeIds':[],
   'assemblyOrder':{'powerDisconnected':True,'connectorBeforeClosure':True,'sequence':tutorial['assemble']},
   'sourceManifestSha256':sha(manifest_path)})
  spatial_entries.append({'id':c['id'],'segments':[], 'checkedHarnessRoute':{
   'partKeys':[], 'coverPartKeys':[], 'meshKeys':c['partKeys'],'contextMeshKeys':contextkeys,
   'coverMeshKeys':covers,'endpoints':endpoints(c),'manifestSha256':sha(manifest_path),
   'displayNote':DISPLAY[c['id']][1],
   'legend':['Insulated conductors','Covered solder joints'],
   'wholeHarnessAccepted':False, 'neutralOnly':True}})
 w['connections']+=entries;s['connections']+=spatial_entries
 current_by_id={c['id']:c for c in w['connections']}
 for step in w['steps']:
  step['connections']=[copy.deepcopy(current_by_id[c['id']]) for c in step.get('connections',[]) if c['id'] in current_by_id]
  step['connectionIds']=[c['id'] for c in step['connections']]
 w['steps'].append({'id':'body-distribution','title':'Body distribution · five local routes','connections':copy.deepcopy(entries)})
 powergroup=next(x for x in w['groups'] if x['id']=='torso-power')
 powergroup.update(title='Body and power',description='Prepare the converter and body distribution with both side covers open. Complete each connection before closing its access.',connectionIds=[c['id'] for c in entries]+powergroup['connectionIds'])
 prereqs=w.setdefault('assemblyCablePrerequisites',{})
 for op in power['operations']:
  ids=[c['id'] for c in m['connections'] if op['sourceTutorialStepId'] in c['tutorialStepIds']]
  if ids:prereqs[op['id']]=[{'id':op['id']+'-routes','text':'Inspect these local routes with both body covers open.','connectionIds':ids,'ports':[],'motorIds':[]}]
 binding={'manifestFile':str(manifest_path),'manifestSha256':sha(manifest_path),
   'receiptSha256':m['receiptSha256'],'selfCheckReceiptSha256':r['selfCheckReceipt']['sha256'],
   'adapterSha256':sha(__file__),'scope':m['integrationScope'],'wholeHarnessAccepted':False,
   'removedLegacyConnectionIds':sorted(removed_connections),'removedPartKeys':sorted(removed_parts),
   'removedScrewIds':sorted(removed_screws),'normalGeometryChanged':False,
   'assemblyContextEquivalence':equivalence}
 for obj in [d,w,s]:obj['bodyWiringAdapter']=copy.deepcopy(binding)
 s['connectionCount']=len(s['connections']);s['segmentCount']=sum(len(x.get('segments',[])) for x in s['connections'])
 require({c['id']:c for c in w['connections'] if c['id'] in LEG_IDS}==preserved,'regional leg data changed')
 for key in ['checkedLegMeshes','checkedLegRetentionMeshes','regionalLegAdapter']:
  require(s.get(key)==spatial.get(key),'regional leg spatial payload changed '+key)
 return d,w,s
