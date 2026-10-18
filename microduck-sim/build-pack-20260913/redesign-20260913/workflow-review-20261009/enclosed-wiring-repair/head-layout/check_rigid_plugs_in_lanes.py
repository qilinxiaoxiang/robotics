from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0])
posefile=D/'native-lanes-pose.json';pose=json.loads(posefile.read_text());hashes[str(posefile)]=sha(posefile)
regfile=D/'native-fusion-repair-inputs.json';reg=json.loads(regfile.read_text());hashes[str(regfile)]=sha(regfile)
Tp=np.array(pose['piCurrentWorldDelta']);Tr=np.array(pose['openrbNativeToWorld'])@np.linalg.inv(np.array(reg['openrb']['nativeToCurrentWorld']))
pifile=H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json';piT=np.array(json.loads(pifile.read_text())['worldTransform']);hashes[str(pifile)]=sha(pifile)
plug={'microB_photo_receiving':mf.Manifold.cube([6,13,25]).translate([63.01,2.4,146.0496]).transform(piT[:3]).transform(Tp[:3])}
cpfile=H/'usb-access/full-harness/published-usbc-verification.json';cp=json.loads(cpfile.read_text());hashes[str(cpfile)]=sha(cpfile)
portdatumfile=D/'openrb-usbc-native-port.json';portdatum=json.loads(portdatumfile.read_text());hashes[str(portdatumfile)]=sha(portdatumfile)
ax=np.array(portdatum['nativeOutwardAxis']);w=np.array(portdatum['nativeWidthAxis']);Cn=np.eye(4);Cn[:3,:3]=np.column_stack((w,np.cross(ax,w),ax));Cn[:3,3]=portdatum['correctedAssumedMouldShoulderMm'];C=np.array(reg['openrb']['nativeToCurrentWorld'])@Cn
plug['C_mould_22']=mf.Manifold.cube([12,7,22]).translate([-6,-3.5,0]).transform(C[:3]).transform(Tr[:3])
plug['C_strain_5']=mf.Manifold.cylinder(5,3.25/np.cos(np.pi/64),3.25/np.cos(np.pi/64),64).translate([0,0,22]).transform(C[:3]).transform(Tr[:3])
portfile=W/'enclosed-wiring-repair/motor-wires/two-openrb-ports.json';ports=json.loads(portfile.read_text());hashes[str(portfile)]=sha(portfile)
for i,port in enumerate(ports['ports']):
 b=np.array(port['housingLocalBounds']);plug['EH_'+str(i+1)]=mf.Manifold.cube(b[1]-b[0]).translate(b[0]).transform(np.array(port['transform'])[:3]).transform(Tr[:3])
out=D/'rigid-plug-in-lanes';out.mkdir(exist_ok=True);meshes=[]
for k,s in plug.items():
 p=out/(k+'-world.stl');meta=pm.export(ctx,s,p);meshes.append({'key':k,'file':str(p),'sha256':sha(p),'bounds':list(s.bounding_box()),**meta})
excluded=[];obstacles=[];checks=[]
for k in rows:
 if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_','E-pi-')) or k in ['openrb','openrb_usb_receiving','curved_cap_hardware','camera_ribbon_200']:
  excluded.append(k);continue
 if k=='head_cap':obs=load(D/'native-cap-registered-world.stl')
 elif k=='face_panel':obs=load(H/'camera-ribbon-repair/positive-x225/face_three_screw_camera-world.stl')
 else:obs=source(k)
 obstacles.append(k)
 for name,s in plug.items():
  a=np.array(s.bounding_box()).reshape(2,3);b=np.array(obs.bounding_box()).reshape(2,3)
  if np.any(a[1]<b[0])or np.any(b[1]<a[0]):checks.append({'plug':name,'fixed':k,'method':'aabb-separated','volumeMm3':0});continue
  q=s^obs;checks.append({'plug':name,'fixed':k,'method':'individual-solid-intersection','volumeMm3':max(0,q.volume()),'intersectionBounds':list(q.bounding_box()) if q.volume()>1e-6 else None})
 del obs;gc.collect()
restored=W/'enclosed-wiring-repair/enclosure-shell/cap-crown-and-rear-restored-world.stl'
obs=load(restored)
for name,s in plug.items():
 q=s^obs;checks.append({'plug':name,'fixed':'restored_cap_retaining_mounts','method':'individual-solid-intersection','volumeMm3':max(0,q.volume()),'intersectionBounds':list(q.bounding_box()) if q.volume()>1e-6 else None})
report={'integrationReady':False,'scope':'Only five separate plug receiving solids against fixed source scene; no unions. Pi/OpenRB populated boards are under separate native CAD review.','poseFile':str(posefile),'piCurrentWorldDelta':Tp.tolist(),'openrbCurrentWorldDelta':Tr.tolist(),'sourceHashes':hashes,'meshes':meshes,'checks':checks,'hits':[x for x in checks if x['volumeMm3']>1e-6],'excluded':excluded,'limits':['MicroB 13x6mm from official-photo receiving estimate;25mm axial extent assumed, not manufacturer-dimensioned. Correct EDAC PCB-plane to socket centre1.30mm.','USB-C22mm mould+5mm diameter6.5mm strain collar source drawing;7mm body thickness receiving assumption.','EH9.5x3.8x7.1 complete housing receiving bound, not detailed latch/mated cavity.','Native shell and restored shell with old mounts reported separately.','No insertion sweep, flexible route, tool access or whole-head acceptance.']}
p=D/'rigid-plug-in-lanes.json';p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'file':str(p),'tested':len(checks),'hits':report['hits']},indent=2))
