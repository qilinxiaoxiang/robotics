from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py');r=json.loads(read(O/'camera-throat-subtractive-overlay.json'));out=[]
for key,xs in [('face_panel',[80.3,80.75,81.2]),('eye_trim',[81.6,82.5,83.5])]:
 mesh=tm.load(H/r['replacementMeshes'][key],force='mesh');rows=[]
 for x in xs:
  a=np.arange(128)*2*np.pi/128;orig=np.tile([x,-.09137821197509766,131.11459922790527],(len(a),1));directions=np.c_[np.zeros(len(a)),np.cos(a),np.sin(a)];loc,ray,_=mesh.ray.intersects_location(orig,directions,multiple_hits=True)
  for i in range(len(a)):
   v=np.sort(np.linalg.norm(loc[ray==i]-orig[i],axis=1));v=v[np.r_[True,np.diff(v)>1e-5]] if len(v) else v
   rows.append({'x':x,'angleDegrees':float(a[i]*180/np.pi),'intersectionsMm':v.tolist(),'firstContinuousWallMm':float(v[1]-v[0]) if len(v)>=2 else None})
 valid=[q for q in rows if q['firstContinuousWallMm'] is not None];out.append({'part':key,'expectedRays':len(a)*len(xs),'completedRays':len(rows),'minimumSampledContinuousWallMm':min(q['firstContinuousWallMm'] for q in valid),'missingTwoBoundaryRays':len(rows)-len(valid),'minimumRow':min(valid,key=lambda q:q['firstContinuousWallMm']),'method':'128 radial rays in each of three X sections; first inner-to-outer material interval, not global wall-thickness proof'})
report={'parts':out,'sourceHashes':n['hashes'],'physicalStrengthVerified':False};(O/'camera-throat-wall-samples.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(out,indent=2))
