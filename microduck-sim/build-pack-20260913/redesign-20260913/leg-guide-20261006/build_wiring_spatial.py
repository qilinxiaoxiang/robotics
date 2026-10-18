#!/usr/bin/env python3
"""Read-only source mapping; write only the sibling 3D wiring illustration data.

Coordinates are mm in the existing trunk_base world frame. Actual mesh centres
are not asserted to be connector pin locations. Curves demonstrate electrical
connections; they are not flex-cable collision or assembled harness evidence.
"""
from pathlib import Path
import json, hashlib, math
G=Path(__file__).resolve().parent
R=G.parent
P=R.parent

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
W=read(G/'wiring-guide-data.json'); D=read(G/'full-build-data.json')
from current_wiring_overlay import load_overlay
overlay=load_overlay(D)
parts={p['key']:p for p in D['parts']}
parts.update({p['key']:p for p in overlay['currentParts']})
harness=read(R/'motor-harness-reach.json')
carrier=read(P/'assembly/service-mounts/design.json')
contract=read(R/'design-contract.json')
assert sha(Path(W['local_contract']))==W['local_contract_sha256']
assert len(W['nodes'])==38 and len(W['connections'])==51
nodes=[]; index={}

def add(id, label, keys, pos, evidence, kind='component', **extra):
    assert id not in index
    assert all(k in parts for k in keys)
    assert len(pos)==3 and all(math.isfinite(float(v)) for v in pos)
    n=dict(id=id,label=label,partKeys=keys,position=[float(v) for v in pos],
           anchorEvidence=evidence,kind=kind,connectorOrientationVerified=False,**extra)
    nodes.append(n);index[id]=n

actual={'regulator':'regulator','pi':'pi','openrb':'openrb','camera':'camera_board',
        'imu':'imu_board','amp':'amplifier','speaker':'speaker'}
actual.update({f'motor{i}':f'motor{i}' for i in range(1,16)})
labels={n['id']:n['label'] for n in W['nodes']}
for id,key in actual.items():
    p=parts[key]
    bounds=p['bounds']; center=[(bounds[0][a]+bounds[1][a])/2 for a in range(3)]
    assert max(abs(a-b)for a,b in zip(center,p['center']))<1e-6
    add(id,labels[id],[key],center,
        'Current display mesh bounding-box centre; component-level anchor, not a connector/pin. Exact per-wire contacts are supplied separately where source-backed.',
        geometryKind=p.get('geometryKind'),bounds=bounds,sourceReference=p.get('referenceMesh',key))

# External objects have no installed robot CAD. Their positions are layout choices.
for id,pos,size in [('charger',[-210,-90,65],[42,30,65]),('receiver',[-145,-90,35],[28,20,5]),
                    ('inputFuse',[-110,-90,-5],[24,5,5])]:
    add(id,labels[id],[],pos,'External schematic placement only; no installed robot pose or component dimensions verified.',
        kind='external-schematic',proxyDimensions=size,proxyDimensionsIllustrative=True)
add('xt30',labels['xt30'],['power_support'],[-61,0,-22],
    'Proposed tether entry near installed power support; connector mounting position and polarity orientation are not measured.',
    kind='proposed-installation',proxyDimensions=[12,10,8],proxyDimensionsIllustrative=True)
add('star','5 V positive star',['power_support'],[-48,-18,-40],
    'Proposed insulated positive junction beside converter, separate from the ground junction; not source CAD.',
    kind='proposed-junction')
add('ground-star','Common ground star',['power_support'],[-48,18,-40],
    'Proposed separate ground junction; all returns are unfused. Position is schematic, not source CAD.',
    kind='proposed-junction',auxiliary=True)
add('otg','SC0727 USB-A female',['pi'],[74,8.9,163],
    'Schematic OTG cable end outside Pi service opening; the cable endpoint and moulded connector pose are not measured.',
    kind='cable-end-schematic',auxiliary=True,proxyDimensions=[12,8,8],proxyDimensionsIllustrative=True)

# Slots are source-backed envelope centres, not connector contact coordinates.
# The reach checker explicitly assigns slot1 F0 and slots2..9 F1..F8.
slot_map={'F0':0,**{f'F{i}':i for i in range(1,9)},'F9':9,'F10':10}
for id,s in slot_map.items():
    f=carrier['fuses'][s]
    evidence=('Current fuse carrier design slot centre; F0/F1–F8 allocation is explicit in check_motor_harness_reach.py; no pin coordinates.'
              if s<9 else 'Remaining carrier slot centre, proposed F9/F10 allocation; installed slot identity and pin orientation require labels/physical confirmation.')
    add(id,labels[id],['fuse_carrier'],f['center_mm'],evidence,kind='fuse-envelope',
        physicalSlot=f['id'],slotAssignmentVerifiedInSource=s<9,proxyDimensions=f['envelope_mm'])
assert set(labels)<=set(index)

def pos(id):return list(index[id]['position'])
def segment(a,b,signal,fromPin=None,toPin=None,via=None,routeEvidence=None):
    points=[pos(a)]+(via or [])+[pos(b)]
    # Remove only consecutive identical positions, retaining nonzero local loops.
    cleaned=[]
    for q in points:
        q=[float(x)for x in q]
        if not cleaned or q!=cleaned[-1]:cleaned.append(q)
    return dict(from_=a,to=b,signal=signal,points=cleaned,fromPin=fromPin,toPin=toPin,
                routeEvidence=routeEvidence or 'Illustrative route between component anchors; not measured connector routing or a collision-checked cable.',
                actualConnectorCoordinates=False)

def seg(a,b,signal,**kw):
    s=segment(a,b,signal,**kw);s['from']=s.pop('from_');return s

connections=[]
for c in W['connections']:
    cid=c['id']; ss=[]
    if cid=='charger-usb':ss=[seg('charger','receiver','USB power negotiation')]
    elif cid=='input-fuse':ss=[seg('receiver','inputFuse','20 V',fromPin='+',toPin='fuse input'),seg('inputFuse','xt30','20 V',fromPin='fuse output',toPin='XT30 +')]
    elif cid=='input-return':ss=[seg('receiver','xt30','GND',fromPin='−',toPin='XT30 −',via=[[-95,-80,-25]])]
    elif cid=='regulator-input':ss=[seg('xt30','regulator',s,fromPin=f,toPin=t)for s,f,t in [('20 V','XT30 +','VIN+'),('GND','XT30 −','GND')]]
    elif cid=='star-output':ss=[seg('regulator','star','5 V',fromPin='5 V',toPin='positive star'),seg('regulator','ground-star','GND',fromPin='GND',toPin='ground star')]
    elif cid=='motor-main':
        ss=[seg('star','F0','5 V',toPin='10 A main input')]
        for i in range(1,9):
            # Two insulated trunks, four branch fuses per trunk; junction points
            # depict topology, not verified splice locations.
            via=[[-47,-12 if i<=4 else 12,-52]]
            ss.append(seg('F0',f'F{i}','5 V',fromPin='F0 output',toPin='3 A branch input',via=via,
                          routeEvidence='F0 output feeds two insulated trunks, four branches per trunk; joint coordinates are illustrative.'))
    elif cid in ['pi-fuse','audio-fuse']:
        ss=[seg('star','F9'if cid=='pi-fuse'else'F10','5 V',toPin='fuse input')]
    elif cid.startswith('motor-F'):
        group=next(g for g in harness['power_groups']if 'motor-'+g['fuse']==cid)
        ids=group['servo_ids']; anchor=group['trunk_route_anchor_mm']
        midpoint=[sum(pos(f'motor{i}')[a]for i in ids)/len(ids)for a in range(3)]
        shift=group['y_shift_toward_trunk_anchor_mm'];norm=math.dist(midpoint,anchor)
        split=[midpoint[a]+(anchor[a]-midpoint[a])*shift/norm for a in range(3)]
        for i in ids:
            ss.append(seg(group['fuse'],f'motor{i}','5 V',fromPin='fuse output',toPin='2 VDD',via=[anchor,split],
                routeEvidence='Source reach-screen torso anchor plus proposed supported Y near group case-centre midpoint; individual factory tail, no pin pose or cable collision claim.'))
            ss.append(seg('ground-star',f'motor{i}','GND',fromPin='unfused ground star',toPin='1 GND',via=[anchor,split],
                routeEvidence='Individual return via group route; common ground remains separate from positive joints. Waypoints are illustrative.'))
    elif cid.startswith('data-'):
        a,b=c['fromNodeIds'][0],c['toNodeIds'][0]
        via=[pos(f'motor{i}')for i in harness['ankle_bridge_routed_path_servo_centers'][1:-1]]if(a,b)==('motor1','motor6')else[]
        ss=[seg(a,b,'TTL DATA',fromPin='3 DATA',toPin='3 DATA',via=via,
            routeEvidence=('Source reach-screen route up right leg/across torso/down left leg via case centres; planned finished DATA lead400mm, no free ankle bridge. Coordinates are proxies, not pin locations.'if via else 'Source DATA chain order; illustrative link between case-centre proxies, no VDD conductor continuity.'))]
    elif cid=='openrb-ground':ss=[seg('openrb','ground-star','GND',fromPin='1 GND',toPin='unfused ground star',via=[[-20,0,35]])]
    elif cid.startswith('pi-5v-'):ss=[seg('F9','pi','5 V',fromPin='F9 output',toPin=cid.rsplit('-',1)[1],via=[[-20,-5,35],[45,-5,100]])]
    elif cid.startswith('pi-gnd-'):ss=[seg('ground-star','pi','GND',toPin=cid.rsplit('-',1)[1],via=[[-20,5,35],[45,5,100]])]
    elif cid=='pi-otg':ss=[seg('pi','otg','USB data + 5 V',fromPin='USB Micro-B',toPin='SC0727 USB-A female')]
    elif cid=='openrb-usb':ss=[seg('otg','openrb','USB data + 5 V',fromPin='USB-A female',toPin='USB-C')]
    elif cid.startswith('imu-'):
        p=c['pins'][0];ss=[seg('pi','imu',p['signal'],fromPin=p['from'],toPin=p['to'],via=[[30,0,55],[-40,0,32]])]
    elif cid=='camera-ribbon':ss=[seg('camera','pi','CSI data + power',fromPin='15-contact CSI',toPin='22-contact CSI',via=[[64,0,170]])]
    elif cid in ['audio-vin','audio-return']:
        ss=[seg('F10'if cid=='audio-vin'else'ground-star','amp','5 V'if cid=='audio-vin'else'GND',toPin='VIN'if cid=='audio-vin'else'GND',via=[[-20,-20,35],[20,-35,100]])]
    elif cid.startswith('audio-')and cid!='audio-gain':
        p=c['pins'][0];ss=[seg('pi','amp',p['signal'],fromPin=p['from'],toPin=p['to'],via=[[60,-38,145]])]
    elif cid=='audio-gain':
        q=pos('amp');ss=[seg('amp','amp','3 dB gain',fromPin='GAIN',toPin='VIN through100kΩ',via=[[q[0]-10,q[1]-12,q[2]+6],[q[0]+10,q[1]-12,q[2]+6]],routeEvidence='Local100kΩ GAIN-to-VIN resistor shown as a loop; solder-pad coordinates are schematic.')]
    elif cid=='speaker':ss=[seg('amp','speaker',p['signal'],fromPin=p['from'],toPin=p['to'],via=[[10,-8 if j==0 else-5,152]])for j,p in enumerate(c['pins'])]
    else:raise AssertionError('Unmapped connection '+cid)
    focus=sorted({k for s in ss for n in [s['from'],s['to']]for k in index[n]['partKeys']})
    if cid=='data-11':
        focus=sorted(set(focus)|{f'motor{i}'for i in harness['ankle_bridge_routed_path_servo_centers']})
    connections.append(dict(id=cid,segments=ss,focusPartKeys=focus,sourceConnectionId=cid,wire=c['wire'],
                            endpointPins=c['pins'],powered=False,physicalCableIdentificationConfirmed=False))

# Exact per-contact endpoints are distinct from component location labels.
# Unknown socket registration stays unverified; neither a centre nor a route
# tangent may manufacture a connector pose.
import re,copy
for c in connections:
    logical=next(x for x in W['connections'] if x['id']==c['id'])
    c.update({k:copy.deepcopy(logical[k]) for k in ['groupIds','tutorial','moduleId','lengthEvidence','assemblyOrder'] if k in logical})
    c['physicalCableIdentificationConfirmed']=logical.get('physical_cable_identification_confirmed',False)
    for s in c['segments']:
        for side in ['from','to']:
            nid=s[side];label=s.get(side+'Pin') or index[nid]['label'];key=index[nid]['partKeys'][0] if index[nid]['partKeys'] else None
            typ='screw-terminal' if nid in ['regulator','receiver','amp'] else 'solder' if nid in ['star','ground-star','xt30','speaker'] or nid.startswith('F') else 'jst-eh-3' if nid.startswith('motor') else 'jst-sh-4' if nid=='imu' else 'unknown'
            endpoint={'partKey':key,'connectorId':nid+':'+str(label),'connectorType':typ,'contactLabel':label,'pinNumber':None,'position':pos(nid),'outwardAxis':None,'upAxis':None,'poseVerified':False,'illustrativeOnly':True,'poseEvidence':'Electrical contact identity only; exact installed socket registration not established. This location labels the component, not a mateable socket.'}
            if nid.startswith('motor'):
                endpoint.update(connectorGeometry={'bodyMm':[9.5,3.8,6.5],'pinCount':3,'pitchMm':2.5,'geometryEvidence':'Official JST EHR-3 drawing; installed housing pose remains unregistered.'},pinMap={'1':'GND','2':'VDD','3':'DATA'},socketChoice='Either of the two parallel JST-EH ports; label incoming/outgoing before fitting. Never infer pin order from world left/right.')
            if nid=='pi' and c['id'] not in ['pi-otg','openrb-usb','camera-ribbon']:
                match=re.match(r'(\d+)',str(label))
                if match:
                    endpoint=copy.deepcopy(overlay['piEndpoints'][int(match.group(1))]);endpoint['contactLabel']=label
            elif c['id']=='camera-ribbon':endpoint['connectorType']='ffc-15' if nid=='camera' else 'ffc-22';endpoint['pinMap']={'function':'CSI data and camera power on this one ribbon'}
            elif c['id']=='pi-otg':endpoint['connectorType']='micro-usb' if nid=='pi' else 'usb-a'
            elif c['id']=='openrb-usb':endpoint['connectorType']='usb-c' if nid=='openrb' else 'usb-a'
            s[side+'Endpoint']=endpoint
            if endpoint['poseVerified']:s['points'][0 if side=='from' else -1]=endpoint['position']
        s['actualConnectorCoordinates']=all(s[k+'Endpoint']['poseVerified'] for k in ['from','to'])

assert [c['id']for c in connections]==[c['id']for c in W['connections']]
for c in connections:
    assert c['segments']
    for s in c['segments']:
        assert s['from']in index and s['to']in index
        assert s['points'][0]==s['fromEndpoint']['position'] and s['points'][-1]==s['toEndpoint']['position']
        assert len(s['points'])>=2 and all(len(q)==3 for q in s['points'])
# Independent graph invariants: isolated VDD chain and exact powered motor groups.
chain=['openrb']+[f'motor{i}'for i in harness['data_chain'][1:]]
assert [(c['segments'][0]['from'],c['segments'][0]['to'])for c in connections if c['id'].startswith('data-')]==list(zip(chain,chain[1:]))
assert all(s['signal']=='TTL DATA'for c in connections if c['id'].startswith('data-')for s in c['segments'])
main=next(c for c in connections if c['id']=='motor-main')['segments']
assert [(s['from'],s['to'])for s in main]==[('star','F0')]+[('F0',f'F{i}')for i in range(1,9)]
for g in harness['power_groups']:
    ss=next(c for c in connections if c['id']=='motor-'+g['fuse'])['segments']
    assert [(s['from'],s['to'],s['signal'])for s in ss]==[(a,f'motor{i}',signal)for i in g['servo_ids']for a,signal in[(g['fuse'],'5 V'),('ground-star','GND')]]
source_paths=[G/'wiring-guide-data.json',G/'full-build-data.json',R/'design-contract.json',R/'ASSEMBLY-WIRING.md',R/'motor-harness-reach.json',R/'check_motor_harness_reach.py',P/'assembly/service-mounts/design.json',Path(__file__)]
result=dict(schemaVersion=1,units='mm',coordinateFrame='existing full-build-data trunk_base world',
    nodes=nodes,auxiliaryNodeIds=['ground-star','otg'],baseNodeCount=38,connections=connections,
    connectionCount=len(connections),segmentCount=sum(len(c['segments'])for c in connections),
    sourceHashes={**{str(p):sha(p)for p in source_paths},**overlay['sourceHashes']},officialPinSources=W['sources'],
    currentParts=overlay['currentParts'],replacePartKeys=overlay['replacePartKeys'],sceneGeometrySource=overlay['sceneGeometrySource'],sceneGeometrySha256=overlay['sceneGeometrySha256'],
    electricalTopologyReviewStatus='Saved prior ledger; user has requested architecture review. No publication acceptance for eleven-fuse topology.',
    geometryPayloadIncluded=True,energizingPerformed=False,physicalRoutingVerified=False,
    actualConnectorOrientationsVerified=False,
    limitations=['Component anchors use the actual installed CAD mesh centres, not exact pins. No true connector pose is asserted.',
      'Logical connector/pin names are source-backed; separated detail-view contacts must be labeled schematic orientation.',
      'External charger/receiver/input fuse and unmodeled junctions use diagram placements; proxy box dimensions are illustrative unless identified as a carrier envelope.',
      'F0 slot1 and F1–F8 slots2–9 are assigned in the source reach checker. F9/F10 use proposed remaining slots10/11; confirm physical labels.',
      'Routes convey order, branch sharing and intended region; CAD cable collision, bend radius, soldering, slack and real cable identities remain unverified.',
      'Only the1→6 DATA path is constrained to the documented torso tour. All motor power tails return individually; no VDD continuity through the DATA chain.',
      'No cable fitting, power test or physical commissioning was performed.'],
    assertionsPassed=['38 original nodes mapped','51 original connection IDs in exact order','F0 is series predecessor of F1–F8','Unfused ground star is a separate node','15 DATA links contain only DATA','15 motors receive exactly their assigned fused VDD and star ground','USB Pi→OTG→OpenRB is two distinct segments','Per-wire Pi contacts bind current discrete-header pose; other unregistered sockets are explicitly unverified','Installed centres equal current display geometry bounds; old head overlay is replaced only in wiring mode'])
(G/'wiring-spatial-data.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k]for k in ['baseNodeCount','connectionCount','segmentCount','assertionsPassed']},ensure_ascii=False))
