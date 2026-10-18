from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
from scipy.spatial.transform import Rotation
old=D/'positive-x225';dest=D/'camera-quarter-rolls';dest.mkdir(exist_ok=True);pivot=np.array([0.,-.09137821197509766,131.11459732055664]);rows=[]
obstacles=[('native_cap',H/'curved-head/community-curved-head-world.stl'),('eye',old/'eye_three_screw_camera-world.stl'),('face',old/'face_three_screw_camera-world.stl'),('amp',H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl')]
for k in ['motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','speaker','head_bottom','upper_pad','lower_pad']:
 if k in n['P'] or k in n['files']:obstacles.append((k,None))
for kind,file in [('oldPi','candidate-manifest.json')]:
 pr=json.loads(read(old/'pi-geometry-manifest.json'));obstacles.extend((kind+'_'+r['key'],H/r['mesh']) for r in pr['parts'])
for kind,file in [('frontFlip','frontFlip-full-usb-unused-0-shift-1.0,0.0,0.0'),('backTilt','backy15-allports-adjusted-0')]:
 pr=json.loads(read(D/'occupancy-layout'/file/'report.json'));obstacles.extend((kind+'_'+r['key'],H/r['mesh']) for r in pr['parts'] if r['key']!='CSI_free4' and not r['key'].startswith('USB'))
for ang in [-90,90]:
 R=Rotation.from_euler('x',ang,degrees=True).as_matrix();T=np.column_stack([R,pivot-R@pivot]);O=dest/str(ang);O.mkdir(exist_ok=True);checks=[];parts=[]
 for key,file in [('camera','camera_board_clamped'),('AF','camera_af_clamped'),('FOV','camera_fov_clamped')]:
  s=load(old/(file+'-world.stl')).transform(T);parts.append({'key':key,'mesh':export(s,key),'boundsMm':list(s.bounding_box())})
  for k,p in obstacles:
   o=load(p) if p else n['source'](k);v,bb=n['volume'](s,o);checks.append({'part':key,'obstacle':k,'volumeMm3':v,'boundsMm':bb,'gapCapped2':float(s.min_gap(o,2))});del o
  del s;gc.collect()
 mouth=R@np.array([75.63,9.3706236,131.1145958])+T[:,3];direction=R@np.array([0.,1,0]);row={'integrationReady':False,'angleAddedAboutOpticalAxisDegrees':ang,'pivot':pivot.tolist(),'worldTransformFromCurrentCamera':T.tolist(),'mouthWorldMm':mouth.tolist(),'outward':direction.tolist(),'contactNormal':[1,0,0],'parts':parts,'checks':checks,'expectedPairs':3*len(obstacles),'completedPairs':len(checks),'sourceHashes':n['hashes'],'oldClampRetired':True,'facePegsNotRetired':True};(O/'report.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'angle':ang,'mouth':mouth.tolist(),'outward':direction.tolist(),'hits':[(x['part'],x['obstacle'],x['volumeMm3']) for x in checks if x['volumeMm3']>1e-5]},indent=2),flush=True)
