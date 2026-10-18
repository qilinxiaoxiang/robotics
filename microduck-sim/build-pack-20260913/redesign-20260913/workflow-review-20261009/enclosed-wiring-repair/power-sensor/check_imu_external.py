from pathlib import Path
import hashlib,json
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(mesh):
 assert mesh.is_volume
 m=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
 assert m.status()==mf.Error.NoError and m.volume()>0
 return m
mp=W/'original-body-converter/fusion-import-manifest.json';lp=D/'imu-local-manifest.json'
j=json.loads(mp.read_text());local=json.loads(lp.read_text());p=next(p for p in local['parts'] if p['key']=='imu_cover')
assert sha(p['meshFile'])==p['meshSha256']
a=trimesh.load(p['meshFile'],force='mesh');ma=solid(a);swept=a.bounds.copy();swept[0,0]-=20
excluded=['imu_clamp','imu_cover','imu_board'];obs=[p for p in j['parts'] if p['key'] not in excluded]
rows=[];hashes={str(mp):sha(mp),str(lp):sha(lp),str(Path(__file__)):sha(__file__),p['meshFile']:sha(p['meshFile'])}
for p in obs:
 assert sha(p['file'])==p['sha256'],p['key']
 b=trimesh.load(p['file'],force='mesh');b.apply_translation(p.get('importTranslationMm',[0,0,0]));bounds=b.bounds
 assert np.max(np.abs(bounds-np.asarray(p['expectedFinalBoundsMm'])))<.001,p['key']
 gap=float(np.linalg.norm(np.maximum(np.maximum(swept[0]-bounds[1],bounds[0]-swept[1]),0)))
 row={'key':p['key'],'sourceSha256':p['sha256'],'actualBoundsMm':bounds.tolist(),'continuousSweptAabbGapMm':gap}
 if gap>0:row.update(status='CONTINUOUS_BOUNDS_SEPARATE',poseCoverage=101)
 else:
  mb=solid(b);volumes=[];gaps=[]
  for x in np.linspace(-20,0,101):
   moved=ma.translate((float(x),0,0));c=moved^mb
   assert c.status()==mf.Error.NoError
   volumes.append(float(c.volume()));gaps.append(float(moved.min_gap(mb,3)))
  row.update(status='CLEAR' if max(volumes)<1e-8 else 'INTERSECTION',poseCoverage=101,maxIntersectionMm3=max(volumes),minimumSampledGapWithin3mm=min(gaps),finalGapWithin3mm=gaps[-1],gapSearchClippedMm=3,continuousGapLowerBoundMm=max(0,min(gaps)-.1),sampleSpacingMm=.2)
 rows.append(row)
out={'scope':'Frozen populated IMU rear-cover including integral tie land, against all external original-body reference parts; neutral robot, final and existing -X20mm closure path. Internal IMU installation remains separately bound to941-check receipt.','expectedObstacleKeys':[p['key'] for p in obs],'excludedLocalAlreadyCheckedKeys':excluded,'expectedChecks':len(obs)*101,'completedChecks':sum(r['poseCoverage'] for r in rows),'complete':len(rows)==len(obs),'passed':all(r['status'] in ['CLEAR','CONTINUOUS_BOUNDS_SEPARATE'] for r in rows),'rows':rows,'sourceHashes':hashes,'geometryChanged':False,'jointMotionVerified':False,'physicalFitVerified':False}
(D/'imu-external-clearance.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['rows','sourceHashes','expectedObstacleKeys']}));print(json.dumps([r for r in rows if r['status']!='CONTINUOUS_BOUNDS_SEPARATE']))
