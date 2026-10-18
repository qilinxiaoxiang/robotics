"""One camera rotation around unchanged optical axis; no frozen artifact mutation."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py');m=json.loads(read(O/'candidate-manifest.json'));base=json.loads(read(H/'viewer-candidate.json'));files=(base['replacementMeshes']|{q['key']:q['mesh'] for q in base['additionalParts']})|(m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']});cy=-.09137821197509766;cz=131.11459732055664
T=np.eye(4);T[1,1]=T[2,2]=-1;T[1,3]=2*cy;T[2,3]=2*cz
cam=load(H/files['camera_board']).transform(T[:3]);fov=load(O/'camera_fov_clamped-world.stl').transform(T[:3]);af=load(O/'camera_af_clamped-world.stl').transform(T[:3]);mouth=(T@np.r_[75.63,9.3706236,131.1145958,1])[:3];free=box([mouth[0]-.3,mouth[1]-4,mouth[2]-8],[mouth[0]+.3,mouth[1],mouth[2]+8]);keys=sorted((set(n['P'])|set(files))-set(base['removedParts'])-set(m['removedParts'])-{'camera_board','openrb'});rows=[]
for key in keys:
 q=load(H/files[key]) if key in files else n['source'](key)
 for k,s in [('camera',cam),('CSI_free4mm',free)]+([('FOV',fov),('AF',af)] if key in ['head_cap','face_panel','eye_trim'] else []):
  v,bb=n['volume'](s,q);rows.append({'moving':k,'obstacle':key,'overlapMm3':v,'boundsMm':bb,'minimumGapCapped2Mm':float(s.min_gap(q,2))})
 del q;gc.collect()
exp={'camera':export(cam,'camera_flip180'),'FOV':export(fov,'camera_flip180_fov'),'AF':export(af,'camera_flip180_af'),'CSI_free4mm':export(free,'camera_flip180_csi_free4mm')};r={'integrationReady':False,'opticalAxisPreserved':True,'rotationAboutOpticalAxisDegrees':180,'worldTransform':T.tolist(),'mouthWorldMm':mouth.tolist(),'outwardAxis':[0,-1,0],'widthAxis':[0,0,-1],'exports':exp,'checks':rows,'expectedObstacles':len(keys),'completedObstacles':len(rows)//2-3,'OpenRB':'Not evaluated in this first camera local-stage; fixed body bounds are remote, require later142-component proof','sourceHashes':n['hashes']};(O/'camera-flip180-local-probe.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'mouth':mouth.tolist(),'hits':[q for q in rows if q['overlapMm3']>1e-5],'cameraMinimums':sorted([(q['minimumGapCapped2Mm'],q['obstacle']) for q in rows if q['moving']=='camera'])[:7]},indent=2))
