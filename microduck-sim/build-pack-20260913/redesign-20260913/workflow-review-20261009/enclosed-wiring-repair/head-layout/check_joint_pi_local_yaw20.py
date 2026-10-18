from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0])
pikeys=[k for k in rows if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_'))]
retired=['openrb','openrb_usb_receiving','curved_cap_hardware','camera_ribbon_200']+[k for k in rows if k.startswith('E-pi-')]
jp=json.loads((D/'packing-photo/pi-cardinal-screen.json').read_text());jr=json.loads((D/'packing-amp-free/openrb-tilt-screen.json').read_text());p=next(r for r in jp['results'] if r['orientationId']==20)['candidates'][0];r=next(r for r in jr['results'] if r['orientationId']==218)['candidates'][0];j={'pi':p,'openrb':r};Tp=np.array(p['currentWorldDelta']);Tr=np.array(r['currentWorldDelta']);piT=np.array(json.loads((H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json').read_text())['worldTransform'])
a=np.radians(-20);Z=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]]);ax=np.arctan(-.035);ay=np.arctan(.08);X=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]]);Y=np.array([[np.cos(ay),0,np.sin(ay)],[0,1,0],[-np.sin(ay),0,np.cos(ay)]]);Q=np.eye(4);Q[:3,:3]=X@Y@Z;Q[:3,3]=np.array([56.,9.,132.])-Q[:3,:3]@np.array([59.,-1.,131.]);Tp=Q@Tp;j['pi']['currentWorldDelta']=Tp.tolist();j['localAdjustment']={'piCenter':[56,9,132],'piYaw':-20,'planeSlopeXZ':-.08,'planeSlopeYZ':-.035,'causalReason':'Move full MicroB sidewards past EH outer wall while tilting GPIO row to follow side crown; rear PCB stays above jaw.'}
pi_parts={k:source(k).transform(Tp[:3])for k in pikeys};pi=mf.Manifold.batch_boolean(list(pi_parts.values()),mf.OpType.Add)
sc=mf.Manifold.cube([6,13,25]).translate([63.01,2.4,146.0496]).transform(piT[:3]).transform(Tp[:3])
ep=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';rb_parts={str(i):load(r['mesh']).transform(Tr[:3])for i,r in enumerate(json.loads(ep.read_text())['components'])};rb=mf.Manifold.batch_boolean(list(rb_parts.values()),mf.OpType.Add)
cplug=load(H/'usb-access/full-harness/openrb-usb-c-published-envelope-world.stl').transform(Tr[:3]);moving={'pi_populated':pi,'microB_photo_receiving':sc,'openrb_populated':rb,'C_plug':cplug};hits=[];clear=0;tested=0
ports=json.loads((W/'enclosed-wiring-repair/motor-wires/two-openrb-ports.json').read_text());
for i,port in enumerate(ports['ports']):
 b=np.array(port['housingLocalBounds']);moving['EH_'+str(i+1)]=mf.Manifold.cube(b[1]-b[0]).translate(b[0]).transform(np.array(port['transform'])[:3]).transform(Tr[:3])
for k in rows:
 if k in pikeys+retired:continue
 if k=='head_cap':obs=load(D/'native-cap-registered-world.stl')
 elif k=='face_panel':obs=load(H/'camera-ribbon-repair/positive-x225/face_three_screw_camera-world.stl')
 else:obs=source(k)
 for key,s in moving.items():
  tested+=1;b=np.array(s.bounding_box()).reshape(2,3);b2=np.array(obs.bounding_box()).reshape(2,3)
  if np.any(b[1]<b2[0])or np.any(b2[1]<b[0]):clear+=1;continue
  q=s^obs;v=max(0,q.volume())
  if v>1e-6:
   entry={'moving':key,'fixed':k,'volume':v,'bounds':list(q.bounding_box())}
   if key=='pi_populated':entry['individual']=[{'key':pk,'volume':(ps^obs).volume()}for pk,ps in pi_parts.items()if (ps^obs).volume()>1e-6]
   if key=='openrb_populated':entry['componentIds']=[pk for pk,ps in rb_parts.items()if (ps^obs).volume()>1e-6]
   hits.append(entry)
  else:clear+=1
 del obs;gc.collect()
for a,b in [(a,b) for a in ['pi_populated','microB_photo_receiving'] for b in ['openrb_populated','C_plug','EH_1','EH_2']]:
 q=moving[a]^moving[b];v=max(0,q.volume());tested+=1
 if v>1e-6:
  entry={'moving':a,'fixed':b,'volume':v,'bounds':list(q.bounding_box())}
  if a=='pi_populated':entry['individual']=[{'key':pk,'volume':(ps^moving[b]).volume()}for pk,ps in pi_parts.items()if (ps^moving[b]).volume()>1e-6]
  hits.append(entry)
 else:clear+=1
out=D/'joint-pi-local-yaw20';out.mkdir(exist_ok=True)
# Keep compound solids internal; output independent part geometry after collision report.
r={'integrationReady':False,'candidate':j,'testedPairs':tested,'clearPairs':clear,'hits':hits,'sourceHashes':hashes,'limits':'Coarse pairing followed by real solids; SC0727 25x13x6 photo receiving and corrected EDAC1.30mm PCB datum; 25mm length assumed, C body thickness7 assumed; retired board mount/flexible shapes must be rebuilt, not hidden in final model.'}
(out/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(hits,indent=2))
