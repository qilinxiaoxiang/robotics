from pathlib import Path
import json,base64,hashlib
import numpy as np,trimesh
D=Path(__file__).resolve().parent;R=D.parents[1];P=R/'leg-guide-20261006/full-build-data.json';data=json.loads(P.read_text());p=next(x for x in data['parts'] if x['key']=='motor7');v=np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3);m=trimesh.Trimesh(v,f,process=False)
S=np.array([[0,0,-1,-8],[-1,0,0,0],[0,1,0,0],[0,0,0,1]]);T=np.array(p['sourceTransformWorld'])@S
native=json.loads((D/'motor-step-solids.json').read_text());points=[];labels=[]
for i in [13,14]:
 for j in [4,12,28,33,38,39,40,45,50,55]:
  face=native['solids'][i]['faces'][j];points.append(face['center']);labels.append(f'header{i}-face{j}')
points=(np.c_[points,np.ones(len(points))]@T.T)[:,:3]
nearest,dist,tri=trimesh.proximity.closest_point(m,points)
rows=[{'sourceFeature':k,'worldPointMm':q.tolist(),'nearestGuideTriangle':int(t),'distanceMm':float(d)}for k,q,t,d in zip(labels,points,tri,dist)]
out={'sourceDataSha256':hashlib.sha256(P.read_bytes()).hexdigest(),'method':'20 manufacturer planar-face centroids projected onto the actual installed motor7 source mesh; surface registration, not solid intersection.','maximumDistanceMm':float(max(dist)),'rows':rows,'passedWithin0_03mm':bool(max(dist)<.03)};out['portMouthAndPinWitnesses']=[r for r in rows if any(r['sourceFeature'].endswith('-face'+str(i)) for i in [12,28,33,38])];out['portWitnessMaximumDistanceMm']=max(r['distanceMm'] for r in out['portMouthAndPinWitnesses']);out['portRegistrationPassedWithin0_005mm']=out['portWitnessMaximumDistanceMm']<.005;out['wholeSurfaceCentroidScreenPassed']=out['passedWithin0_03mm'];(D/'mesh-registration-check.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))
