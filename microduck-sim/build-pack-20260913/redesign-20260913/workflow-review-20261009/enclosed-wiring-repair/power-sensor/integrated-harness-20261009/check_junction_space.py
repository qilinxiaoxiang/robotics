"""One deliberate paired splice location; no search and no acceptance of unknown stock."""
from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent; N=D.parent; W=N.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,dtype=np.float64),np.asarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError
 return s
manifest=W/'original-body-converter/fusion-import-manifest.json';j=json.loads(manifest.read_text())
obs=j['parts']+[{'key':'imu_clamp','file':str(N/'imu-clamp-retained-world.stl'),'importTranslationMm':[0,0,0]},{'key':'imu_cover','file':str(N/'imu-cover-retained-world.stl'),'importTranslationMm':[0,0,0]}]
rows=[];parts=[];hashes={str(manifest):sha(manifest),str(Path(__file__)):sha(Path(__file__))}
for key,y in [('distribution_5v',-7),('distribution_gnd',7)]:
 m=trimesh.creation.cylinder(radius=3,height=12,sections=48);m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));m.apply_translation([-7,y,35.5]);a=solid(m)
 f=D/(key+'-receiving-world.stl');m.export(f)
 parts.append({'key':key,'file':str(f),'sha256':sha(f),'center':[-7,y,35.5],'axis':[1,0,0],'diameterMm':6,'lengthMm':12,'geometryKind':'Engineering receiving envelope for an insulated soldered splice; not a purchased connector or proven solder process'})
 for q in obs:
  b=q.get('expectedFinalBoundsMm');r={'splice':key,'obstacle':q['key']}
  if b is not None and (np.any(m.bounds[1]<np.array(b)[0]) or np.any(np.array(b)[1]<m.bounds[0])):r['status']='BOUNDS_SEPARATE'
  else:
   p=Path(q['file']);hashes[str(p)]=sha(p);n=trimesh.load(p,force='mesh');n.apply_translation(q.get('importTranslationMm',[0,0,0]))
   if np.any(m.bounds[1]<n.bounds[0]) or np.any(n.bounds[1]<m.bounds[0]):r['status']='BOUNDS_SEPARATE'
   else:
    try:bsolid=solid(n)
    except AssertionError:
     bsolid=solid(n.convex_hull);r['conservativeObstacle']=True
    c=a^bsolid;v=c.volume();r.update(status='CLEAR' if c.is_empty() else 'INTERSECTION',volumeMm3=v,boundsMm=None if c.is_empty() else list(c.bounding_box()))
   del n
  rows.append(r)
fail=[x for x in rows if x['status']=='INTERSECTION']
out={'status':'SPACE_ONLY_NO_ELECTRICAL_OR_ASSEMBLY_ACCEPTANCE','complete':len(rows)==2*len(obs),'expectedPairs':2*len(obs),'checkedPairs':len(rows),'spaceClear':not fail,'parts':parts,'rows':rows,'failures':fail,'sourceHashes':hashes,'wholeHarnessAccepted':False}
(D/'junction-space.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'checked':len(rows),'failures':fail}))
