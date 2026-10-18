from pathlib import Path
import argparse,json,hashlib,gc,sys
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;E=D.parents[1];sys.path.insert(0,str(E/'power-sensor/integrated-harness-20261009'))
from wire_geometry import solid
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(o):
 assert sha(o['file'])==o['sha256'],o['file'];m=trimesh.load_mesh(o['file'],process=True);m.apply_transform(o.get('worldTransform',np.eye(4)));return m
def overlap(a,b):return not (np.any(a[1]<b[0])or np.any(b[1]<a[0]))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--wires',action='store_true');args=ap.parse_args();plan=json.loads((D/'plan.json').read_text());top=json.loads((D.parent/'active-topology.json').read_text());parts=[]
 for key,p in plan['ports'].items():
  lo,hi=np.array(p['housingLocalBounds']);m=trimesh.creation.box(hi-lo);m.apply_translation((hi+lo)/2);m.apply_transform(p['transform']);f=D/(key+'-housing.stl');m.export(f)
  parts.append({'key':key+'-housing','port':key,'ownMotor':p['motor'],'file':str(f),'sha256':sha(f),'boundsMm':m.bounds.tolist(),'m':m,'a':solid(m)})
 if args.wires:
  routes=json.loads((D/'routes.json').read_text())
  for p in routes['parts']:
   m=load(p);parts.append({**p,'boundsMm':m.bounds.tolist(),'m':m,'a':solid(m)})
 obs=plan['obstacles'].copy()
 for motor in [11,12]:
  T=np.array(top['ports'][f'motor-{motor}-socket-13']['transform'])
  for p in plan['nativeMotorSource']:obs.append({'key':f'motor{motor}/{p["solid"]}','file':p['file'],'sha256':p['sha256'],'worldTransform':(T@np.linalg.inv(p['worldTransform'])).tolist()})
 rows=[];bounds=[];invalid=[]
 for o in obs:
  m=load(o);bounds.append({'key':o['key'],'boundsMm':m.bounds.tolist()});near=[p for p in parts if overlap(np.array(p['boundsMm']),m.bounds)]
  if not near:continue
  try:assert m.is_volume,'not closed mesh';b=solid(m)
  except Exception as ex:invalid.append({'key':o['key'],'error':str(ex),'affected':[p['key']for p in near]});continue
  for p in near:
   cut=p['a']^b;v=cut.volume();row={'part':p['key'],'obstacle':o['key'],'volumeMm3':v,'boundsMm':list(cut.bounding_box())if v>1e-7 else None}
   if v>1e-7:print(row,flush=True)
   rows.append(row)
  del b,m;gc.collect()
 pairs=[]
 for i,p in enumerate(parts):
  for q in parts[:i]:
   if not overlap(np.array(p['boundsMm']),np.array(q['boundsMm'])):continue
   cut=p['a']^q['a'];v=cut.volume();pairs.append({'a':p['key'],'b':q['key'],'volumeMm3':v,'boundsMm':list(cut.bounding_box())if v>1e-7 else None})
 result={'candidateOnly':True,'wholeHarnessAccepted':False,'parts':[{k:v for k,v in p.items()if k not in ['m','a']}for p in parts],'testedObstacleCount':len(obs),'aabbSeparatedPairCount':len(obs)*len(parts)-len(rows)-sum(len(x['affected'])for x in invalid),'exactPairs':rows,'invalidObstacles':invalid,'mutualPairs':pairs,'sourceHashes':{str(D/'plan.json'):sha(D/'plan.json'),**{o['file']:o['sha256']for o in obs}}}
 name='check-routes'if args.wires else 'check-housings';(D/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n');(D/'obstacle-bounds.json').write_text(json.dumps(bounds,indent=2)+'\n');print('done',len(rows),'exact',len(invalid),'invalid',flush=True)
if __name__=='__main__':main()
