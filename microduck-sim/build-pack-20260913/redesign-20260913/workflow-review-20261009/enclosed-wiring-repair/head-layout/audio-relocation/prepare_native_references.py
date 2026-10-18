from pathlib import Path
O=Path(__file__).resolve().parent
exec((O/'check_one_pose.py').read_text().split('Tp=')[0])
E=O/'reference-meshes';E.mkdir(exist_ok=True)
Tp=np.array(read(D/'pi-front-up05-pose.json')['piCurrentWorldDelta']);piT=np.array(read(H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json')['worldTransform'])
refs=[]
for k,row in rows.items():
 if not(k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_'))):continue
 path=Path(row['file']);T=Tp.copy();T[:3,3]+=Tp[:3,:3]@np.array(row.get('importTranslationMm',[0,0,0]))
 if k.startswith('gpio_pin_'):
  s=(source(k).transform(np.linalg.inv(piT)[:3])^mf.Manifold.cube([200,400,400]).translate([50.52,-200,-100])).transform(piT[:3]);path=E/(k+'-16p79.stl');pm.export(ctx,s,path);T=Tp.copy()
 refs.append({'name':'REFERENCE Pi current '+k,'file':str(path),'sha256':sha(path),'worldTransform':T.tolist(),'role':'16.79mm individual female class hardware bound'if k.startswith('gpio_pin_')else'Independent current Pi source part'})
s=mf.Manifold.cube([6,13,25]).translate([63.01,2.4,146.0496]).transform(piT[:3]).transform(Tp[:3]);p=E/'microB-current-photo-receiving.stl';pm.export(ctx,s,p);refs.append({'name':'REFERENCE MicroB photo receiving','file':str(p),'sha256':sha(p),'worldTransform':np.eye(4).tolist(),'role':'Photo13x6mm section,25mm axial bound; EDAC1.30mm datum, not measured mould'})
# Only new cradle seat material and changed M2.5x8 screw are tested here.
pad=(mf.Manifold.cylinder(.951,2.6,circular_segments=64)-mf.Manifold.cylinder(1.1,1.4,circular_segments=64).translate([0,0,-.05])).translate([-16,17,127.49]);cradle=source('speaker_cradle');changed=cradle+pad
assert len(changed.decompose())==1
p=E/'speaker-cradle-single-seat-adjustment-world.stl';pm.export(ctx,changed,p)
shaft=mf.Manifold.cylinder(8,1.25,circular_segments=48).translate([-16,17,127.49]);head=mf.Manifold.cylinder(1.7,2.5,circular_segments=48).translate([-16,17,125.79])
check=[]
for k in ['head_cap','jaw_support','jaw_frame','upper_pad','lower_pad','head_bottom','motor13','motor14','motor15','head_yaw_link','face_panel','camera_retainer','camera_board','eye_trim','speaker','speaker_keeper']:
 obs=load(D/'pi-roof-mounts/closed-cap-with-pi-bosses-world.stl') if k=='head_cap' else source(k)
 for name,s in [('newSeatOnly',pad),('changedScrewShaft',shaft),('changedScrewHead',head)]:
  v=max(0,(s^obs).volume());check.append({'moving':name,'fixed':k,'volumeMm3':v})
 del obs;gc.collect()
r={'references':refs,'sourceHashes':hashes,'seatPadBoundsMm':list(pad.bounding_box()),'seatAdditionMm':.95,'actualScrewEntryMm':2.04,'screwTipZMm':135.49,'pilotEndZMm':135.8,'clearanceToBlindEndMm':.31,'changedCradle':{'file':str(p),'sha256':sha(p),'original':rows['speaker_cradle']['file']},'checks':check,'passed':all(x['volumeMm3']<1e-7 for x in check),'hits':[x for x in check if x['volumeMm3']>=1e-7]};(O/'native-reference-preparation.json').write_text(json.dumps(r,indent=2));print(json.dumps({'refs':len(refs),'seatCheckPassed':r['passed'],'hits':r['hits']}))
