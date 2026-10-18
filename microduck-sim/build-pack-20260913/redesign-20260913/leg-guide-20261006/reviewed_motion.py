"""Authored assembly translations, reviewed against the native guide meshes."""
def apply(modules,parts,screws):
    vectors={
      'torso_base':[0,0,-28], 'power_support':[-28,0,0], 'ring10_torso':[0,0,-28], 'ring5_torso':[0,0,-28],
      'regulator':[0,0,28], 'imu_clamp':[-28,0,0], 'imu_board':[-28,0,0], 'imu_cover':[-28,0,0],
      'idler11':[0,-28,0], 'idler12':[0,-28,0], 'idler_cap11':[0,-28,0], 'idler_cap12':[0,-28,0],
      'neck_pitch_ring':[0,0,28], 'motor13':[0,0,28], 'motor14':[-28,0,0],
      'head_bottom':[0,0,-28], 'jaw_support':[0,0,28], 'pi':[-28,0,0], 'openrb':[0,0,-28], 'audio_carrier':[0,0,-28],
      'washer_E-camera_foot-01_1':[0,-28,0], 'washer_E-camera_foot-02_1':[0,28,0], 'washer_E-camera_hinge-01_2':[28,0,0],
    }
    for m in modules:
      if 'leg' in m['id']:continue
      for op in m['operations']:
        op.setdefault('partApproachVectors',{}).update({k:v for k,v in vectors.items() if k in op['add']})
    by={m['id']:m for m in modules}
    power=by['power']['operations'][1]
    power.update(moveKeys=['regulator_insert','regulator'],approachVector=[-28,0,0])
    capkeys=['head_cap','openrb','audio_carrier','amplifier','speaker','camera_pitch_foot','camera_cradle','camera_board']
    for op in by['head-close']['operations'][:2]:
      op['isolatedPartKeys']=[p['key'] for p in parts if p['key'] not in capkeys and not p['key'].startswith(('nut_E-camera','washer_E-camera','nut_E-openrb'))]

    by['neck']['operations'][6]['approachVector']=[0,40,0]
    by['neck']['operations'][8]['approachVector']=[0,0,40]
    by['head-close']['operations'][0]['approachVector']=[0,0,40]
    roll=by['neck']['operations'][4]
    roll['add']=['head_yaw_link','head_roll_ring_a','head_roll_ring_b','motor14']
    roll['partApproachVectors']={'head_yaw_link':[0,0,0],'head_roll_ring_a':[-60,0,0],'head_roll_ring_b':[-60,0,0],'motor14':[-60,0,0]}
    import copy
    audio=by['electronics']['operations']
    if len(audio)==6:
      audio[4].update(title='Populate the audio carrier on the open bench',isolatedPartKeys=['audio_carrier','amplifier','speaker'],partApproachVectors={'audio_carrier':[0,0,0],'amplifier':[0,0,60],'speaker':[0,0,60]},text='Keep the carrier off the cap. Seat and connect the amplifier and speaker from the open face, then retain them with the specified narrow ties.')
      fastening=copy.deepcopy(audio[5])
      audio[5].update(title='Retain and check the loose audio subassembly',add=[],screwIds=[],isolatedPartKeys=['audio_carrier','amplifier','speaker'],text='Fit the two tie loops for each device. Keep the speaker diaphragm free and the labeled cable ends accessible; support the carrier for installation.')
      audio.append(dict(id='electronics-07',kind='place',title='Bring the populated audio carrier into the detached cap',add=[],screwIds=[],moveKeys=['audio_carrier','amplifier','speaker'],approachVector=[0,0,-60],isolatedPartKeys=['audio_carrier','amplifier','speaker','head_cap','openrb'],text='With the cap open on the bench, move the retained carrier, amplifier and speaker together into its mounting seats. Keep leads clear of the posts.'))
      fastening['id']='electronics-08';audio.append(fastening)
    head=by['head']['operations']
    if head[0]['add']==['head_bottom','jaw_support']:
      fastening=copy.deepcopy(head[1])
      head[0].update(title='Seat and connect the jaw motor in the loose support',add=['jaw_support','motor15'],isolatedPartKeys=['jaw_support','motor15'],partApproachVectors={'jaw_support':[0,0,0],'motor15':[0,60,0]},text='Keep the black support separate from the yellow lower shell. Seat ID15 from the open side and connect its lead while its socket is accessible. Keep the moving jaw off.')
      head[1].update(title='Check jaw-motor retention before fitting the shell',add=[],screwIds=[],isolatedPartKeys=['jaw_support','motor15'],text='Check the existing printed locating features while supporting the motor. No extra case screw is specified; do not use a screw to pull a tight fit closed.')
      head[2].update(title='Fit the lower shell around the prepared motor supports',add=['head_bottom'],moveKeys=[],approachVector=[0,0,-60],text='Support the prepared jaw motor and roll joint. Bring the yellow lower shell up from below. The source shell contacts the motor seats and ring before its nominal final pose; check the actual fit gently before installing the support screws.')
      head[3]=fastening;head[3]['id']='head-04';head[3]['text']='After the shell seats freely by hand, install four M2.5×6 TAP into the shell pilots. Do not pull the shell over a binding motor or ring with these screws.'
    for mod in modules:
      for i,op in enumerate(mod['operations'],1):op['id']=f"{mod['id']}-{i:02d}"
    shell=by['head']['operations'][2]
    shell['approachVector']=[0,0,-40]
    shell['motionStop']={'start':[0,0,-40],'stop':[0,0,-0.70068359375],'movingKeys':['head_bottom'],'contactPair':['head_bottom','motor15'],'reason':'The source lower shell reaches the jaw-motor seat before the nominal assembled pose. Stop and check the actual motor and ring seats gently; do not pull them closed with screws.'}
    shell['beforeClose']=['Check the jaw and roll motor seats and both support rings by hand.','Continue to the four support screws only when the lower shell seats without force.']
    # Fit the cap's captive camera nuts before the OpenRB occupies their entry.
    camera=by['camera'];electronics=by['electronics']
    camera['prerequisites']=['head'];electronics['prerequisites']=['head','camera']
    camera['title']='Camera on the empty detached cap'
    camera['contextPartKeys']=[]
    if 'head_cap' not in camera['operations'][0]['add']:camera['operations'][0]['add'].insert(0,'head_cap')
    for op in electronics['operations']:op['add']=[k for k in op['add'] if k!='head_cap']
    electronics['contextPartKeys']=['head_cap','camera_pitch_foot','camera_cradle','camera_board']
    i=modules.index(camera);modules.pop(i);modules.insert(modules.index(electronics),camera)
    by['neck']['operations'][4]['partApproachVectors']['head_roll_ring_b']=[60,0,0]
    for mid,index,keys,start,stop,pair in [
      ('electronics',3,[f'nut_E-openrb-0{i}' for i in range(1,5)],[0,0,12],[0,0,2.7],['nut_E-openrb-01','head_cap']),
      ('camera',1,['nut_E-camera_foot-01','nut_E-camera_foot-02'],[0,0,-12],[0,0,-2.8],['nut_E-camera_foot-01','head_cap'])]:
      op=by[mid]['operations'][index]
      op['motionStop']={'start':start,'stop':stop,'movingKeys':keys,'contactPair':pair,'reason':'A straight nut approach meets the cap pocket entrance before its final seat. Hand-position the nut through the open cap and check that it sits flat; do not pull it through the obstruction with the screw.'}
      op['beforeClose']=['Keep the cap detached so both sides remain accessible.','Fit the captive nuts by hand before tightening the named screws. If a nut cannot seat flat without force, leave this joint open for fit correction.']
    for mod in modules:
      for i,op in enumerate(mod['operations'],1):
        op['id']=f"{mod['id']}-{i:02d}"
        op.setdefault('highlightKeys',[]);op.setdefault('retentionNotes',[])
    # The jaw must be fitted on the bench; open it for the cap screw corridors.
    close=by['head-close']['operations'];head=by['head']['operations']
    pose={'keys':['jaw_frame','lower_pad'],'axis':[0,1,0],'pivot':[26.1,0,118.6146],'degrees':30}
    if len(close)==8:
      support_screws=list(head[3]['screwIds']);jaw_screws=list(close[5]['screwIds'])
      def op(kind,title,add=None,screwIds=None,**kw):
        return dict(kind=kind,title=title,add=add or [],screwIds=screwIds or [],highlightKeys=[],retentionNotes=[],**kw)
      by['head']['operations']=[
        op('place','Prepare the loose jaw, pad and support',['jaw_support','jaw_frame','lower_pad'],text='Keep the black support separate on the bench. Fit the lower pad to the moving jaw before adding its motor; keep the pad clear of the output screw faces.',isolatedPartKeys=['jaw_frame','lower_pad'],partApproachVectors={'jaw_frame':[0,0,0],'lower_pad':[0,0,32],'jaw_support':[0,0,0]}),
        op('fasten','Check the lower pad on the loose jaw',text='Check the pad sits on its own jaw feature and does not cover the motor-output screw holes. This is a hand-fit check; no screw is added.',isolatedPartKeys=['jaw_frame','lower_pad']),
        op('place','Seat ID15 in the loose jaw',['motor15'],text='Support the loose jaw and pad. Approach the output from the open side, with the lower shell and black support still separate.',isolatedPartKeys=['jaw_frame','lower_pad','motor15'],approachVector=[0,-32,0]),
        op('fasten','Fasten the jaw output on the open bench',screwIds=jaw_screws,text='Install the two M2×6 and two M2×7 TAP at their exact curved seats while the output faces are exposed.',isolatedPartKeys=['jaw_frame','lower_pad','motor15']),
        op('place','Fit the prepared jaw and motor into the loose support',text='Keep the black support off the lower shell. The straight preview stops at its first obstruction; hand-fit the support and jaw together without using screws to pull them closed.',moveKeys=['jaw_frame','motor15','lower_pad'],isolatedPartKeys=['jaw_support','jaw_frame','motor15','lower_pad'],approachVector=[0,0,-32]),
        op('fasten','Check the jaw-support fit and connect the lead',text='Continue only after the motor and integral rear seat are correctly retained and the jaw turns freely. Connect ID15 while its socket is accessible. A rigid full-entry path is not established for this printed support.',isolatedPartKeys=['jaw_support','jaw_frame','motor15','lower_pad'],wiringStage=4),
        head[2],
        op('fasten','Fasten the support after checking the lower shell',screwIds=support_screws,text='After the yellow lower shell seats freely by hand, install four M2.5×6 TAP into its pilots. Leave the upper pad off until the cap screws are complete.')]
      close[4]=op('place','Fit the upper lip pad with the jaw held open',['upper_pad'],text='Keep the jaw open about 30°. Bring the upper pad through the front opening, then lift it into its seat. Fit it after all three cap screws are complete.',fixedPoses=[pose],motionWaypoints={'movingKeys':['upper_pad'],'points':[[40,0,-3],[-.375,0,-3],[0,0,0]],'reason':'Enter through the open mouth, then raise the pad. Keep the lower jaw open throughout. Check the final printed fit by hand.'})
      close[5]=op('fasten','Check pad retention and all moving cable loops',text='With source power disconnected, gently open and close the jaw and move the head through its intended range. Check pad retention and cable slack; stop at rubbing, tension or pinching.')
      del close[6:]
    by['head-close']['title']='Close the head with jaw open, then upper pad'
    by['head-close']['contextPartKeys'] += ['jaw_frame','lower_pad','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']
    for op in by['head-close']['operations'][:5]:op['fixedPoses']=[pose]
    by['head-close']['operations'][3]['text']='Keep the jaw and lower pad open about 30° and leave the upper pad off. Install the two front M2.5×8 TAP closure screws through the open mouth-side corridors, then the neck-end screw.'
    by['head-close']['operations'][3]['access']='Open the lower jaw about 30° before approaching either front screw. Leave the upper pad off until these screws are finished.'
    for mod in modules:
      for i,operation in enumerate(mod['operations'],1):
        operation['id']=f"{mod['id']}-{i:02d}"
        operation.setdefault('highlightKeys',[]);operation.setdefault('retentionNotes',[])
    by['head']['title']='Jaw bench assembly and lower-shell fit'
    by['head']['checks']=['Fit the jaw and motor to the loose support before adding the lower shell.','Keep the upper pad off; open the lower jaw for final cap screws.']
    jawfit=by['head']['operations'][4]
    jawfit['motionStop']={'start':[0,0,-32],'stop':[0,0,-13.420135498046875],'movingKeys':['jaw_frame','motor15','lower_pad'],'contactPair':['jaw_frame','jaw_support'],'reason':'The assembled jaw reaches the printed support before a straight entry can finish. This is a measured obstruction preview. Check the real loose support and jaw fit before continuing; do not force it with the output screws.'}
    cap=by['head-close']['operations'][2]
    cap['text']='Keep the lower jaw open about 30° and the upper pad off. Bring the complete cap, camera and audio group toward the connected face. The rim blocks a purely vertical rigid entry; the preview stops before that contact. Check the actual rim engagement gently before fastening.'
    cap['motionStop']={'start':[0,0,48],'stop':[0,0,32.413434982299805],'movingKeys':cap['moveKeys'],'contactPair':['head_cap','face_panel'],'reason':'The head-cap rim meets the face along this straight route. The guide has not established the complete rigid closing maneuver. Keep the head open if the rim cannot engage without force or pinching a lead.'}
    cap['beforeClose']=['Lower jaw held open about 30°; upper pad remains off.','All connectors seated and cables outside the rim seam.','Actual rim engagement checked by hand before tightening.']
    by['head-close']['checks']=['All three cap screws are completed with the lower jaw open and upper pad absent.','Complete actual fit and disconnected cable-clearance checks before powering.']

    shell=by['head']['operations'][6]
    shell['motionStop'].update(stop=[0,0,-20.22527503967285],contactPair=['head_bottom','jaw_frame'],reason='With the prepared jaw present, the lower shell meets the jaw before its nominal seat. This preview stops before the measured obstruction. The complete shell-fitting maneuver still needs an actual bench fit; keep the joint open if it cannot engage freely.')
    face=by['head-close']['operations'][0]
    face['motionStop']={'start':[0,0,40],'stop':[0,0,2.7495737075805664],'movingKeys':face['moveKeys'],'contactPair':['face_panel','head_bottom'],'reason':'The face meets the lower-shell seat near the end of the rigid approach. The preview stops before contact. Check the actual mating edges and cable clearance by hand before proceeding.'}

    by['head-close']['operations'][3]['title']='Fasten the cap with the jaw open and upper pad absent'
