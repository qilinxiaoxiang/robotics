"""Source-bound BNO085 local assembly and four body-side leads; no Pi-end fiction."""
import copy
from pathlib import Path
from build_body_wiring_adapter import read,sha,require,verify_file,verify_hashes,packed_mesh

G=Path(__file__).resolve().parent
D=G.parent/'workflow-review-20261009/enclosed-wiring-repair/power-sensor'
DEFAULT_MANIFEST=D/'imu-local-manifest.json'
ACCEPTED_MANIFEST_SHA256='b85d5e941b7b25a5e7a290b6a0aaa5daa470f048d074c504328399f8bc94fc0c'
EXTERNAL_REPORT=D/'imu-external-clearance.json'
EXTERNAL_SHA256='3237d3148692c6c5624a764bd429d336eede53c32caeb5c6c9e9b3201d674f2b'
DELTA_DIR=G.parent/'workflow-review-20261009/enclosed-wiring-repair/assembly-motion-completion/imu-holder-delta'
DELTA_HASHES={'holder-check.json': 'd8c56b89bb7808cb9d8031b9c51691ba223c302535b04c3354d7458c9b397680', 'tools-check.json': '4347b3442fa0b2d89c7714b5f3ea5ccdfbe3038a24464acd70b8a4e50f7e2ece'}
NETS=[('gnd','GND','imu-gnd',9),('3v3','3V3','imu-vin',1),('sda','SDA','imu-sda',3),('scl','SCL','imu-scl',5)]
IDENTITY=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]


def load_verified_manifest(path=DEFAULT_MANIFEST):
 verify_file(path,ACCEPTED_MANIFEST_SHA256);m=read(path)
 require(m.get('localDigitalAssemblyAccepted') is True and m.get('wholeHarnessAccepted') is False,'IMU acceptance scope invalid')
 verify_file(m['acceptance']['report'],m['acceptance']['sha256']);r=read(m['acceptance']['report'])
 require(r.get('passed') is True and r.get('complete') is True and not r['failures'],'IMU local check failed')
 require(len(r['checks'])==r['expectedChecks']==m['acceptance']['checks']==941,'IMU local check inventory incomplete')
 verify_hashes(m);verify_hashes(r)
 verify_file(EXTERNAL_REPORT,EXTERNAL_SHA256);external=read(EXTERNAL_REPORT)
 require(external.get('passed') is True and external.get('complete') is True and external['completedChecks']==external['expectedChecks'],'IMU external check failed/incomplete')
 verify_hashes(external)
 for name,digest in DELTA_HASHES.items():
  path=DELTA_DIR/name;verify_file(path,digest);delta=read(path)
  require(delta.get('passed') is True and not delta.get('failures'),'IMU holder/tool delta failed')
  verify_hashes(delta);verify_file(DELTA_DIR/'check_delta.py',delta['scriptSha256'])
 reg=read(D/'bno085-endpoint-registration.json')
 require(reg.get('rotationDeterminant')==1,'mirrored IMU registration rejected')
 for p in m['parts']:
  verify_file(p['file'],p['sha256']);verify_file(p['meshFile'],p['meshSha256'])
  require(p['meshCoordinates']=='world millimetres; no extra transform','unexpected IMU mesh frame')
 require(len(m['parts'])==8,'IMU part inventory differs')
 return m,r,reg


def mesh_part(p):
 return packed_mesh({'key':p['key'],'file':p['meshFile'],'sha256':p['meshSha256'],
                     'color':p['color'],'expectedFinalBoundsMm':p['expectedFinalBoundsMm']})


def tutorial(prepare,assemble,check):
 return {'prepare':prepare,'assemble':assemble,'check':check}


def apply_imu_wiring_adapter(data,wiring,spatial,manifest_path=DEFAULT_MANIFEST):
 m,r,reg=load_verified_manifest(manifest_path)
 d,w,s=copy.deepcopy((data,wiring,spatial))
 require(not d.get('imuWiringAdapter'),'IMU overlay already applied')
 payload={p['key']:mesh_part(p) for p in m['parts']}
 source={p['key']:p for p in m['parts']}
 core=['imu_clamp','imu_board','imu_cover'];plug='imu_sh4_receiving'
 old_by_key={p['key']:p for p in d['parts']}
 names={'imu_clamp':'IMU holder','imu_board':'BNO085 motion sensor','imu_cover':'IMU rear cover','imu_sh4_receiving':'JST SH 4-pin plug'}
 for key in core+[plug]:
  src=source[key];packed=payload[key];old=old_by_key.get(key,{})
  bounds=packed['expectedFinalBoundsMm']
  part={**old,**{k:packed[k] for k in ['positionB64','indexB64','color']},'key':key,'name':names[key],
        'bounds':bounds,'center':[(a+b)/2 for a,b in zip(*bounds)],
        'dimensions':[b-a for a,b in zip(*bounds)],'triangles':packed['triangleCount'],
        'sourceFile':src['meshFile'],'sourceMeshSha256':src['meshSha256'],'sourceTransformWorld':IDENTITY,
        'manufacturerSourceToWorld':src['sourceToWorld'],'moduleId':'imu','body':'trunk_base',
        'geometryKind':'checked-local-revision' if key in ['imu_clamp','imu_cover'] else 'manufacturer-reference' if key=='imu_board' else 'connector-receiving-envelope',
        'partKind':'print' if key in ['imu_clamp','imu_cover'] else 'electronics',
        'description':{'imu_clamp':'Revised holder with an accessible side connector opening. Reuse the two M2 × 6 clamp screws.','imu_board':'Adafruit BNO085 board. Match its four mounting holes and labeled cable socket.','imu_cover':'Revised cover with PCB supports and cable-retention slots.','imu_sh4_receiving':'Keyed housing on the four-wire sensor cable; insert before closing the rear cover.'}[key], 'sourceDescription':src['name']+'. '+m['acceptance']['scope'],
        'revisionSourceManifestSha256':sha(manifest_path)}
  if key in old_by_key:d['parts'][d['parts'].index(old)]=part
  else:d['parts'].append(part)
 module=next(x for x in d['modules'] if x['id']=='imu')
 clamp_screws=[x['id'] for x in d['screws'] if x['id'].startswith('E-imu_clamp-')]
 cover_screws=[x['id'] for x in d['screws'] if x['id'].startswith('E-imu_rear_cover-')]
 require(len(clamp_screws)==2 and len(cover_screws)==4,'IMU original mounting hardware missing')
 checked_screws={x['id']:x for x in read(DELTA_DIR.parent/'station-inputs/imu-04.json')['screws']}
 for screw in d['screws']:
  if screw['id'] in clamp_screws+cover_screws:
   checked=checked_screws[screw['id']]
   for field in ['world_center_mm','world_axis','length_mm','washer_mm']:
    require(screw.get(field,0)==checked.get(field,0),'IMU screw differs from tool receipt '+screw['id']+' '+field)

 for screw in d['screws']:
  if screw['id'] in clamp_screws:
   note='Use the revised IMU holder and the two existing M2 × 6 TAP clamp screws. Stop when their tips contact the rails; leave the heads about 1.8 mm proud. Do not tighten the heads flush or add washers.'
   screw['fastenerRevision'].update(notice=note,requiresRevisedPart='imu_clamp');screw['evidence']=note

 clamp_specs=sorted({x['spec'] for x in d['screws'] if x['id'] in clamp_screws})
 cover_specs=sorted({x['spec'] for x in d['screws'] if x['id'] in cover_screws})
 context=[k for k in ['power_support','torso_base'] if k in old_by_key]
 scope='Local digital fit only. Real printed tolerance, comfortable hand access, head continuation and powered sensing remain separate checks.'
 tutorials=[
  tutorial(['Disconnect power. Keep the BNO085 board and rear cover off the holder.', 'Identify the existing holder rails and the two retained clamp screws: '+', '.join(clamp_specs)+'.'],
   ['Position the revised holder at its original torso station and retain it with the existing two clamp screws. Do not overtighten the plastic pilots.','Slide the empty holder onto the fixed rails from the open rear (−X), then start and gently tighten both clamp screws.'],
   ['The holder is stable on the fixed torso rails. Its side aperture and four PCB locating pins remain accessible.',scope]),
  tutorial(['Keep the rear cover and cable plug off. Locate the BNO085 component side and four mounting holes.'],
   ['Bring the board from the open rear (−X) onto the four locating pins. The component side faces the open rear.'],
   ['All four mounting holes locate without bending the PCB; the components do not bear on the holder. Record the sensor axis markings.']),
  tutorial(['Prepare the JST SH 4-contact cable with power disconnected. Find the highlighted side socket; verify its GND, 3V3, SDA and SCL labels.','Leave the rear cover off.'],
   ['Hold the connector housing and align its key with the highlighted side socket, and insert straight. Do not pull on the four wires.', 'Dress the four insulated leads through the exit by hand before fitting the cover.'],
   ['The keyed housing is seated. No insulated lead crosses a locating pin or the cover seam.','This housing-volume check does not certify the fine mating contact surfaces.']),
  tutorial(['Confirm the SH plug is already seated and all four wires are outside the seam. Keep the four rear screws out.'],
   ['Bring the rear cover in from −X. Its annular stops contact only the PCB mounting-hole surrounds. Guide the flexible leads by hand.'],
   ['The cover meets the holder without force or component compression. Inspect every seam before starting a screw.']),
  tutorial(['Prepare the four original rear-cover screws: '+', '.join(cover_specs)+'.'],
   ['Start all four rear-cover screws, then tighten gently and evenly into the existing pilots. Do not substitute longer screws.'],
   ['The nominal axial PCB freeplay is at most 0.2 mm; confirm retention without squeezing components.', 'The checked tool envelope is a 3 mm shaft with an 18 mm × 60 mm handle. Use a suitable driver and confirm comfortable access on the actual assembly.']),
  tutorial(['Prepare one 4.8 mm nylon tie for the integral cover slots; available stock is not assumed.','Identify the four free ends before extending toward the head.'],
   ['Thread the tie after closing and fastening the cover. Retain only the insulated leads, with gentle strain relief at the SH plug.','Lay the body-side leads to the open neck-root boundary. Leave the ends free; do not treat this as a connection to the Pi.'],
   ['The tie does not crush insulation or pull the plug. The actual leads clear the cover seam and moving mechanisms.', 'The 150 mm nominal cable has only the remaining allowance listed in the route view. Head extension and the moving neck loop are not accepted by this local record.'])]
 specs=[
  ('holder','place','Retain the open holder',['imu_clamp'],clamp_screws,['imu_clamp'],[-28,0,0]),
  ('board','place','Seat BNO085 before its cable',['imu_board'],[],['imu_clamp','imu_board'],[-25,0,0]),
  ('plug','place','Connect SH4 before closing the cover',[plug],[],['imu_clamp','imu_board',plug],[0,-12,0]),
  ('cover','place','Close the populated rear cover',['imu_cover'],[],core+[plug],[-20,0,0]),
  ('fasten','fasten','Fasten the four original cover screws',[],cover_screws,core+[plug],None),
  ('retain','inspect','Retain leads; leave neck ends free',[],[],core+[plug],None)]
 operations=[]
 for (name,kind,title,add,screws,visible,approach),t in zip(specs,tutorials):
  op={'id':'imu-local-'+name,'kind':kind,'title':title,'text':' '.join(t['assemble']),
      'add':add,'screwIds':screws,'tutorial':t,'isolatedPartKeys':visible+context,'visiblePartKeys':visible+context,
      'highlightKeys':add,'priorScrewIds':clamp_screws if name!='holder' else [],
      'motionEvidence':{'status':'sampled-local-path' if approach else 'inspection-or-fastening',
                        'receiptSha256':m['acceptance']['sha256'],'scope':scope,'caption':'The shown approach was checked against the nearby parts. Hold the plug housing and guide the flexible leads by hand; confirm the real fit before tightening.' if name=='plug' else 'The shown approach was checked against the nearby parts. Pause or drag to inspect it; confirm the real printed fit before tightening.' if approach else 'Use the indicated screw positions and accessible driver direction.'}}
  if name=='holder':op['motionEvidence']['receiptSha256']=DELTA_HASHES['holder-check.json']
  if screws:op['toolEvidence']={'receiptSha256':DELTA_HASHES['tools-check.json'],'shaftDiameterMm':3,'handleDiameterMm':18,'handleLengthMm':60}
  if name=='retain':op['priorScrewIds']=clamp_screws+cover_screws
  if approach:op['partApproachVectors']={add[0]:approach}
  operations.append(op)
 module.update(title='Torso IMU · connect before cover',operations=operations,
   ownedPartKeys=core+[plug],partKeys=core+[plug]+context,contextPartKeys=context,
   checks=[scope,'No Pi endpoint is shown as connected.'])
 # Local routes retain IDs for existing navigation, but replace their old Pi-to-board illustration.
 ids={row[2] for row in NETS}
 w['connections']=[c for c in w['connections'] if c['id'] not in ids]
 s['connections']=[c for c in s['connections'] if c['id'] not in ids]
 port=next(p for p in reg['ports'] if p['id']=='CONN4')
 new=[];newsp=[]
 for index,(net,label,cid,pin) in enumerate(NETS):
  length=m['wireLengthBoundary'][label]
  t=tutorial(['Keep power disconnected. Identify the '+label+' contact at both ends of the SH4 cable.','Prepare the nominal 150 mm cable; do not cut from the rendered example.'],
    ['Connect SH4 while the rear cover is absent. Dress this lead along the checked body corridor, then close the cover and fit the tie.','Leave the free end at the open neck-root boundary. Its eventual Pi destination is physical pin '+str(pin)+', but that continuation is not modeled here.'],
    ['Verify '+label+' continuity and insulation with both ends unpowered.',f"Body-side example {length['routedLengthMm']:.2f} mm; nominal remaining allowance {length['remainingNominalMm']:.2f} mm after the stated connector reserve. Actual usable length must be checked.",'No claim is made that 150 mm reaches the Pi through the articulated neck.'])
  new.append({'id':cid,'from':'BNO085 CONN4 · '+label,'to':'Open neck-root lead · '+label,
    'purpose':label+' · body-side IMU lead','wire':'One conductor of the nominal 150 mm SH4 cable',
    'pins':[],'fromNodeIds':[],'toNodeIds':[],'groupIds':['data'],'moduleId':'imu','tutorial':t,
    'notes':[scope],'nominalCableLengthMm':150,'lengthBoundary':copy.deepcopy(length),
    'assemblyOrder':{'powerDisconnected':True,'connectorBeforeClosure':True,'sequence':t['assemble']}})
  marker=port['pins'][index]['contactMouthProjectionWorldMm']
  newp={'id':cid,'segments':[], 'checkedHarnessRoute':{'partKeys':[],
   'meshKeys':['imu_exact_'+plug,'imu_exact_imu_'+net],
   'contextMeshKeys':['imu_exact_'+k for k in core]+['imu_exact_imu_'+other for other,_,_,_ in NETS if other!=net]+[p['key'] for p in s.get('checkedHarnessMeshes',[]) if p.get('nativePartKey') in ['power_support','torso_base']],
   'coverMeshKeys':['imu_exact_imu_cover'],'coverPartKeys':[],
   'endpoints':[{'id':cid+'-sh4','role':'from','label':'BNO085 CONN4 · '+label,'position':marker,'outwardAxis':port['outwardAxis']},
    {'id':cid+'-free','role':'to','label':'Open neck-root end · not plugged into Pi','position':length['freeBoundaryWorldMm'],'outwardAxis':None,'illustrativeOnly':True}],
   'manifestSha256':sha(manifest_path),'displayNote':'Local body-side route only. The free end is not connected to the Pi.',
   'legend':['Official BNO085 board registration','150 mm nominal cable; head extension remains separate'],
   'neutralOnly':True,'wholeHarnessAccepted':False}}
  newsp.append(newp)
 w['connections']+=new;s['connections']+=newsp
 byid={c['id']:c for c in w['connections']}
 for step in w['steps']:
  step['connections']=[copy.deepcopy(byid[c['id']]) for c in step.get('connections',[]) if c['id'] in byid]
  step['connectionIds']=[c['id'] for c in step['connections']]
  if step['id']=='imu':
   step['actions']=tutorials[2]['assemble']+tutorials[5]['assemble'];step['check']=' '.join(tutorials[5]['check'])
 for p in payload.values():
  p=copy.deepcopy(p);original=p['key'];p['key']='imu_exact_'+original;p['partKey']=original;p['nativePartKey']=original
  s.setdefault('checkedHarnessMeshes',[]).append(p)
 for op in operations:
  if op['id'] in ['imu-local-plug','imu-local-cover','imu-local-retain']:
   w.setdefault('assemblyCablePrerequisites',{})[op['id']]=[{'id':op['id']+'-leads','text':'SH4 must be connected before the rear cover is seated; the neck ends remain free.','connectionIds':[x[2] for x in NETS],'ports':['CONN4'],'motorIds':[]}]
 binding={'manifestFile':str(manifest_path),'manifestSha256':sha(manifest_path),
  'assemblyReceiptSha256':m['acceptance']['sha256'],'externalReceiptSha256':EXTERNAL_SHA256,'deltaReceiptHashes':DELTA_HASHES,
  'adapterSha256':sha(__file__),'replacementPartKeys':core,'newReceivingPartKeys':[plug],
  'sourceCoordinateRule':m['sourceCoordinateContract'],'physicalFitVerified':False,'wholeHarnessAccepted':False,
  'scope':scope,'currentPrintPackageModified':False}
 for obj in [d,w,s]:obj['imuWiringAdapter']=copy.deepcopy(binding)
 s['connectionCount']=len(s['connections']);s['segmentCount']=sum(len(x.get('segments',[])) for x in s['connections'])
 return d,w,s
