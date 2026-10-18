"""ROOT-only bounded CAD gate for the single prepared side-U family.

No optimizer. Each completed pose is flushed and fsynced. This gate tests ONLY
its explicit external segment, never promotes it to a full harness acceptance.
"""
import os,sys,json,math,hashlib,ast,gc
from pathlib import Path
N=Path(__file__).resolve().parent
if os.environ.get('MICRODUCK_BOUNDED_CAD')!='1':raise SystemExit('Root must dispatch through run_bounded_cad.py under the sole CAD token.')
sys.path.insert(0,str(N.parent));from check_routes import *
from single_circle_candidate import candidate,A,B
from scipy.spatial import cKDTree
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,default=0);ap.add_argument('--end',type=int,default=229);ap.add_argument('--neutral-first',action='store_true');ap.add_argument('--output',default='single-circle-collision.jsonl');opt=ap.parse_args()
prepPath=N/'single-circle-candidate.json';prep=json.loads(read(prepPath));basePath=H/'usb-access/usb-repair/rigid-domain.json';base=json.loads(read(basePath));target=prep['constantFlexibleLengthMm'];assert len(base['samples'])==229
SIM=H.parent.parents[1];fkPath=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py';sys.path.insert(0,str(fkPath.parent));from assembly_fk import fk
zero,_=fk();inv={k:np.linalg.inv(v) for k,v in zero.items()};body={p['key']:p.get('body','jaw_soft') for p in data['parts']}
for k in obs:body.setdefault(k,'jaw_soft')
body={k:b if b in zero else 'trunk_base' for k,b in body.items()}
for node in ast.parse((H/'usb-access/full-harness/build_harness.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name=='tube':exec(compile(ast.Module(body=[node],type_ignores=[]),'<tube>','exec'))
ptail=np.array([1e9]*3)
def closest_segment(a,b,c,d):
 u=b-a;v=d-c;w=a-c;uu=float(u@u);vv=float(v@v);uv=float(u@v);uw=float(u@w);vw=float(v@w);den=uu*vv-uv*uv
 s=np.clip((uv*vw-vv*uw)/den,0,1) if den>1e-14 else 0.;t=np.clip((uv*s+vw)/vv,0,1) if vv>1e-14 else 0.;s=np.clip((uv*t-uw)/uu,0,1) if uu>1e-14 else 0.
 return float(np.linalg.norm((a+s*u)-(c+t*v)))
def self_check(p,diam=7):
 lens=np.linalg.norm(np.diff(p,axis=0),axis=1);cum=np.r_[0,np.cumsum(lens)];mid=(p[:-1]+p[1:])/2;tree=cKDTree(mid);pairs=tree.query_pairs(diam+float(max(lens)),output_type='ndarray');minimum=None;bad=[]
 for i,j in pairs:
  # C1 exact circular/straight family, Rmin>=4.336; a local14mm neighborhood
  # is one continuous tube rather than a crossing of nonadjacent stretches.
  # Report this exclusion explicitly and never use it as a broad pair waiver.
  if abs((cum[i]+cum[i+1]-cum[j]-cum[j+1])/2)<=2*diam:continue
  gap=closest_segment(p[i],p[i+1],p[j],p[j+1]);minimum=gap if minimum is None else min(minimum,gap)
  if gap<diam-1e-5:bad.append({'segments':[int(i),int(j)],'centerlineDistanceMm':gap})
 return {'minimumCheckedNonlocalDistanceMm':minimum,'candidatePairs':len(pairs),'localArclengthExclusionMm':2*diam,'crossings':bad[:20],'crossingCount':len(bad)}
output=N/opt.output
if output.exists():
 prior=[json.loads(x) for x in output.read_text().splitlines()];done={x['index'] for x in prior}
else:done=set()
inputs={'sourceHashes':hashes,'fkSha256':hashlib.sha256(fkPath.read_bytes()).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generatorSha256':hashlib.sha256((N/'single_circle_candidate.py').read_bytes()).hexdigest(),'constantLengthMm':target,'scope':'External flexible section A-to-B only, all obstacles retained. NOT connector-to-connector or whole harness release.','nativeBaselineField':'nativeShellOriginalBottomIntersectionsMm3','jointLimitsChanged':False,'wholeHarnessAccepted':False,'requestedRange':[opt.start,opt.end]};inputPath=output.with_suffix('.inputs.json')
if inputPath.exists():
 old=json.loads(inputPath.read_text());assert old['sourceHashes']==inputs['sourceHashes'],'Input changed; choose a new output instead of resuming stale frames'
else:inputPath.write_text(json.dumps(inputs,indent=2)+'\n')
indices=list(range(opt.start,opt.end))
if opt.neutral_first:indices=[-1]+indices
for index in indices:
 if index in done:continue
 q={} if index==-1 else base['samples'][index]['jointDegrees'];r=candidate(q,target);p=np.asarray(r.pop('points'));poses,_=fk({k:math.radians(v) for k,v in q.items()});Ts={k:poses[k]@inv[k] for k in poses};expected=(Ts['jaw_soft']@np.r_[A,1])[:3];anchorError=float(np.linalg.norm(expected-p[0]));assert anchorError<1e-4,(q,anchorError)
 keep=np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-7];p=p[keep];sc=self_check(p);mesh=tube(p,7);solid=man(mesh);intersections={}
 for k,o in obs.items():
  v=hits(solid,o.transform(Ts[body[k]][:3]))
  if v>1e-4:intersections[k]=v
 row={'index':index,'jointDegrees':q,'nativeSourceCollisionsMm3':{} if index==-1 else base['samples'][index]['nativeShellOriginalBottomIntersectionsMm3'],'lengthMm':r['lengthMm'],'minimumCenterRadiusMm':r['minimumCenterRadiusMm'],'minimumInnerRadiusBoundMm':r['minimumCenterRadiusMm']-3.5,'headAnchorFKErrorMm':anchorError,'intersectionsMm3':intersections,'selfCheck':sc,'meshWatertight':bool(mesh.is_watertight),'meshBodyCount':len(mesh.split(only_watertight=False))}
 with output.open('a') as f:f.write(json.dumps(row,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())
 print(json.dumps({'index':index,'solidHits':len(intersections),'selfCrossings':sc['crossingCount'],'nativeBlocked':bool(row['nativeSourceCollisionsMm3'])}),flush=True)
 if index==-1:mesh.export(N/'single-circle-neutral-world.stl')
 failed=bool(intersections) or sc['crossingCount'] or not mesh.is_watertight
 del mesh,solid,p;gc.collect()
 if index==-1 and failed:print('Neutral failure saved. Stop and diagnose without spending budget on229poses.',flush=True);break
