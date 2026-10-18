"""Single horizontal roof Pi architecture. No mounting changes or readiness claim."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py');m=json.loads(read(O/'pi-geometry-manifest.json'));Told=np.array(json.loads(read(D/'positive-x225-pose.json'))['worldTransform']);T=np.array([[0,-1,0,32.4886227],[0,0,-1,128.0496],[1,0,0,79.39],[0,0,0,1.]]);delta=T@np.linalg.inv(Told);new=[];O=D/'roof-layout';O.mkdir(exist_ok=True)
for row in m['parts']:
 q=load(H/row['mesh']).transform(delta[:3]);new.append({'key':row['key'],'mesh':export(q,row['key']),'boundsMm':list(q.bounding_box())})
checks=[];keys=['native_cap','motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','head_roll_ring_a','head_roll_ring_b','speaker','head_bottom','upper_pad','lower_pad'];observed=[]
for key in keys:
 if key=='native_cap':obs=load(H/'curved-head/community-curved-head-world.stl')
 elif key not in n['P'] and key not in n['files']:continue
 else:obs=n['source'](key)
 observed.append(key)
 for row in new:
  q=load(H/row['mesh']);v,bb=n['volume'](q,obs);checks.append({'part':row['key'],'obstacle':key,'overlapMm3':v,'boundsMm':bb,'minimumGapCapped2Mm':float(q.min_gap(obs,2))});del q
 del obs;gc.collect()
report={'integrationReady':False,'worldTransform':T.tolist(),'deltaFromX225':delta.tolist(),'parts':new,'checks':checks,'expectedPairs':len(new)*len(observed),'completedPairs':len(checks),'requiresNewPlacements':['OpenRB vertical negativeY','Amplifier positiveY','Pi/USB mounts'],'sourceHashes':n['hashes']};(O/'pi-roof-coarse.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'headers':[q for q in new if 'gpio' in q['key']],'hits':[q for q in checks if q['overlapMm3']>1e-5]},indent=2))
