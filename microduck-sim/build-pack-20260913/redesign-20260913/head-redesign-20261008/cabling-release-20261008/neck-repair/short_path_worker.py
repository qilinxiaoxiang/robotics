"""One guarded stage / one obstacle. Never loads complete scene solids."""
import argparse,base64,hashlib,json,math,os,sys,itertools
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent.parent;OUT=D/'short-isolated';CACHE=H/'usb-access/usb-repair/robot-source-cache'
KEYS=['power_support','neck_link_a','neck_link_b','neck_pitch','neck_pitch_ring','head_yaw_link','motor11','motor12','motor13','motor14','shell_left','shell_right','torso_base','imu_clamp','imu_board']
POSES=[-1,68,136,148,167,208]
BODIES={'trunk_base':0,'neck':1,'neck_pitch':2,'yaw_roll_motion':3,'jaw_soft':4}
ORDER=['neck_pitch','head_pitch','head_yaw','head_roll']
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,indent=2)+'\n');tmp.replace(p)
def guard():
 if os.environ.get('MICRODUCK_BOUNDED_CAD')!='1':raise SystemExit('Use run_bounded_cad.py --wait-lock-seconds30 --max-mib512 --seconds120')
def inputs():
 return [D/x for x in ['short_path_worker.py','prepare_short_selected.py','finite_anchor_screen.py','short_continuous_family.py','single_circle_candidate.py','prepare_single_candidate.py','check_local_pair_stdlib.py','compact_segments.py','rolling_loop_math.py']]+[H/'usb-access/usb-repair/rigid-domain.json',CACHE/'index.json']
def plan():
 index=json.loads((CACHE/'index.json').read_text());assert sha(index['sourceFile'])==index['sourceDataSha256'];paths=inputs()+[Path(index['sourceFile'])];obstacles=[]
 for key in KEYS:
  p=CACHE/index['parts'][key];d=json.loads(p.read_text());assert d['key']==key and d['body'] in BODIES;paths.append(p);obstacles.append({'key':key,'body':d['body'],'path':str(p.resolve()),'sha256':sha(p)})
 overlays=[]
 for name in ['camera-ribbon-repair/local-candidate-manifest.json','gpio-audio-repair/amp16z2-current-overlay.json']:
  p=H/name;d=json.loads(p.read_text());stale=[]
  for dep,h in d.get('sourceHashes',{}).items():
   pp=Path(dep);pp=pp if pp.is_absolute() else H/pp
   if not pp.exists() or sha(pp)!=h:stale.append(str(pp))
  overlays.append({'file':name,'sha256':sha(p),'declaredDependenciesCurrent':not stale,'staleDependencies':stale,'appliedToThisSourceOnlySubset':False})
 r={'accepted':False,'stageScope':'Source neck/torso/motor obstacles only. No current head cap/electronic fit claim.','currentHeadState':'Amp+16X/+2Z overlay is diagnostic; lowered camera manifest cap retains old amp posts pending unified cap replay. These are recorded, not final obstacles. Original curved cap must be checked separately when unified; it has not been deleted or passed here.','sourceDataSha256':index['sourceDataSha256'],'inputHashes':{str(p.resolve()):sha(p) for p in paths},'headOverlaysReference':overlays,'obstacles':obstacles,'expectedSelfIndices':list(range(229)),'expectedPairs':[{'pose':i,'obstacle':k} for i in POSES for k in KEYS]};save(OUT/'plan.json',r);print(json.dumps({'planHash':sha(OUT/'plan.json'),'expectedSelf':229,'expectedPairs':len(r['expectedPairs']),'scope':r['stageScope']}))
def current():
 p=json.loads((OUT/'plan.json').read_text())
 for name,h in p['inputHashes'].items():
  if sha(name)!=h:raise RuntimeError('Stale input '+name)
 return p

def geom(i):
 from prepare_short_selected import path,B,U,L
 base=json.loads((H/'usb-access/usb-repair/rigid-domain.json').read_text());row={'jointDegrees':{},'nativeShellOriginalBottomIntersectionsMm3':{}} if i==-1 else base['samples'][i]
 g=path(row['jointDegrees'],B,U,L);assert g is not None
 return row,g

def self_one(points):
 from check_local_pair_stdlib import dist
 from prepare_single_candidate import norm,sub
 clean=[points[0]]
 for p in points[1:]:
  if norm(sub(p,clean[-1]))>1e-8:clean.append(p)
 seg=list(zip(clean,clean[1:]));cum=[0.]
 for a,b in seg:cum.append(cum[-1]+norm(sub(b,a)))
 threshold=7+2*(9-math.sqrt(81-.25**2));cell=threshold+.5;grid={};mids=[]
 for i,(a,b) in enumerate(seg):
  mid=[(a[k]+b[k])/2 for k in range(3)];ix=tuple(math.floor(x/cell) for x in mid);mids.append(ix);grid.setdefault(ix,[]).append(i)
 checked=0;bad=[]
 for i,(a,b) in enumerate(seg):
  for offset in itertools.product([-1,0,1],repeat=3):
   ix=tuple(mids[i][k]+offset[k] for k in range(3))
   for j in grid.get(ix,[]):
    if j<=i or cum[j]-cum[i+1]<=14:continue
    c,d=seg[j]
    if any(max(min(a[k],b[k]),min(c[k],d[k]))-min(max(a[k],b[k]),max(c[k],d[k]))>=threshold for k in range(3)):continue
    checked+=1;dd=dist(a,b,c,d)
    if dd<threshold:
     bad.append({'segments':[i,j],'centerDistanceMm':dd})
     if len(bad)==20:return {'passed':False,'failures':bad,'truncated':True,'exactDistancePairs':checked,'thresholdMm':threshold}
 return {'passed':not bad,'failures':bad,'truncated':False,'exactDistancePairs':checked,'thresholdMm':threshold}
def self_all():
 p=current();ph=sha(OUT/'plan.json');done=[]
 for i in p['expectedSelfIndices']:
  row,g=geom(i);r=self_one(g['points']);rec={'pose':i,'planHash':ph,'nativeBaselineBlocked':bool(row['nativeShellOriginalBottomIntersectionsMm3']),'jointDegrees':row['jointDegrees'],**r};save(OUT/'self'/f'{i}.json',rec);done.append(rec)
  if not r['passed']:
   save(OUT/'self-summary.json',{'planHash':ph,'passed':False,'expected':229,'completed':len(done),'coverageComplete':False,'failedIndex':i,'firstFailure':rec});print(json.dumps({'failedIndex':i,'completed':len(done),'nativeBlocked':rec['nativeBaselineBlocked'],'first':r['failures'][0]}));return 2
 r={'planHash':ph,'passed':True,'expected':229,'completed':len(done),'coverageComplete':True,'nativeClearCount':sum(not x['nativeBaselineBlocked'] for x in done),'nativeBlockedCount':sum(x['nativeBaselineBlocked'] for x in done),'scope':'All229 sampled curves; no continuous angular or solid obstacle acceptance.','receiptHashes':{str(x['pose']):sha(OUT/'self'/f'{x["pose"]}.json') for x in done}};save(OUT/'self-summary.json',r);print(json.dumps({k:v for k,v in r.items() if k!='receiptHashes'}))
def passed_self():
 current();s=json.loads((OUT/'self-summary.json').read_text());assert s['planHash']==sha(OUT/'plan.json') and s['passed'] and s['coverageComplete'];return s

def mesh(i):
 passed_self();row,g=geom(i);sr=self_one(g['points']);assert sr['passed'];import numpy as np,trimesh,manifold3d as mf
 points=np.asarray(g['points']);points=points[np.r_[True,np.linalg.norm(np.diff(points,axis=0),axis=1)>1e-8]];t=np.gradient(points,axis=0);t/=np.linalg.norm(t,axis=1)[:,None];n=np.array([1.,0,0]);n-=t[0]*(n@t[0])
 if np.linalg.norm(n)<.1:n=np.array([0.,1,0]);n-=t[0]*(n@t[0])
 n/=np.linalg.norm(n);sides=24;radius=(3.5+(9-math.sqrt(81-.25**2)))/math.cos(math.pi/sides);v=[];f=[]
 for point,tan in zip(points,t):
  n-=tan*(n@tan);n/=np.linalg.norm(n);b=np.cross(tan,n)
  for k in range(sides):angle=2*math.pi*k/sides;v.append(point+radius*(n*math.cos(angle)+b*math.sin(angle)))
 for i0 in range(len(points)-1):
  for k in range(sides):a=i0*sides+k;b=i0*sides+(k+1)%sides;c=(i0+1)*sides+k;d=(i0+1)*sides+(k+1)%sides;f.extend([[a,b,d],[a,d,c]])
 for k in range(1,sides-1):f.append([0,k+1,k]);z=(len(points)-1)*sides;f.append([z,z+k,z+k+1])
 m=trimesh.Trimesh(v,f,process=True);m.fix_normals();assert m.is_watertight and m.is_volume;dst=OUT/'meshes'/f'{i}.stl';dst.parent.mkdir(exist_ok=True);m.export(dst);del m
 m=trimesh.load(dst,force='mesh');assert m.is_watertight and m.is_volume and len(m.split())==1;a=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert a.status()==mf.Error.NoError and a.volume()>0
 meta={'pose':i,'planHash':sha(OUT/'plan.json'),'selfSummaryHash':sha(OUT/'self-summary.json'),'sha256':sha(dst),'bounds':m.bounds.tolist(),'watertightReadback':True,'positiveVolumeReadback':True,'manifoldStatus':'NoError','receiverODMm':7,'circumscribedMeshRadiusMm':radius,'jointDegrees':row['jointDegrees'],'nativeBaselineBlocked':bool(row['nativeShellOriginalBottomIntersectionsMm3'])};save(dst.with_suffix('.json'),meta);print(json.dumps(meta))
def obstacle(i,key):
 p=current();passed_self();item=next(x for x in p['obstacles'] if x['key']==key);dst=OUT/'meshes'/f'{i}.stl';meta=json.loads(dst.with_suffix('.json').read_text());assert meta['planHash']==sha(OUT/'plan.json') and meta['selfSummaryHash']==sha(OUT/'self-summary.json') and meta['sha256']==sha(dst);assert sha(item['path'])==item['sha256'];import numpy as np,trimesh,manifold3d as mf
 from prepare_single_candidate import moved
 d=json.loads(Path(item['path']).read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True)
 sourceValidation={'originalWatertight':bool(m.is_watertight),'originalPositiveVolume':bool(m.is_volume),'topologyNormalization':False}
 if not (m.is_watertight and m.is_volume):
  original=m;native=mf.Manifold(mf.Mesh(np.asarray(original.vertices,np.float32),np.asarray(original.faces,np.uint32)));assert native.status()==mf.Error.NoError and native.volume()>0
  converted=native.to_mesh();m=trimesh.Trimesh(converted.vert_properties[:,:3],converted.tri_verts,process=False)
  def triangle_digest(mm):
   triangles=np.ascontiguousarray(mm.vertices[mm.faces],dtype=np.float32);vertices=np.sort(triangles.view('V12').reshape(-1,3),axis=1);triangles=np.sort(vertices.view('V36').reshape(-1));return hashlib.sha256(triangles.tobytes()).hexdigest()
  digest=triangle_digest(original);assert digest==triangle_digest(m) and np.array_equal(m.bounds,original.bounds) and abs(m.volume-original.volume)<1e-7
  assert m.is_watertight and m.is_volume
  normpath=OUT/'normalized-inputs'/f'{key}.ply';normpath.parent.mkdir(exist_ok=True);m.export(normpath);read=trimesh.load(normpath,force='mesh',process=False)
  assert read.is_watertight and read.is_volume and triangle_digest(read)==digest
  sourceValidation.update(topologyNormalization=True,rule='Only split coincident contact vertices. Complete triangle coordinate multiset identical; no triangle added, removed or moved.',triangleMultisetSha256=digest,normalizedInputSha256=sha(normpath),readbackWatertight=True,readbackPositiveVolume=True)
  m=read;del original,native,converted
 assert m.is_watertight and m.is_volume
 q={k:meta['jointDegrees'].get(k,0) for k in ORDER[:BODIES[d['body']]]};origin=np.array(moved([0,0,0],q));R=np.array([moved(x,q,True) for x in [[1,0,0],[0,1,0],[0,0,1]]]).T;T=np.eye(4);T[:3,:3]=R;T[:3,3]=origin;m.apply_transform(T)
 def solid(mm):
  a=mf.Manifold(mf.Mesh(np.asarray(mm.vertices,np.float32),np.asarray(mm.faces,np.uint32)));assert a.status()==mf.Error.NoError and a.volume()>0;return a
 b=solid(m);other=m.bounds;box=np.array(meta['bounds']);disjoint=bool(np.any(box[0]>=other[1]) or np.any(other[0]>=box[1]));volume=0.;method='valid-solid-aabb-disjoint';bounds=None
 if not disjoint:
  cable=trimesh.load(dst,force='mesh');assert cable.is_watertight and cable.is_volume;a=solid(cable);v=a^b;assert v.status()==mf.Error.NoError;volume=float(v.volume());assert volume>=0;method='valid-solid-boolean';bounds=list(v.bounding_box()) if volume>0 else None
 r={'pose':i,'key':key,'planHash':sha(OUT/'plan.json'),'obstacleSha256':item['sha256'],'receivingSha256':meta['sha256'],'nativeBaselineBlocked':meta['nativeBaselineBlocked'],'jointDegrees':meta['jointDegrees'],'body':d['body'],'bodyTransform':T.tolist(),'intersectionMm3':volume,'intersectionBounds':bounds,'passed':volume<=1e-8,'method':method,'inputObstacleWatertight':True,'inputObstacleVolumePositive':True,'booleanStatus':'NoError' if not disjoint else 'not-required','maximumLoadedObstacleCount':1,'sourceValidation':sourceValidation};save(OUT/'pairs'/f'{i}__{key}.json',r);print(json.dumps(r));return 0 if r['passed'] else 2
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['plan','self','mesh','obstacle']);ap.add_argument('--pose',type=int,default=-1);ap.add_argument('--key');opt=ap.parse_args();guard();sys.exit(plan() if opt.stage=='plan' else self_all() if opt.stage=='self' else mesh(opt.pose) if opt.stage=='mesh' else obstacle(opt.pose,opt.key))
