from pathlib import Path
O=Path(__file__).resolve().parent
exec((O/'check_one_pose.py').read_text().split('Tp=')[0])
N=O/'native';receipt=read(N/'native-audio-readback.json');assert receipt['status']=='NATIVE_AUDIO_FEATURES_CREATED_NEIGHBOR_CHECK_PENDING'
for f in receipt['exports']:assert sha(f['file'])==f['sha256']
cap=load(N/'closed-cap-Pi-audio-mounts-world.stl');oldcap=load(D/'pi-roof-mounts/closed-cap-with-pi-bosses-world.stl');added=cap-oldcap
cradle=load(N/'speaker-cradle-single-seat-adjustment.stl');oldcradle=source('speaker_cradle');pad=cradle-oldcradle
Tp=np.array(read(D/'pi-front-up05-pose.json')['piCurrentWorldDelta']);piT=np.array(read(H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json')['worldTransform']);amp=load(O/'amplifier-front-free-bay-world.stl');keeper=source('speaker_keeper');speaker=source('speaker');checks=[]
def test(op,s,obs,key,offset=None,plane=False):
 a=np.array(s.bounding_box()).reshape(2,3);b=np.array(obs.bounding_box()).reshape(2,3);v=0. if np.any(a[1]<b[0])or np.any(b[1]<a[0])else max(0,(s^obs).volume());allowed=plane and v<1e-4;checks.append({'operation':op,'part':key,'offsetMm':offset,'intersectionMm3':v,'intentionalSeatingPlaneNumericalContact':bool(allowed)})
for k in rows:
 if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_')):
  obs=source(k)
  if k.startswith('gpio_pin_'):obs=(obs.transform(np.linalg.inv(piT)[:3])^mf.Manifold.cube([200,400,400]).translate([50.52,-200,-100])).transform(piT[:3])
  obs=obs.transform(Tp[:3]);test('new audio cap solids vs final Pi',added,obs,k);test('new cradle pad vs final Pi',pad,obs,k)
  for dz in np.linspace(-15,0,61):test('Pi joins preinstalled cap/audio from below',obs.translate([0,0,float(dz)]),added,k,float(dz));test('Pi joins preinstalled cap/audio from below',obs.translate([0,0,float(dz)]),amp,k,float(dz))
  del obs;gc.collect()
for k in ['jaw_support','jaw_frame','upper_pad','lower_pad','head_bottom','motor13','motor14','motor15','head_yaw_link','face_panel','camera_retainer','camera_board','eye_trim']:
 obs=load(H/'camera-ribbon-repair/positive-x225/face_three_screw_camera-world.stl') if k=='face_panel' else source(k)
 test('new audio solids vs fixed head',added,obs,k);test('new cradle pad vs fixed head',pad,obs,k);del obs;gc.collect()
for name,s in [('amplifier',amp),('speaker',speaker),('speaker_keeper',keeper),('speaker_cradle',cradle)]:
 test('final seated source mating',s,cap,name,plane=True)
 for dz in np.linspace(-15,0,61):test('prewired parts enter detached cap from below',s.translate([0,0,float(dz)]),cap,name,float(dz),plane=abs(dz)<1e-8)
for i,(x,y,z) in enumerate([(13.287000885,-12.3499993896,134.0149994),(13.287000885,.3500006104,134.0149994),(-16,7,128.44),(-16,17,127.49)]):
 tool=mf.Manifold.cylinder(25,1.5,circular_segments=32).translate([x,y,z-25]);test('mounting driver on detached cap',tool,cap,str(i))
 # The screwdriver ends at its own screw head seat, not through its own mounted PCB/cradle.
 for name,s in [('amplifier',amp),('speaker',speaker),('speaker_keeper',keeper)]:test('mounting driver neighboring parts',tool,s,str(i)+'/'+name)
hits=[q for q in checks if q['intersectionMm3']>1e-7 and not q['intentionalSeatingPlaneNumericalContact']];out={'passed':not hits,'wholeHeadAccepted':False,'physicalFitVerified':False,'checks':checks,'failures':hits,'sourceHashes':hashes,'nativeReceiptSha256':sha(N/'native-audio-readback.json'),'newCapMaterialMm3':added.volume(),'newCradleMaterialMm3':pad.volume(),'scope':'Exact added solids vs current independent Pi and fixed head; detached-cap mounting/15mm subassembly entry and four drivers. Flexible conductors and final complete head closure separate. Source-mating planar contact <1e-4mm3 only at final amp/speaker/cradle/keeper seats; no motion contact waiver.'};(N/'audio-local-assembly-check.json').write_text(json.dumps(out,indent=2));print(json.dumps({'passed':out['passed'],'checks':len(checks),'failures':hits[:20],'failureCount':len(hits)},indent=2))
