exec((__import__('pathlib').Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/curved-head/finalize_cap.py')).read_text().split('cap=load(')[0].replace('D=Path(__file__).resolve().parent',"D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/curved-head')"))
piMesh=tri(dec('pi'));center=piMesh.bounds.mean(0);R=trimesh.transformations.rotation_matrix(np.pi,[1,0,0],center)
moving={'pi':dec('pi')}
for k in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails','zero_w_usb_moulding','zero_w_csi_latch_exit']:moving[k]=load(D/(k+'-world.stl'))
exclude={'pi','head_cap','camera_pitch_foot','camera_cradle','camera_board','camera_ribbon','face_panel','eye_trim','openrb','amplifier','speaker','audio_carrier'}
fixed={k:dec(k) for k,p in P.items() if k not in exclude and not str(p.get('fastenerId','')).startswith(('E-camera_','E-openrb-','E-audio'))}
for k,f in [('face_panel','camera-retainer/face-with-camera-anchors-world.stl'),('camera_board','camera-retainer/camera-shifted-reference-world.stl'),('camera_retainer','camera-retainer/camera-retainer-world.stl'),('camera_hardware','camera-retainer/camera-all-six-screw-envelopes-world.stl'),('eye_trim','eye-trim-camera-clearance-world.stl')]:fixed[k]=load(V/f)
for k,f in [('head_cap','curved-cap-final-candidate-world.stl'),('openrb','openrb-curved-layout-world.stl'),('amplifier','amplifier-curved-layout-world.stl'),('speaker','speaker-curved-layout-world.stl'),('speaker_cradle','speaker-cradle-world.stl'),('speaker_keeper','speaker-keeper-world.stl'),('cap_hardware','cap-eight-screw-heads-four-nuts-world.stl')]:fixed[k]=load(D/f)
rows=[]
for dx in range(6):
 T=R.copy();T[0,3]+=dx;hh={};bounds={}
 for k,m in moving.items():
  q=m.transform(T[:3,:]);bounds[k]=np.array(q.bounding_box()).reshape(2,3).tolist()
  for n,o in fixed.items():
   v=hits(q,o)
   if v>1e-4:hh[k+'--'+n]=v
 rows.append({'flipAxis':'worldX','centerMm':center.tolist(),'additionalXmm':dx,'transform':T.tolist(),'intersectionsMm3':hh,'receivingBoundsMm':bounds});print(json.dumps({'dx':dx,'hits':hh,'usbBounds':bounds['zero_w_usb_moulding']}),flush=True)
Path('/tmp/pi-flip-independent.json').write_text(json.dumps({'status':'finite-static-variant-review','scope':'Original board center, normal-axis180rotation, plusX0..5mm. Existing camera pose unchanged. USB/CSI proxy dimensions retain their explicit unmeasured receiving-envelope limitation.','cases':rows,'sourceCapHash':hashlib.sha256((D/'curved-cap-final-candidate-world.stl').read_bytes()).hexdigest()},indent=2))
