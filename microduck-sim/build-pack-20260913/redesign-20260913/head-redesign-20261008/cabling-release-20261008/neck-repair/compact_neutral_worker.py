"""Isolated bounded workers; never import the all-scene check_routes module."""
import argparse,base64,hashlib,json,math,os,sys
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent.parent;CACHE=H/'usb-access/usb-repair/robot-source-cache';OUT=D/'compact-isolated'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2)+'\n');tmp.replace(path)
def require_guard():
 if os.environ.get('MICRODUCK_BOUNDED_CAD')!='1':raise SystemExit('Root must dispatch this stage through run_bounded_cad.py.')
def verify_plan():
 p=json.loads((OUT/'plan.json').read_text())
 for s,h in p['inputHashes'].items():
  if sha(s)!=h:raise SystemExit('Input changed; regenerate isolated plan before resuming: '+s)
 return p
def plan():
 require_guard();index=json.loads((CACHE/'index.json').read_text());configPath=H/'viewer-candidate.json';config=json.loads(configPath.read_text());assert sha(index['sourceFile'])==index['sourceDataSha256']
 paths=[CACHE/'index.json',configPath,Path(index['sourceFile']),D/'compact_segments.py',D/'rolling_loop_math.py',D/'single_circle_candidate.py',D/'prepare_single_candidate.py',Path(__file__),D/'compact-segmented-candidate.json'];mapping={};removed=[];overlayRecords=[]
 for key,file in index['parts'].items():
  cached=CACHE/file;paths.append(cached);mapping[key]={'key':key,'kind':'cached-source-json','path':str(cached.resolve()),'sha256':sha(cached),'transform':None}
 def overlay(config,path,label):
  paths.append(path);changes=[]
  for declared,expected in config.get('sourceHashes',{}).items():
   dep=Path(declared);dep=dep if dep.is_absolute() else H/dep
   if not dep.exists() or sha(dep)!=expected:raise SystemExit('Stale declared overlay input: '+str(dep))
   paths.append(dep)
  for key in config.get('removedParts',[]):
   mapping.pop(key,None);removed.append({'key':key,'owner':label});changes.append(['remove',key])
  for key,file in config.get('replacementMeshes',{}).items():
   src=(H/file).resolve();paths.append(src);mapping[key]={'key':key,'kind':'stl','path':str(src),'sha256':sha(src),'transform':None};changes.append(['replace',key])
  for x in config.get('additionalParts',[]):
   src=(H/x['mesh']).resolve();paths.append(src);mapping[x['key']]={'key':x['key'],'kind':'stl','path':str(src),'sha256':sha(src),'transform':None};changes.append(['add-or-update',x['key']])
  for key,T in config.get('transforms',{}).items():
   if key in mapping:mapping[key]['transform']=T
  for key,file in config.get('diagnosticGeometry',{}).items():
   src=(H/file).resolve();paths.append(src);name=label+'__'+key;mapping[name]={'key':name,'kind':'stl','path':str(src),'sha256':sha(src),'transform':None};changes.append(['receiving-diagnostic',name])
  overlayRecords.append({'label':label,'manifest':str(path.resolve()),'sha256':sha(path),'changes':changes})
 overlay(config,configPath,'published-reference')
 local=H/'camera-ribbon-repair/local-candidate-manifest.json';current=json.loads(local.read_text());assert current['baseViewerCandidateSha256']==sha(configPath);overlay(current,local,'current-head-candidate')
 if not args.amp_manifest:raise SystemExit('Plan requires --amp-manifest with current audio replacement/additional/removed mappings. No fallback to old amplifier.')
 amp=Path(args.amp_manifest).resolve();ampData=json.loads(amp.read_text());assert 'replacementMeshes' in ampData and 'amplifier' in ampData['replacementMeshes'];overlay(ampData,amp,'current-audio-candidate')
 parts=list(mapping.values());r={'sourcePartCount':len(index['parts']),'effectiveObstacleCount':len(parts),'sourceDataSha256':index['sourceDataSha256'],'explicitRemovedParts':removed,'overlays':overlayRecords,'obstacles':parts,'expectedPairs':[{'pose':'neutral','obstacle':x['key']} for x in parts],'inputHashes':{str(p.resolve()):sha(p) for p in paths},'acceptance':False,'resourceContract':'Each guarded worker loads at most one obstacle; centerline and self-check independent. No all-scene mesh/Manifold dictionary exists.'};save(OUT/'plan.json',r);print(json.dumps({'sourceParts':len(index['parts']),'effectiveObstacles':len(parts),'planSha256':sha(OUT/'plan.json')}))
def geometry():
 require_guard();p=verify_plan();from compact_segments import geometry as make
 parts=make({});points=[];slices=[]
 for i,s in enumerate(parts):
  start=len(points);points.extend(s['points'][1 if i else 0:]);slices.append({'name':s['name'],'startIndex':max(0,start-1),'endIndex':len(points)-1,'lineSegmentIndexRangeInclusive':[max(0,start-1),len(points)-2],'lengthMm':s['lengthMm']})
 r={'planSha256':sha(OUT/'plan.json'),'points':points,'segments':slices,'lengthMm':sum(s['lengthMm'] for s in parts),'minimumCenterRadiusMm':min(s['minimumRadiusMm'] for s in parts),'diameterMm':7,'meshGenerated':False,'obstaclesLoaded':0};save(OUT/'centerline.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['points','segments']}))
def required_centerline():
 p=verify_plan();c=json.loads((OUT/'centerline.json').read_text());assert c['planSha256']==sha(OUT/'plan.json');return p,c
def self_check():
 require_guard();_,c=required_centerline()
 import numpy as np
 from scipy.spatial import cKDTree
 p=np.asarray(c['points']);p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-7]];lens=np.linalg.norm(np.diff(p,axis=0),axis=1);cum=np.r_[0,np.cumsum(lens)];mid=(p[:-1]+p[1:])/2;tree=cKDTree(mid);diam=c['diameterMm'];minimum=None;bad=[];pairsChecked=0
 def dist(a,b,c,d):
  u=b-a;v=d-c;w=a-c;uu=float(u@u);vv=float(v@v);uv=float(u@v);uw=float(u@w);vw=float(v@w);den=uu*vv-uv*uv
  def endpoint(x,p0,p1):
   direction=p1-p0;ll=float(direction@direction);t=float(np.clip(((x-p0)@direction)/ll,0,1)) if ll>1e-14 else 0.
   return float(np.linalg.norm(x-(p0+t*direction)))
  values=[endpoint(a,c,d),endpoint(b,c,d),endpoint(c,a,b),endpoint(d,a,b)]
  if den>1e-14:
   ss=(uv*vw-vv*uw)/den;tt=(uu*vw-uv*uw)/den
   if 0<=ss<=1 and 0<=tt<=1:values.append(float(np.linalg.norm((a+ss*u)-(c+tt*v))))
  return min(values)
 # Query one midpoint at a time; do not allocate the complete pair set.
 for i,center in enumerate(mid):
  neighbors=tree.query_ball_point(center,diam+float(max(lens)),return_sorted=True)
  for j in neighbors:
   if j<=i or abs((cum[i]+cum[i+1]-cum[j]-cum[j+1])/2)<=2*diam:continue
   dd=dist(p[i],p[i+1],p[j],p[j+1]);pairsChecked+=1;minimum=dd if minimum is None else min(minimum,dd)
   if dd<diam-1e-5:
    bad.append({'segments':[i,j],'centerlineDistanceMm':dd})
    if len(bad)>=20:break
  if len(bad)>=20:break
 r={'centerlineSha256':sha(OUT/'centerline.json'),'passed':not bad,'detectedCrossings':bad,'stoppedAfterFirst20Crossings':len(bad)>=20,'checkedNonlocalPairs':pairsChecked,'minimumCheckedNonlocalDistanceMm':minimum,'localArclengthExclusionMm':2*diam,'localExclusionJustification':'Exact C1 arcs/straights have minimumR9; within14mm contour separation the single continuous tube neighborhood is not a nonlocal branch crossing.','obstaclesLoaded':0,'manifoldLoaded':False};save(OUT/'self-check.json',r);print(json.dumps(r));return 0 if r['passed'] else 2
def self_pass():
 p,c=required_centerline();r=json.loads((OUT/'self-check.json').read_text());assert r['centerlineSha256']==sha(OUT/'centerline.json')
 if not r['passed']:raise SystemExit('Self-crossing candidate: no mesh or obstacle checking may run. Diagnose saved self-check first.')
 return p,c
def mesh():
 require_guard();_,c=self_pass()
 import numpy as np,trimesh
 p=np.asarray(c['points']);p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-7]];t=np.gradient(p,axis=0);t/=np.linalg.norm(t,axis=1)[:,None];n=np.array([1.,0,0])
 if abs(t[0]@n)>.9:n=np.array([0.,1,0])
 n-=t[0]*(n@t[0]);n/=np.linalg.norm(n);verts=[];sides=16;r=c['diameterMm']/2
 for point,tan in zip(p,t):
  n-=tan*(n@tan);n/=np.linalg.norm(n);b=np.cross(tan,n)
  for k in range(sides):a=2*math.pi*k/sides;verts.append(point+r*(n*math.cos(a)+b*math.sin(a)))
 faces=[]
 for i in range(len(p)-1):
  for k in range(sides):a=i*sides+k;b=i*sides+(k+1)%sides;cc=(i+1)*sides+k;d=(i+1)*sides+(k+1)%sides;faces.extend([[a,b,d],[a,d,cc]])
 for k in range(1,sides-1):faces.append([0,k+1,k]);z=(len(p)-1)*sides;faces.append([z,z+k,z+k+1])
 m=trimesh.Trimesh(verts,faces,process=True);m.fix_normals();assert m.is_watertight and m.is_volume
 dst=OUT/'receiving-world.stl';m.export(dst);save(OUT/'mesh.json',{'centerlineSha256':sha(OUT/'centerline.json'),'selfCheckSha256':sha(OUT/'self-check.json'),'meshSha256':sha(dst),'bounds':m.bounds.tolist(),'watertight':bool(m.is_watertight),'faces':len(m.faces),'obstaclesLoaded':0});print(json.dumps({'meshSha256':sha(dst),'faces':len(m.faces)}))
def obstacle(key):
 require_guard();p,c=self_pass();meta=json.loads((OUT/'mesh.json').read_text());assert meta['centerlineSha256']==sha(OUT/'centerline.json') and meta['selfCheckSha256']==sha(OUT/'self-check.json') and meta['meshSha256']==sha(OUT/'receiving-world.stl')
 item=next(x for x in p['obstacles'] if x['key']==key);assert sha(item['path'])==item['sha256'];import numpy as np,trimesh
 if item['kind']=='cached-source-json':
  a=json.loads(Path(item['path']).read_text());assert a['key']==key;m=trimesh.Trimesh(np.frombuffer(base64.b64decode(a['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(a['indexB64']),'<u4').reshape(-1,3),process=True)
 else:m=trimesh.load(item['path'],force='mesh')
 if item['transform'] is not None:m.apply_transform(item['transform'])
 box=np.asarray(meta['bounds']);other=m.bounds;disjoint=bool(np.any(box[0]>=other[1]) or np.any(other[0]>=box[1]));volume=0.;status='aabb-disjoint'
 if not disjoint:
  import manifold3d as mf
  def man(mm):return mf.Manifold(mf.Mesh(np.asarray(mm.vertices,np.float32),np.asarray(mm.faces,np.uint32)))
  cable=trimesh.load(OUT/'receiving-world.stl',force='mesh');a=man(cable);b=man(m);assert a.status()==mf.Error.NoError and b.status()==mf.Error.NoError;v=a^b;assert v.status()==mf.Error.NoError;volume=max(0.,float(v.volume()));status='native-solid-intersection'
 r={'key':key,'planSha256':sha(OUT/'plan.json'),'meshSha256':meta['meshSha256'],'obstacleSha256':item['sha256'],'intersectionMm3':volume,'passed':volume<=1e-4,'method':status,'maximumSimultaneouslyLoadedObstacles':1};save(OUT/'pairs'/(key+'.json'),r);print(json.dumps(r));return 0 if r['passed'] else 2
def summary():
 require_guard();p,c=required_centerline();planHash=sha(OUT/'plan.json');meshPath=OUT/'mesh.json';meshMeta=json.loads(meshPath.read_text()) if meshPath.exists() else {};expected=[x['obstacle'] for x in p['expectedPairs']];missing=[];stale=[];failed=[];complete=[];receipts={}
 for item in p['obstacles']:
  key=item['key'];rp=OUT/'pairs'/(key+'.json')
  if not rp.exists():missing.append(key);continue
  r=json.loads(rp.read_text());receipts[key]=sha(rp)
  if r.get('planSha256')!=planHash or r.get('meshSha256')!=meshMeta.get('meshSha256') or r.get('obstacleSha256')!=item['sha256']:stale.append(key);continue
  complete.append(key)
  if not r.get('passed',False):failed.append(key)
 sp=OUT/'self-check.json';sr=json.loads(sp.read_text()) if sp.exists() else {};selfPassed=sr.get('passed',False) and sr.get('centerlineSha256')==sha(OUT/'centerline.json');actualMesh=OUT/'receiving-world.stl';meshCurrent=bool(meshMeta and actualMesh.exists() and meshMeta.get('centerlineSha256')==sha(OUT/'centerline.json') and sp.exists() and meshMeta.get('selfCheckSha256')==sha(sp) and meshMeta.get('meshSha256')==sha(actualMesh));coverage=len(complete)==len(expected) and not missing and not stale
 result={'planSha256':planHash,'expectedPairs':p['expectedPairs'],'completedPairs':[{'pose':'neutral','obstacle':k} for k in complete],'missingPairs':missing,'stalePairs':stale,'failedPairs':failed,'coverageComplete':coverage,'selfCheckPassed':selfPassed,'meshCurrent':meshCurrent,'neutralClear':bool(coverage and selfPassed and meshCurrent and not failed),'wholeHarnessAccepted':False,'status':'complete' if coverage and selfPassed and meshCurrent else 'incomplete','receiptHashes':receipts,'rule':'Timed-out/skipped/not-run/stale records are incomplete, never inferred clear from successful subset.'};save(OUT/'summary.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['expectedPairs','completedPairs','receiptHashes']}));return 0 if result['neutralClear'] else 2
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('stage',choices=['plan','geometry','self','mesh','obstacle','summary']);a.add_argument('--key');a.add_argument('--amp-manifest');args=a.parse_args()
 if args.stage=='obstacle' and not args.key:a.error('obstacle stage requires --key')
 sys.exit(obstacle(args.key) if args.stage=='obstacle' else globals()[{'self':'self_check'}.get(args.stage,args.stage)]() or 0)
