"""Current print-and-fit head overlay; display triangles, not a geometry acceptance gate.

Run after the body/IMU/input overlays. Source assemblies remain immutable. Every
new approach is a static bench instruction until an insertion path is established.
"""
from pathlib import Path
import base64, copy, struct
from build_body_wiring_adapter import read, sha, verify_file, packed_mesh

G = Path(__file__).resolve().parent
R = G.parent
P = R / 'printing/15-COMPLETE-INCREMENTAL-20261009'
F = R / 'workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009'
ADOPTION = F / 'prototype-adoption/prototype-adoption.json'
HEAD_MODULES = {'head', 'camera', 'electronics', 'head-close'}
IDENTITY = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
BLOCK = 'Work with this subassembly open on the bench. The view shows where the parts seat; fit them gently before tightening screws.'
USB = 'Keep the cap open until a Pi Micro-B-host to OpenRB USB-C-device cable with suitable rigid ends has been fitted. The existing 4472 straight C plug conflicts with this closed-shell layout; a replacement cable has not been selected. Do not force the cap or cut a new opening.'

def check_ref(ref):
    verify_file(ref['file'], ref['sha256'])
    return ref

def display_part(ref, key, name, module, color):
    check_ref(ref)
    p = packed_mesh(dict(ref, key=key, color=color))
    t = ref.get('worldTransform', IDENTITY)
    raw = base64.b64decode(p['positionB64']); buf = bytearray()
    bounds = [[float('inf')]*3, [float('-inf')]*3]
    for v in struct.iter_unpack('<3f', raw):
        q = [sum(t[i][j]*v[j] for j in range(3))+t[i][3] for i in range(3)]
        buf.extend(struct.pack('<3f', *q))
        for i in range(3):
            bounds[0][i]=min(bounds[0][i],q[i]); bounds[1][i]=max(bounds[1][i],q[i])
    p.update(positionB64=base64.b64encode(buf).decode(), bounds=bounds,
             center=[(a+b)/2 for a,b in zip(*bounds)], dimensions=[b-a for a,b in zip(*bounds)],
             name=name, description=name, aliases=name, moduleId=module, body='jaw_soft',
             stage=0,index=0,colorName='Current head',partKind='assembly',
             triangles=p['triangleCount'],geometryKind='source-mesh-display',
             sourceTransformWorld=t,approachVector=[0,0,0],expectedFinalBoundsMm=bounds,
             coordinateRule='Declared source mesh and rigid world transform; display only.')
    return p

def load_current_parts():
    adoption=read(ADOPTION); check_ref(adoption['baselineManifest'])
    package=read(adoption['baselineManifest']['file'])
    yw=read(P/'yellow-white-inventory.json'); black=read(P/'black-inventory.json')
    source_refs=[ADOPTION,Path(adoption['baselineManifest']['file']),P/'yellow-white-inventory.json',P/'black-inventory.json']
    refs={}; names={}; modules={}; colors={}
    def add(key,ref,name,module,color):
        refs[key]=ref; names[key]=name; modules[key]=module; colors[key]=color
    rows={x['key']:x for x in package['parts']}
    for key in ['jaw_support','jaw_frame','lower_pad','upper_pad','camera_board','eye_trim','camera_retainer']:
        mod='head' if key in ['jaw_support','jaw_frame','lower_pad'] else 'head-close' if key=='upper_pad' else 'camera'
        add(key,rows['REFERENCE fixed head '+key],key.replace('_',' ').title(),mod,'#292b30' if key in ['jaw_support','eye_trim','camera_retainer'] else '#e79b3c' if key in ['jaw_frame','lower_pad','upper_pad'] else '#3d7268')
    for row in yw['parts']:
        add(row['key'],{'file':row['path'],'sha256':row['sha256']},'Lower head shell' if row['key']=='head_bottom' else 'Eye-camera face panel','head' if row['key']=='head_bottom' else 'camera','#edc447' if row['key']=='head_bottom' else '#e9e7df')
    for asset in adoption['printAssets']:
        ref=asset.get('combinedWorldFile') or asset['worldMesh']
        add(asset['key'],ref,asset['key'].replace('_',' ').title(),'electronics','#e99436')
    # Use the same world meshes whose print counterparts were reconciled to stock.
    for key in ['eye_trim','camera_retainer','mouth_sliding_ring']:
        row=next(x for x in black['parts'] if x['key']==key)
        # Locate the explicit worldSource record without treating print coordinates as world.
        def find_world(v):
            if isinstance(v,dict):
                if 'worldSource' in v:return {'file':v['worldSource'],'sha256':v['worldSourceSha256']}
                for child in v.values():
                    z=find_world(child)
                    if z:return z
            if isinstance(v,list):
                for child in v:
                    z=find_world(child)
                    if z:return z
        ref=find_world(row)
        if ref is None: raise ValueError('Missing world source: '+key)
        add(key,ref,key.replace('_',' ').title(),'head' if key=='mouth_sliding_ring' else 'camera','#292b30')
    add('speaker',rows['REFERENCE current speaker'],'8 ohm speaker','electronics','#55585e')
    add('amplifier',adoption['amplifierPoseRequired']['replacementMesh'],'MAX98357A amplifier','electronics','#30645a')
    # Real whole-board display mesh, not the 142 conservative collision hulls.
    board=R/'head-redesign-20261008/curved-head/openrb-curved-layout-world.stl'
    controller=next(x for x in package['parts'] if x['group']=='controller')
    add('openrb',{'file':str(board),'sha256':sha(board),'worldTransform':controller['worldTransform']},'OpenRB-150','electronics','#367363')
    for row in package['parts']:
        if row['group']=='pi':
            short=row['key'].removeprefix('REFERENCE Pi current ')
            key='pi' if short=='pi' else 'head_pi_'+short
            name='Pi Zero W' if short=='pi' else 'Pi '+short.replace('_',' ')
            add(key,row,name,'electronics','#3d7268' if short=='pi' else '#b7b7b5' if 'pin_' in short or 'solder' in short else '#30333a')
        elif row['key'].startswith('REFERENCE fixed head camera_clamp_screw_'):
            key=row['key'].removeprefix('REFERENCE fixed head ')
            add(key,row,'Camera clamp screw '+key[-1],'camera','#b5b5b5')
        elif row['group']=='speaker_hardware':
            add(row['key'],row,'Speaker mounting screw','electronics','#b5b5b5')
    parts=[display_part(ref,key,names[key],modules[key],colors[key]) for key,ref in refs.items()]
    sources={str(p):sha(p) for p in source_refs}
    sources.update({r['file']:r['sha256'] for r in refs.values()})
    return parts,adoption,sources

def operation(id,title,add,visible,text,fasteners=None):
    return dict(id=id,kind='inspect',title=title,add=add,screwIds=[],highlightKeys=add,
                text=text,isolatedPartKeys=visible,visiblePartKeys=visible,
                animationBlockedReason=BLOCK,retentionNotes=[fasteners] if fasteners else [],
                tutorial={'prepare':['Keep all electronics unpowered. Work with this subassembly detached and accessible.'],
                          'assemble':[text]+([fasteners] if fasteners else []),
                          'check':['Check seating and access by hand before proceeding. Do not use screws to pull an obstructed part into place.']})

def moved_head_connection_ids(wiring, spatial):
    """Find actual incident endpoints, not incidental context/focus parts.

    A checked body-only harness may mention Pi as its eventual destination in
    prose, but its open neck boundary must remain an unchanged local route.
    """
    moved={'pi','openrb','amplifier','amp','speaker','camera','camera_board'}
    nodes={n['id'] for n in spatial.get('nodes',[]) if set(n.get('partKeys',[])) & moved}
    nodes |= moved
    def endpoint(e):
        return isinstance(e,dict) and (e.get('partKey') in moved or e.get('nodeId') in nodes)
    result=set()
    logical=[wiring.get('connections',[])]+[s.get('connections',[]) for s in wiring.get('steps',[])] if wiring else []
    for collection in logical:
        for c in collection:
            if set(c.get('fromNodeIds',[])+c.get('toNodeIds',[])) & nodes or endpoint(c.get('fromEndpoint')) or endpoint(c.get('toEndpoint')):
                result.add(c['id'])
    for c in spatial.get('connections',[]):
        for segment in c.get('segments',[]):
            if segment.get('from') in nodes or segment.get('to') in nodes or endpoint(segment.get('fromEndpoint')) or endpoint(segment.get('toEndpoint')):
                result.add(c['id'])
    return result

def add_head_power_instructions(data, wiring, spatial):
    """Logical destinations only: preserve the checked body routes to the neck."""
    source=R/'workflow-review-20261009/enclosed-wiring-repair/power-sensor/integrated-harness-20261009/integrated-harness.json'
    harness=read(source)
    if harness['openrbPower']['jumper']!='VIN(DXL), JP1 terminal position':
        raise ValueError('Head power tutorial needs review after jumper topology change')
    metadata=data['headPrototypeRevision']
    metadata['sourceHashes'][str(source)]=sha(source)
    metadata['headPowerInstructions']={
      'source':str(source),'sourceSha256':sha(source),
      'scope':'Logical destinations and assembly order; no head route, connector SKU or completed power-up claimed.',
      'laterAdoptedGroundDecision':'Amplifier VIN uses HEAD5V. The existing Pi physical pin 20 lead provides amplifier GND; do not add the earlier duplicate distribution-to-amplifier return.',
      'supersededSourceSentence':'Give MAX98357A VIN/GND a separate paired branch.',
      'headDistributionTerminationSelected':False,'physicalCommissioningPassed':False}
    rows=[
      ('head-pi-supply','Supply Pi through its GPIO power pins','Head 5 V and ground distribution','Pi physical pins 2 / 4 and 6 / 14',
       [{'from':'5 V','to':'physical 2','signal':'+5V'},{'from':'5 V','to':'physical 4','signal':'+5V'},{'from':'GND','to':'physical 6','signal':'GND'},{'from':'GND','to':'physical 14','signal':'GND'}],
       'Two 22 AWG 5 V leads and two matched 22 AWG ground leads', ['head-5v','head-ground'],['pi'],
       ['Connect head 5 V to physical pins 2 and 4. Connect the matching returns to physical pins 6 and 14; these are physical header numbers, not BCM GPIO numbers.',
        'Keep the Pi PWR IN USB socket empty. Connect these leads while the board and header remain accessible, before fitting the face.']),
      ('head-openrb-supply','Supply OpenRB at J4','Head 5 V and ground distribution','OpenRB J4 VIN+ / GND',
       [{'from':'5 V','to':'J4 VIN+','signal':'+5V'},{'from':'GND','to':'J4 GND','signal':'GND'}],
       'A dedicated paired 5 V / ground branch', ['head-5v','head-ground'],['openrb'],
       ['Connect regulated head 5 V to J4 VIN+ and the matching return to J4 GND. Identify polarity from the board markings.',
        'With all power disconnected, set JP1 to VIN(DXL), the terminal-power position, before connecting Pi-to-OpenRB USB. Keep USB intact; do not cut VBUS.',
        'Do not power Pi from the OpenRB accessory pin. The separately powered motor zones do not take their motor VDD through the OpenRB DXL ports.']),
      ('head-amplifier-vin','Supply the amplifier VIN','Head 5 V distribution','MAX98357A VIN',
       [{'from':'5 V','to':'VIN','signal':'+5V'}],
       'Head-local insulated 5 V branch; final length and termination fitted on the open bench', ['head-5v'],['amp'],
       ['Connect head 5 V to MAX98357A VIN. Its ground return is the Pi physical pin 20 to amplifier GND lead shown under audio; do not add a duplicate ground branch.',
        'Keep the speaker pair on amplifier speaker + and − only. Neither speaker terminal connects to ground.'])
    ]
    connections=[]
    for id,purpose,fr,to,pins,wire,fn,tn,assemble in rows:
        c={'id':id,'purpose':purpose,'from':fr,'to':to,'pins':pins,'wire':wire,'voltage':'5 V DC / common ground',
           'fromNodeIds':fn,'toNodeIds':tn,'groupIds':['head'],'moduleId':'electronics','prototypeFitPending':True,
           'physical_cable_identification_confirmed':False,'notes':['No finished distribution connector or contact SKU is selected here. Make and insulate the chosen joints with the head open; allow slack through the neck.'],
           'tutorial':{'prepare':['Disconnect the charger and USB before making or changing these connections. Identify 5 V and ground at the neck-trunk ends.'],
                       'assemble':assemble,'check':['Verify continuity, polarity and insulation with power disconnected. No 20 V lead connects to Pi, OpenRB, the amplifier or the camera. Check the actual wire exits before closing the cap.']},
           'assemblyOrder':{'powerDisconnected':True,'connectorBeforeClosure':True,'sequence':assemble}}
        connections.append(c)
    retired={'pi-gnd-6','pi-gnd-14','audio-return'}
    additions={c['id'] for c in connections}
    wiring['connections']=[c for c in wiring.get('connections',[]) if c['id'] not in retired|additions]+copy.deepcopy(connections)
    for step in wiring['steps']:
        step['connections']=[c for c in step.get('connections',[]) if c['id'] not in retired|additions]
        if 'connectionIds' in step:step['connectionIds']=[x for x in step['connectionIds'] if x not in retired|additions]
        if step['id']=='pi-usb':
            step['title']='Connect internal Pi-to-OpenRB USB'
            step['actions']=['First complete the head power connections: Pi pins 2/4 and 6/14, OpenRB J4, and amplifier VIN with its Pi20 return.',USB]
    wiring['steps']=[step for step in wiring['steps'] if step['id']!='head-power-current']
    wiring['steps'].append({'id':'head-power-current','title':'Connect head power before closing','actions':[a for c in connections for a in c['tutorial']['assemble']],
                           'connections':copy.deepcopy(connections),'connectionIds':[c['id'] for c in connections],
                           'check':'Check the regulated 5 V polarity and all insulation before a separate powered test.','powered':False})
    for group in wiring.get('groups',[]):
        group['connectionIds']=[x for x in group.get('connectionIds',[]) if x not in retired|additions]
        if group['id']=='head':group['connectionIds']=[c['id'] for c in connections]+group['connectionIds']
    for collection in [wiring['connections']]+[step['connections'] for step in wiring['steps']]:
        for c in collection:
            if c['id']=='audio-20':
                c.update(purpose='Amplifier ground return',wire='Pi physical pin 20 to amplifier GND · head-local insulated return')
                c['tutorial']['assemble']=['Connect Pi physical pin 20 to MAX98357A GND. This is the amplifier return; do not add the retired second return from the distribution joint.']
                c['notes']=['The common ground comes through the Pi ground connections to the head return. Speaker + and − remain isolated from ground.']
    node_ids={n['id'] for n in wiring.get('nodes',[])}
    for id,label in [('head-5v','Head 5 V distribution'),('head-ground','Head common-ground distribution')]:
        if id not in node_ids:wiring['nodes'].append({'id':id,'label':label,'kind':'logical-distribution','physicalTerminationSelected':False})
    spatial['connections']=[c for c in spatial.get('connections',[]) if c['id'] not in retired|additions]
    for c in connections:
        spatial['connections'].append({'id':c['id'],'segments':[],'endpoints':[],
            'focusPartKeys':['pi'] if c['id']=='head-pi-supply' else ['openrb'] if c['id']=='head-openrb-supply' else ['amplifier'],
            'prototypeFitPending':True,'geometryStatus':'Named electrical endpoints; physical head routing and termination remain fit-to-install.'})
    metadata['logicalHeadPowerConnectionIds']=[c['id'] for c in connections]
    for module in data['modules']:
        if module['id']=='electronics':
            for op in module['operations']:
                if op['id']=='electronics-current-04':
                    op['tutorial']['assemble'].insert(0,rows[1][-1][0]+' '+rows[1][-1][1])
                if op['id']=='electronics-current-05':
                    op['tutorial']['assemble'].insert(0,rows[0][-1][0]+' Keep Pi PWR IN empty.')

def apply_head_prototype_adapter(data,wiring,spatial):
    data=copy.deepcopy(data); wiring=copy.deepcopy(wiring); spatial=copy.deepcopy(spatial)
    parts,adoption,sources=load_current_parts(); newkeys={p['key'] for p in parts}
    oldmods=[m for m in data['modules'] if m['id'] in HEAD_MODULES]
    oldowned={k for m in oldmods for k in m.get('ownedPartKeys',[])}
    oldscrews={s for m in oldmods for o in m['operations'] for s in o.get('screwIds',[])}
    # Original jaw motor remains. Old screw coordinates for superseded board/camera
    # mounts are removed; current fastener quantities are stated at their bench steps.
    retired=oldowned-newkeys-{'motor15'}
    data['parts']=[p for p in data['parts'] if p['key'] not in retired|newkeys]+parts
    data['screws']=[s for s in data['screws'] if s['id'] not in oldscrews]
    jaw=['jaw_support','jaw_frame','lower_pad','mouth_sliding_ring','motor15']
    camera=['face_panel','eye_trim','camera_board','camera_retainer']+[f'camera_clamp_screw_{i}' for i in range(1,4)]
    electronic=[p['key'] for p in parts if p['moduleId']=='electronics']
    pi=[k for k in electronic if k=='pi' or k.startswith('head_pi_')]
    cap=['head_cap']; audio=cap+['speaker_keeper','speaker','speaker_cradle','speaker_mount_screw_1','speaker_mount_screw_2','amplifier']
    full=jaw+['head_bottom','upper_pad']+camera+electronic+['head_roll_ring_a','head_roll_ring_b','head_yaw_link','motor14']
    ops={
      'head':[
        operation('head-current-01','Prepare the original jaw and separate bearing ring',jaw[:-1],jaw[:-1],'Use the original open support and the separate mouth sliding ring. Check the ring rotates freely in its seat; no split cheek or closed replacement bushing is used.'),
        operation('head-current-02','Fit ID 15 while the jaw is loose',['motor15'],jaw,'Fit the motor and jaw together on the open bench. Keep the passive ring in its seat and the output screw faces accessible.','Source jaw output: 2 × M2 × 6 TAP and 2 × M2 × 7 TAP. Preserve their original seats; do not substitute machine screws.'),
        operation('head-current-03','Connect ID 15 before fitting the lower shell',[],jaw,'Insert the keyed motor lead with the socket visible. Leave ordinary flexible slack clear of the rotating jaw and of the lower-shell screw seats.'),
        operation('head-current-04','Fit the current yellow lower shell',['head_bottom'],jaw+['head_bottom','motor14','head_roll_ring_a','head_roll_ring_b'],'Fit the revised lower shell with its local ID 14 plug clearance. Keep the motor lead inside the intended opening. Seat the supports before tightening their four existing frame screws. Check jaw motion without torque.','4 × M2.5 × 6 TAP for the support frame.')],
      'camera':[
        operation('camera-current-01','Prepare the face and eye trim',['face_panel','eye_trim'],['face_panel','eye_trim'],'Use the current white face without Pi pillars and the black eye trim. The camera is inside the eye; no rooftop foot or tilt hinge is installed.'),
        operation('camera-current-02','Connect the camera ribbon on the open bench',['camera_board'],camera[:3],'Open the camera CSI latch, insert the orange Standard–Mini 200 mm ribbon in the connector orientation, then close the latch. Hold the reinforced end; do not fold at the stiffener or pull the lens.'),
        operation('camera-current-03','Retain the eye camera',['camera_retainer']+camera[4:],camera,'Seat the board in the matching three-anchor retainer, keeping the lens inside the eye. Tighten the three existing clamp screws evenly. Leave the ribbon free at the rear; do not trap it between the face and clamp.','3 × M2 × 4 TAP at the camera-clamp anchors.')],
      'electronics':[
        operation('electronics-current-01','Prepare the closed curved head cap',cap,cap,'The printed cap already contains the board rails, controller posts and audio posts. Do not add separate posts, the old audio carrier, or Pi spacers.'),
        operation('electronics-current-02','Preconnect and secure the speaker cage',audio[1:-1],audio[:-1],'Connect the two speaker leads before trapping the speaker between keeper and cradle. Support the cone without pressing it.','2 × M2.5 × 8 TAP through the speaker cage into the cap posts.'),
        operation('electronics-current-03','Preconnect and seat the amplifier',['amplifier'],audio,'Connect speaker outputs and prepare VIN, GND, BCLK, LRCLK and DIN while the pads and terminals are exposed. Use the current amplifier location matching the cap posts.','2 × M2.5 × 8 TAP; VIN to the head 5 V branch, GND to Pi physical pin 20, BCLK to 12, LRCLK to 35, DIN to 40.'),
        operation('electronics-current-04','Connect OpenRB before fitting it to the cap',['openrb'],audio+['openrb'],'Prepare both keyed motor bus leads, J4 power and the internal USB connection while the controller sockets are accessible. '+USB,'4 × M2 × 6 TAP into the integral controller posts.'),
        operation('electronics-current-05','Connect and mount Pi on the integral rails',pi,electronic,'Preserve the existing 40-pin header. Fit the required female leads and the Pi end of the camera ribbon while the face is off. Arrange the flexible tails by hand so they do not bear on the face. Their practical bend clearance remains a prototype fit check.','4 × M2 × 6 TAP into the integral Pi rails. No 2 mm Pi spacers are used.')],
      'head-close':[
        operation('head-close-current-01','Inspect the connected head with the face open',['upper_pad'],full,'Before closing, check both CSI latches, the amplifier terminals, both motor-bus plugs and all PCB screws. Keep ribbon slack inside the available cavity and away from the jaw and shell seam.'),
        operation('head-close-current-02','Trial-fit the face and cap without screws',[],full,'Support the face and populated cap separately, bring them together gently, and watch the plug bodies and wire exits. The assembled view helps identify the parts; check the real plugs and wires as the seam closes. '+USB),
        operation('head-close-current-03','Complete closure only after the fit check',[],full,'If the actual plugs and flexible leads fit without pressure, close the shell using the existing shell attachment screws. Otherwise reopen it and correct the local interference. Whole-head closure, power-up and motor commissioning have not been completed.','After a successful fit: 3 × M2.5 × 8 TAP for the shell closure; no M2 × 5.')]
    }
    titles={'head':'Original jaw and current lower shell','camera':'Eye camera and ribbon preparation','electronics':'Populate the detached curved cap','head-close':'Pre-close checks and prototype fit'}
    ownership={'head':jaw+['head_bottom'],'camera':camera,'electronics':electronic,'head-close':['upper_pad']}
    for m in data['modules']:
        if m['id'] in HEAD_MODULES:
            mid=m['id'];m.update(title=titles[mid],operations=ops[mid],ownedPartKeys=ownership[mid],
              partKeys=list(dict.fromkeys(k for o in ops[mid] for k in o['visiblePartKeys'])),
              contextPartKeys=[],checks=['Keep power disconnected. Check that parts seat and wires remain free before tightening the shell.'],
              prerequisites=['Use the current 12-part incremental print set. Preserve completed legs.'])
    metadata={'status':'CURRENT_PRINT_PROTOTYPE_GUIDE','sourceHashes':sources,'printGeometrySynchronized':True,
              'wholeHeadAccepted':False,'physicalCommissioningPassed':False,'finishedUsbCableSelected':False,
              'retiredPartKeys':sorted(retired),'currentPartKeys':sorted(newkeys),'fasteners':adoption['fastenerSummary'],
              'boundary':USB}
    metadata['moduleFasteners']={
      'head':[{'spec':'M2 × 6 TAP','quantity':2,'use':'Jaw motor output'}, {'spec':'M2 × 7 TAP','quantity':2,'use':'Other jaw motor output seats'}, {'spec':'M2.5 × 6 TAP','quantity':4,'use':'Lower-shell support frame'}],
      'camera':[{'spec':'M2 × 4 TAP','quantity':3,'use':'Three camera-retainer anchors'}],
      'electronics':[{'spec':'M2 × 6 TAP','quantity':8,'use':'Four OpenRB screws and four Pi screws'}, {'spec':'M2.5 × 8 TAP','quantity':4,'use':'Two speaker-cage screws and two amplifier screws'}],
      'head-close':[{'spec':'M2.5 × 8 TAP','quantity':3,'use':'Shell attachment, only after a successful unpowered fit check'}]
    }
    data['headPrototypeRevision']=metadata
    # Replace the obsolete current-head wiring overlay as well as assembly meshes.
    spatial=spatial or {}; prior=spatial.get('currentParts',[])
    oldreplace=set(spatial.get('replacePartKeys',[]))
    legacy_overlay=read(G/'current-wiring-overlay.json')
    stable_context={'motor14','motor15','head_yaw_link','head_roll_ring_a','head_roll_ring_b'}
    retired_overlay={p['key'] for p in legacy_overlay['currentParts']}-stable_context
    spatial['currentParts']=[p for p in prior if p['key'] not in oldowned|newkeys|retired_overlay]+parts
    spatial['replacePartKeys']=sorted(oldreplace|oldowned|newkeys)
    spatial['headPrototypeRevision']=metadata
    # Old head routes and connector coordinates belong to a different PCB pose.
    # Keep connection instructions, but never animate those stale spatial endpoints.
    headids={'camera-ribbon','pi-otg','openrb-usb','audio-vin','audio-return','audio-12','audio-35','audio-40','audio-20','audio-gain','speaker','pi-gnd-6','pi-gnd-14'} | moved_head_connection_ids(wiring,spatial)
    metadata['retiredHeadRouteIds']=sorted(headids)
    bykey={p['key']:p for p in parts}
    aliases={'amp':'amplifier','camera':'camera_board'}
    for node in spatial.get('nodes',[]):
        key=aliases.get(node['id'],node['id'])
        if key in {'pi','openrb','amplifier','speaker','camera_board'}:
            p=bykey[key]; node.update(position=p['center'],bounds=p['bounds'],partKeys=[key],connectorOrientationVerified=False,anchorEvidence='Current component centre for locating the part; not a connector or pin position.')
    for c in spatial.get('connections',[]):
        if c['id'] in headids:
            c.update(segments=[],endpoints=[],focusPartKeys=c.get('focusPartKeys') or (['camera_board','pi'] if c['id']=='camera-ribbon' else ['pi','openrb'] if c['id'] in {'pi-otg','openrb-usb'} else ['amplifier','speaker','pi']),
                     geometryStatus='Current head: use open-cap instructions; old route geometry retired.',prototypeFitPending=True)
    if wiring:
        wiring['headPrototypeRevision']=metadata
        # One internal link replaces the obsolete two-adapter/coupler tutorial.
        wiring['connections']=[c for c in wiring.get('connections',[]) if c['id']!='openrb-usb']
        spatial['connections']=[c for c in spatial.get('connections',[]) if c['id']!='openrb-usb']
        for group in wiring.get('groups',[]):
            group['connectionIds']=[i for i in group.get('connectionIds',[]) if i!='openrb-usb']
            if group['id']=='head': group['description']='Connect the eye camera, controller, Pi and audio while the cap is open. Trial-fit the real plugs and flexible leads before closing.'
        for step in wiring.get('steps',[]):
            step['connections']=[c for c in step.get('connections',[]) if c['id']!='openrb-usb']
            if 'connectionIds' in step: step['connectionIds']=[i for i in step['connectionIds'] if i!='openrb-usb']
        collections=[wiring.get('connections',[])]+[s.get('connections',[]) for s in wiring.get('steps',[])]
        for connections in collections:
            for c in connections:
                if c['id'] in headids:
                    if c['id']=='pi-otg':
                        c.update(purpose='Internal Pi-to-OpenRB USB data connection',
                                 **{'from':'Pi Zero W Micro-B USB host port','to':'OpenRB USB-C device port'},
                                 wire='Compatible internal USB data cable; finished ends remain unselected',
                                 fromNodeIds=['pi'],toNodeIds=['openrb'],
                                 pins=[{'from':'Micro-B host','to':'USB-C device','signal':'USB data'}],notes=[USB])
                    elif c['id']=='camera-ribbon':
                        c.update(**{'from':'Pi CSI 22-contact socket','to':'Eye camera CSI 15-contact socket'},
                                 wire='Raspberry Pi Standard–Mini camera cable · 200 mm')
                    c['tutorial']={'prepare':['Keep cap and face detached; electronics unpowered.'],
                      'assemble':[USB if c['id'] in {'pi-otg','openrb-usb'} else 'Connect both ends with their latches and polarity visible, before fitting the face. Arrange flexible slack through the open cavity without pulling on either connector.'],
                      'check':['Verify connector seating and check that the actual lead is not trapped when trial-fitting the cap. No completed whole-head fit is claimed.']}
                    c['prototypeFitPending']=True
    if wiring: add_head_power_instructions(data,wiring,spatial)
    return data,wiring,spatial
