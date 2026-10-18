from pathlib import Path
import json,sys,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;rid=sys.argv[1];m=json.loads((D/'manifest.json').read_text());r=next(x for x in json.loads((D/'routes.json').read_text())['routes']if x['id']==rid)
def solid(path,translation=None):
 x=trimesh.load_mesh(path,process=True)
 if translation is not None:x.apply_translation(translation)
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(x.vertices,dtype=np.float64),np.ascontiguousarray(x.faces,dtype=np.uint64)))
 if str(a.status())!='Error.NoError' or a.volume()<=0:raise ValueError(str(a.status()))
 return a,{'trimeshWatertight':bool(x.is_watertight),'manifoldValid':True,'volumeMm3':a.volume()}
parts=[p for p in m['parts'] if p['key'].startswith(rid+'-') or p['key'] in [f"motor-{r[k]['motor']:02}-socket-{r[k]['sourceSocket']}-housing"for k in ['from','to']]]
obstacles=[]
for f in (D/'obstacles').glob('*.json'):
 o=json.loads(f.read_text())
 if o['key']=='openrb':
  cm=D.parents[2]/'head-redesign-20261008/usb-access/usb-repair/openrb-component-enclosures/manifest.json'
  for c in json.loads(cm.read_text())['components']:
   obstacles.append({'key':f"openrb-component-{c['index']:04}",'file':c['mesh'],'sha256':c['meshSha256'],'expectedFinalBoundsMm':c['bounds'],'importTranslationMm':[0,0,0],'conservativeEnclosure':True})
 else:obstacles.append(o)
rows=[]
for p in parts:
 a,ev=solid(p['file']);bb=np.array(p['expectedFinalBoundsMm'])
 for o in obstacles:
  ob=np.array(o['expectedFinalBoundsMm']);
  if np.any(bb[1]<ob[0]) or np.any(ob[1]<bb[0]):continue
  if p['kind']=='receiving-envelope' and (o['key']==f"motor{int(p['key'].split('-')[1])}" or (p['key'].startswith('motor-00-') and o['key']=='openrb-component-0074')):
   rows.append({'part':p['key'],'obstacle':o['key'],'status':'intended-own-socket-mating-not-tested-with-coarse-housing-box'});continue
  try:
   b,oe=solid(o['file'],o.get('importTranslationMm',[0,0,0]));cut=a^b;assert str(cut.status())=='Error.NoError';v=cut.volume()
   rows.append({'part':p['key'],'movingSha256':p['sha256'],'obstacle':o['key'],'conservativeObstacle':o.get('conservativeEnclosure',False),'overlapMm3':v,'intersectionBoundsMm':list(cut.bounding_box())if v>1e-6 else None,'obstacleEvidence':oe,'obstacleSourceSha256':o['sha256'],'translationMm':o.get('importTranslationMm',[0,0,0])})
  except Exception as e:rows.append({'part':p['key'],'obstacle':o['key'],'status':'invalid-input-unresolved','error':str(e)})
 output={'route':rid,'routeFileSha256':hashlib.sha256((D/'routes.json').read_bytes()).hexdigest(),'rows':rows,'candidateOnly':True}
 (D/(rid+'-static.json')).write_text(json.dumps(output,indent=2))
print(rid,[(x['part'],x['obstacle'],round(x.get('overlapMm3',0),3))for x in rows if x.get('overlapMm3',0)>1e-6], 'unresolved',sum(x.get('status')=='invalid-input-unresolved'for x in rows))
