from pathlib import Path
OUT=Path(__file__).resolve().parent;D=OUT.parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0].replace('D=Path(__file__).resolve().parent;R=', 'D=Path(__file__).resolve().parent.parent;R='))
T=np.array([[0,0,1,-29],[1,0,0,0],[0,1,0,-1],[0,0,0,1]],float)
regfile=D/'native-fusion-repair-inputs.json';reg=json.loads(regfile.read_text());hashes[str(regfile)]=sha(regfile);delta=T@np.linalg.inv(np.array(reg['openrb']['nativeToCurrentWorld']))
ep=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';hashes[str(ep)]=sha(ep);recs=json.loads(ep.read_text())['components'];moving={};kinds={}
for i,r in enumerate(recs):
 key='OpenRB_component_'+str(i);actual=D/'actual-openrb-components'/('component-%04d-world.stl'%i)
 # Existing hulls cover every original source triangle; negative intersections remain conservative until detailed component comparison.
 moving[key]=load(r['mesh']).transform(delta[:3]);kinds[key]='source-component-conservative-convex-hull'
portfile=D/'openrb-usbc-native-port.json';port=json.loads(portfile.read_text());hashes[str(portfile)]=sha(portfile);C=np.eye(4);ax=np.array(port['nativeOutwardAxis']);w=np.array(port['nativeWidthAxis']);C[:3,:3]=np.column_stack((w,np.cross(ax,w),ax));C[:3,3]=port['correctedAssumedMouldShoulderMm'];C=T@C
moving['USB_C_mould22']=mf.Manifold.cube([12,7,22]).translate([-6,-3.5,0]).transform(C[:3]);moving['USB_C_strain5']=mf.Manifold.cylinder(5,3.25/np.cos(np.pi/64),3.25/np.cos(np.pi/64),64).translate([0,0,22]).transform(C[:3])
portsfile=W/'enclosed-wiring-repair/motor-wires/two-openrb-ports.json';hashes[str(portsfile)]=sha(portsfile);ports=json.loads(portsfile.read_text())
for i,port in enumerate(ports['ports']):
 b=np.array(port['housingLocalBounds']);moving['EH_'+str(i+1)]=mf.Manifold.cube(b[1]-b[0]).translate(b[0]).transform(np.array(port['transform'])[:3]).transform(delta[:3])
for k in moving:
 if not k.startswith('OpenRB_'):kinds[k]='connector-receiving-bound'
keys=['torso_base','shell_left','shell_right','ring10_torso','ring5_torso','power_support','regulator_insert','regulator','imu_clamp','imu_cover','imu_board','hip','yaw','right_hip','right_yaw','motor5','motor10','neck_link_a','neck_link_b','neck_pitch','neck_pitch_ring','head_yaw_link','head_roll_ring_a','head_roll_ring_b','motor11','motor12','motor13','idler11','idler12','idler_cap11','idler_cap12','motor14','head_bottom','jaw_support','jaw_frame','lower_pad','upper_pad']
checks=[]
for fk in keys:
 obs=source(fk);b=np.array(obs.bounding_box()).reshape(2,3)
 for k,s in moving.items():
  a=np.array(s.bounding_box()).reshape(2,3)
  if np.any(a[1]<b[0])or np.any(b[1]<a[0]):checks.append({'moving':k,'fixed':fk,'volumeMm3':0,'method':'aabb-separated'});continue
  q=s^obs;v=max(0,q.volume());checks.append({'moving':k,'fixed':fk,'volumeMm3':v,'method':'independent-component-intersection','intersectionBounds':list(q.bounding_box()) if v>1e-6 else None})
 del obs;gc.collect()
meshes=[]
for k,s in moving.items():
 if k.startswith('OpenRB_'):continue
 p=OUT/(k+'-world.stl');meta=pm.export(ctx,s,p);meshes.append({'key':k,'file':str(p),'sha256':sha(p),'bounds':list(s.bounding_box()),**meta})
r={'integrationReady':False,'nativeOpenRBToWorld':T.tolist(),'currentOpenRBWorldToCandidate':delta.tolist(),'sourceHashes':hashes,'movingKinds':kinds,'checks':checks,'hits':[q for q in checks if q['volumeMm3']>1e-6],'meshes':meshes,'limits':['142 conservative independent hulls exactly cover manufacturer STL source triangles; clear is conservative; positive intersection is not yet proof of actual material contact. No compound union.','DFR regulator/insert and oldpower_support intentionally reported separately; none removed from results.','USB-C native mouth [0.015,32.9,3.23], assumed shoulder gap1.2; thickness7mm receiving bound. EH receiver includes full inserted portion and catalog bound, not detailed mating cavity.','Static single neutral pose only; no dynamic or insertion acceptance.']};(OUT/'report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'tested':len(checks),'hits':r['hits']},indent=2))
