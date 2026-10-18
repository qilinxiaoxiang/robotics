"""Connector-first prototype guide: real plug positions and access order, no prescribed soft-wire shape."""
from pathlib import Path
import json,hashlib,struct,base64,copy,array,sys
G=Path(__file__).resolve().parent
J=G.parent/'workflow-review-20261009/enclosed-wiring-repair/motor-wires/shared-port-repair'
P=J.parent/'slack-packaging'
M=P/'mixed-leg-manifest.json'
SNAP=G/'wiring-current-sources/regional-before-20261009'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def packed_mesh(p):
 data=Path(p['file']).read_bytes();assert hashlib.sha256(data).hexdigest()==p['sha256'];n=struct.unpack_from('<I',data,80)[0];assert len(data)==84+50*n,('not binary STL',p['file'])
 vertices=bytearray();indices=array.array('I');seen={}
 for off in range(84,len(data),50):
  for i in range(3):
   v=data[off+12+12*i:off+24+12*i]
   if v not in seen:seen[v]=len(seen);vertices.extend(v)
   indices.append(seen[v])
 if sys.byteorder!='little':indices.byteswap()
 return {**{k:p[k] for k in ['key','kind','color','sha256','expectedFinalBoundsMm'] if k in p},'sourceFile':p['file'],**({'color':'#383c3f','sourceColor':p.get('color'),'displayStyle':'black flexible motor cable'} if p.get('kind') in ['wire','bundle-illustration'] else {}),'positionB64':base64.b64encode(vertices).decode(),'indexB64':base64.b64encode(indices.tobytes()).decode(),'triangleCount':n,'vertexCount':len(seen),'exactSourceTriangleCoordinates':True}
def instructions(a,b,side,length):
 mid=a in [3,8];ankle=a in[2,7];knee=a in[4,9]
 if ankle:
  deadline=f'Before fitting the thigh motors, plug the upper end into motor {a}. Plug the ankle end into motor {b} before closing its fork.'
  route='Guide the cable along the existing thigh opening and around the lower lip to the ankle. Keep its three conductors together as a loose bundle; arrange only the available slack against the leg. Leave a loose bend at the joint; do not tie together parts that move relative to each other.'
 elif mid:
  deadline=f'Before fitting the thigh motors, plug both ends into motors {a} and {b} while both are outside the thigh. Both sockets on each motor must be prepared before seating either motor.'
  route='Route the upper end across the existing rear-frame opening, then inward. Keep the three conductors together, clear of the adjacent knee and ankle plugs. Adjust the available slack naturally along the leg without pulling on either plug.'
 elif knee:
  deadline=f'Before fitting the thigh motors, plug the thigh end into motor {b}. Connect motor {a} on the open hip bench, before its cover and link fasteners close access.'
  route='Use the short 100 mm cable. Pass the thigh end downward before turning sideways, and arrange the small spare loop against the thigh. Retain it on the same upper-leg body, away from the output shaft.'
 else:
  deadline=f'Connect motors {a} and {b} on the open hip bench, before the hip cover is installed. The closed torso cover blocks the straight approach to motor {a}.'
  route='Lead the cable off the socket axis, around the existing edge corridor, then arrange the 180 mm spare loop. Keep it off the converter and rotating output; leave a loose bend so the joint can move.'
 return {'prepare':[f'Disconnect power. Prepare one ROBOTIS X3P {length} mm three-conductor cable; identify both keyed JST-EH plugs and the motor labels.',deadline,'If this joint is already closed, reopen only the relevant motor/fork retention to expose the socket. Do not force a connector through a closed cover.'], 'assemble':[deadline,'Hold the plug housing, align its key with the highlighted socket, and push straight until fully seated. Either motor socket carries the same bus; keep the cable pin order unchanged.',route,'Feed the flexible cable by hand while seating the preconnected motors. Arrange the remaining soft wire by hand through the existing opening, leaving slack at the joint.'], 'check':['Both connector housings are fully seated. Inspect the frame lip, shaft, screw paths and cover seam before tightening the corresponding closure.', 'Adjust and loosely retain spare cable on the moving side. Move the unpowered joint gently: no pull at the socket, rubbing, pinching or taut loop.', f'The cable length class is {length} mm. Lay spare wire along the same leg, away from the moving output and cover seam. Check the real jacket, connector seating and freedom of movement.']}
def main():
 bench=read(P/'bench-port-insertion.json');assert bench['passed'] and bench['sourceManifestSha256']==sha(M)
 manifest=read(M)
 assert read(manifest['verificationFile'])['passed'];top=read(J.parent/'active-topology.json');gate=read(J/'eight-leg-handoff-check.json');assert gate['passed'];assert read(J/'four-preplugged-delta.json')['passed'];assert read(J/'current-lower-revision-delta.json')['passed']
 for p,h in manifest['sourceHashes'].items():assert sha(p)==h,('stale manifest source',p)
 assert sha(manifest['centerlineInput'])==manifest['centerlineSha256']
 SNAP.mkdir(parents=True,exist_ok=True)
 for name in ['wiring-guide-data.json','wiring-spatial-data.json']:
  if not (SNAP/name).exists():
   assert not read(G/name).get('regionalLegAdapter');(SNAP/name).write_bytes((G/name).read_bytes())
 wiring=read(SNAP/'wiring-guide-data.json');spatial=read(SNAP/'wiring-spatial-data.json');base=read(G/'full-build-data.json')
 pairs={frozenset([r['fromPort'].split('-')[1],r['toPort'].split('-')[1]])for r in manifest['routes']};pairs.add(frozenset(['1','6']))
 def motorpair(c):
  aa=[x[5:]for x in c.get('fromNodeIds',[])if x.startswith('motor')];bb=[x[5:]for x in c.get('toNodeIds',[])if x.startswith('motor')]
  return frozenset(aa+bb) if len(aa)==len(bb)==1 else frozenset()
 removed={c['id']for c in wiring['connections']if c['id'].startswith('data-')and motorpair(c)in pairs};assert len(removed)==9
 wiring['connections']=[c for c in wiring['connections']if c['id']not in removed]
 for s in wiring['steps']:s['connections']=[c for c in s['connections']if c['id']not in removed]
 spatial['connections']=[c for c in spatial['connections']if c['id']not in removed]
 for g in wiring['groups']:g['connectionIds']=[x for x in g['connectionIds']if x not in removed]
 titles={'left-leg':'Left leg','right-leg':'Right leg','head':'Head','torso-power':'Torso and power','data':'Data and sensors'}
 for g in wiring['groups']:g['title']=titles.get(g['id'],g['id'])
 entries=[];newsp=[];payloads=[]
 for side,order in [('left',[10,9,8,7]),('right',[5,4,3,2])]:
  module=side+'-leg';keys=next(m['partKeys']for m in base['modules']if m['id']==module);group=next(g for g in wiring['groups']if g['id']==module)
  # Preserve legacy separate power rows in their explicit whole-machine entry, never the local leg route.
  displaced=group['connectionIds'];power=next(g for g in wiring['groups']if g['id']=='torso-power');power['connectionIds']+= [x for x in displaced if x not in power['connectionIds']]
  group['connectionIds']=[f'ttl-{a:02d}-{a-1:02d}'for a in order];group['description']=f'Four local cables, motor {order[0]} to {order[-1]-1}. Preconnect blocked sockets before closing the thigh or ankle. Trunk entry is a separate installation.'
  for a in order:
   b=a-1;rid=f'ttl-{a:02d}-{b:02d}';r=next(r for r in manifest['routes']if r['id']==rid);ports=[top['ports'][r[x]]for x in ['fromPort','toPort']];parts=[p for p in manifest['parts']if p['routeId']==rid];assert len(parts)==5
   parts=[p for p in parts if p['key'] in [r['fromPort'],r['toPort']]];assert len(parts)==2
   length=r['nominalCableLengthMm'];tutorial=instructions(a,b,side,length)
   c={'id':rid,'from':f'XL330 ID {a} · 3-pin TTL socket','to':f'XL330 ID {b} · 3-pin TTL socket','fromNodeIds':[r['fromPort']],'toNodeIds':[r['toPort']],'purpose':f'Motor {a} → {b} · one {length} mm cable','wire':f'1 × ROBOTIS X3P {length} mm cable; two keyed JST-EH plugs','nominalCableLengthMm':length,'voltage':'Unpowered mechanical routing review','pins':[],'notes':['The two servo sockets are parallel. Their CAD identifiers do not change pin order.','Follow the preparation step before fitting covers. Route the flexible cable through the existing opening and check joint movement before tightening.'], 'moduleId':module,'groupIds':[module],'tutorial':tutorial,'assemblyOrder':{'connectorBeforeClosure':True,'powerDisconnected':True,'sequence':tutorial['assemble']},'checkedLegRoute':True,'sourceManifestSha256':sha(M)}
   entries.append(c);nodeids=[]
   for name,p in zip([r['fromPort'],r['toPort']],ports):
    nodeids.append(name)
    if not any(n['id']==name for n in spatial['nodes']):spatial['nodes'].append({'id':name,'label':f'ID {p["motor"]} · 3-pin TTL socket','partKeys':[f'motor{p["motor"]}'],'position':p['mouth'],'kind':'registered-servo-port','anchorEvidence':'Official X330 STEP port registration; not a motor bounding-box centre.','outwardAxis':p['outward']})
   packed=[packed_mesh(p)for p in parts];payloads+=packed
   newsp.append({'id':rid,'focusPartKeys':keys,'segments':[],'checkedLegRoute':{'moduleId':module,'partKeys':keys,'meshKeys':[p['key']for p in packed],'retentionMeshKeys':[],'nominalCableLengthMm':length,'portIds':nodeids,'ports':ports,'benchInsertion':[{'port':v['port'],'axis':v['outwardAxisWorld'],'approachMm':v['prepareAtMm'],'housingSha256':v['sourceHousingSha256']} for v in bench['ports'] if v['port'] in nodeids],'benchCheckSha256':sha(P/'bench-port-insertion.json'),'neutralOnly':True,'wholeHarnessAccepted':False,'manifestSha256':sha(M),'softCableShapeSpecified':False,'channelInstruction':tutorial['assemble'][2],'basePlugsManifestSha256':sha(M),'installationDependencyFile':manifest['operationDependencies'],'representation':'connector-and-channel','routeArrangement':tutorial['assemble'][2]},'actualConnectorCoordinates':True})
 wiring['connections']+=entries;stage=next(s for s in wiring['steps']if s['id']=='motor-data');stage['connections']+=entries
 spatial['connections']+=newsp;spatial['checkedLegMeshes']=payloads;spatial['checkedLegRetentionMeshes']=[];spatial['geometryPayloadIncluded']=True
 # The assembly page consumes the same closure deadlines as the wiring page.
 # Keep historical mesh/fastener source data unchanged; this is an operation overlay.
 wiring['assemblyCablePrerequisites']={}
 for module in base['modules']:
  for op in module['operations']:
   requirements=[]
   for dependency in read(manifest['operationDependencies'])['dependencies']:
    if not (op['id'] in dependency.get('before',[])+dependency.get('during',[]) or dependency.get('beforePart') in op.get('add',[])):continue
    ports=[p for p in dependency.get('ports',[]) if 'motor'+p.split('-')[1] in (op.get('add',[]) if dependency.get('during') else module['partKeys'])]
    if dependency.get('ports') and not ports:continue
    cables=[c for c in entries if (any(p in c['fromNodeIds']+c['toNodeIds'] for p in ports) if ports else c['moduleId']==module['id'])]
    requirements.append({'id':dependency['id'],'text':dependency['requires'],'ports':ports,'motorIds':sorted({int(p.split('-')[1]) for p in ports}),'connectionIds':[c['id'] for c in cables]})
   if requirements:wiring['assemblyCablePrerequisites'][op['id']]=requirements

 retentionWithdrawal={'status':'withdrawn','keys':[p['key'] for p in manifest['retentionContexts']],'reason':'Assistant-designed rectangular receiving loops are not actual installed ties or original printed parts. Their prescribed geometry and routing requirement are withdrawn, not accepted by hiding them.','replacementPrintedParts':[],'replacementRetentionDesignAccepted':False,'sourceEvidenceRetained':str(M),'conductorModelScope':'Preserved neutral clearance reference only; not a rigid routing template or flexible-motion proof.'}
 wiring['withdrawnLegRetentionDesign']=retentionWithdrawal;spatial['withdrawnLegRetentionDesign']=retentionWithdrawal
 binding={'manifestSha256':sha(M),'softCableShapeSpecified':False,'sourceHashes':{**manifest['sourceHashes'],**{str(p):sha(p)for p in [M,P/'bench-port-insertion.json',Path(__file__),J/'four-preplugged-delta.json',J/'current-lower-revision-delta.json']}},'removedLegacyConnectionIds':sorted(removed),'acceptedDisplay':'User-authorized prototype scope, 2026-10-09: exact keyed plug locations and insertion, physical access sequence and existing-opening route instructions. Soft-wire geometry and artificial retention frames withdrawn; no physical-motion claim.','wireDisplayStyle':{'color':'#383c3f','scope':'Display only; source mesh bytes and original material metadata retained.'},'unrelatedElectricalTopologyChanged':False,'physicalCommissioningVerified':False}
 wiring['regionalLegAdapter']=binding;spatial['regionalLegAdapter']=binding;spatial['connectionCount']=len(spatial['connections']);spatial['segmentCount']=sum(len(c.get('segments',[]))for c in spatial['connections'])
 for name,data in [('wiring-guide-data.json',wiring),('wiring-spatial-data.json',spatial)]: (G/name).write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False))
 (G/'regional-leg-wiring-adapter-report.json').write_text(json.dumps({'passed':True,'connections':len(entries),'representation':'connector-and-channel','softWireMeshesIncluded':False,'exactMeshes':len(payloads),'sourceBinding':binding,'outputs':{n:sha(G/n)for n in ['wiring-guide-data.json','wiring-spatial-data.json']}},indent=2))
 print('8 connections / 16 keyed plugs / access order and channel instructions; no artificial frames or prescribed soft-wire solids.')
if __name__=='__main__':main()
