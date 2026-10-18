"""One deterministic joint-relative candidate; ROOT dispatches through bounded CAD.

Incremental JSONL survives resource termination. This is intentionally a local
loop clearance screen, not whole-harness acceptance: fixed bridges, support
parts, full wire lengths, mating ends, and installation must follow a passing
local screen. A neutral failure stops immediately instead of broad-searching.
"""
import os,sys,json,hashlib,math,argparse
from pathlib import Path
N=Path(__file__).resolve().parent
if os.environ.get('MICRODUCK_BOUNDED_CAD')!='1':
 raise SystemExit('Only root may dispatch this script via H/run_bounded_cad.py after obtaining the sole CAD token.')
sys.path.insert(0,str(N.parent))
from check_routes import *
from rolling_loop_math import rolling_loop
import ast
for node in ast.parse((H/'usb-access/full-harness/build_harness.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name=='tube':exec(compile(ast.Module(body=[node],type_ignores=[]),'<parallel transported tube>','exec'))
ptail=np.array([1e9]*3)
SIM=H.parent.parents[1];sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'));from assembly_fk import fk
B,_=fk();inv={k:np.linalg.inv(v) for k,v in B.items()};body={p['key']:p.get('body','jaw_soft') for p in data['parts']}
for k in obs:body.setdefault(k,'jaw_soft')
body={k:b if b in B else 'trunk_base' for k,b in body.items()}
# One explicit source-frozen placement, no automatic parameter search.
# Center/axis/radial are NEUTRAL world coordinates; parent motion then applies.
# Upper anchor must follow child motion exactly; negative q sign for reversed axis.
segments=[
 {'joint':'neck_pitch','parent':'trunk_base','child':'neck','center':[26,-50,32.4215],'axis':[0,-1,0],'radial':[-1,0,0],'R':18,'d':24,'C':55,'sign':1},
 {'joint':'head_pitch','parent':'neck','child':'neck_pitch','center':[26,-50,82.4215],'axis':[0,-1,0],'radial':[-1,0,0],'R':18,'d':24,'C':55,'sign':-1},
 {'joint':'head_yaw','parent':'neck_pitch','child':'yaw_roll_motion','center':[26,0,160],'axis':[0,0,1],'radial':[-1,0,0],'R':18,'d':24,'C':95,'sign':1},
 {'joint':'head_roll','parent':'yaw_roll_motion','child':'jaw_soft','center':[-36,0,115.6146],'axis':[-1,0,0],'radial':[0,-1,0],'R':18,'d':24,'C':22.5,'sign':1}]
args=argparse.ArgumentParser();args.add_argument('--stage',choices=['neutral','229','paths'],default='neutral');args.add_argument('--resume',action='store_true');opt=args.parse_args()
basePath=H/'usb-access/usb-repair/rigid-domain.json';base=json.loads(read(basePath));cases=[{'q':{},'nativeContacts':{},'kind':'neutral'}]
if opt.stage!='neutral':
 cases += [{'q':r['jointDegrees'],'nativeContacts':r['nativeShellOriginalBottomIntersectionsMm3'],'kind':'229'} for r in base['samples']]
if opt.stage=='paths':
 # Every existing target is approached from neutral at <=1 degree maximum-axis increments.
 # No pose is omitted on the basis of cable failure or prior added-post collision.
 for i,r in enumerate(base['samples']):
  q=r['jointDegrees'];n=max(1,math.ceil(max(map(abs,q.values()))))
  for j in range(1,n):cases.append({'q':{k:v*j/n for k,v in q.items()},'nativeContacts':None,'kind':'angular-path','target':i,'fraction':j/n})
output=N/('segmented-'+opt.stage+'.jsonl');done=set()
if opt.resume and output.exists():
 for line in output.read_text().splitlines():done.add(json.loads(line)['index'])
else:output.write_text('')
metadata={'sourceHashes':hashes,'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'mathSha256':hashlib.sha256((N/'rolling_loop_math.py').read_bytes()).hexdigest(),'segments':segments,'stage':opt.stage,'sampleCount':len(cases),'acceptance':False,'receivingDiameterMm':7,'nominalIndividualWireODMm':[1.8]*4+[1.5]*3+[.8]*4,'guideAndBridgeDesignComplete':False,'wholeHarnessComplete':False,'nativeBaselineMeaning':'Uses nativeShellOriginalBottomIntersectionsMm3 for all229 states. Angular-path rigid contacts need an independent fresh gate; no classification is inferred from endpoints.'};(N/('segmented-'+opt.stage+'-inputs.json')).write_text(json.dumps(metadata,indent=2)+'\n')
for i,case in enumerate(cases):
 if i in done:continue
 q=case['q'];poses,_=fk({k:math.radians(v) for k,v in q.items()});Ts={k:poses[k]@inv[k] for k in poses};oo={k:s.transform(Ts[body[k]][:3]) for k,s in obs.items()};row={'index':i,**case,'segments':[]};ss={}
 for p in segments:
  model=rolling_loop(p['center'],p['axis'],p['radial'],p['R'],p['d'],math.radians(p['C']),math.radians(q.get(p['joint'],0))*p['sign'],.5)
  neutral=rolling_loop(p['center'],p['axis'],p['radial'],p['R'],p['d'],math.radians(p['C']),0,.5)
  T=Ts[p['parent']];pts=np.array(model['points']);pts=pts@T[:3,:3].T+T[:3,3]
  expected=(Ts[p['child']]@np.r_[neutral['upperAnchor'],1])[:3];actual=(T@np.r_[model['upperAnchor'],1])[:3];error=float(np.linalg.norm(expected-actual))
  if error>1e-4:raise AssertionError((p['joint'],'moving anchor does not follow child',error))
  mesh=tube(pts,7);solid=man(mesh);ss[p['joint']]=solid;hh={}
  for k,o in oo.items():
   v=hits(solid,o)
   if v>1e-4:hh[k]=v
  row['segments'].append({'joint':p['joint'],'lengthMm':model['analyticLengthMm'],'minimumRadiusMm':model['minimumCenterlineRadiusMm'],'movingAnchorErrorMm':error,'intersectionsMm3':hh})
  if i==0:mesh.export(N/(p['joint']+'-rolling-loop-neutral-world.stl'))
 row['betweenSegmentsMm3']={}
 keys=list(ss)
 for a in range(len(keys)):
  for b in range(a):
   v=hits(ss[keys[a]],ss[keys[b]])
   if v>1e-4:row['betweenSegmentsMm3'][keys[a]+'--'+keys[b]]=v
 with output.open('a') as f:f.write(json.dumps(row,separators=(',',':'))+'\n');f.flush();os.fsync(f.fileno())
 print(json.dumps({'index':i,'total':len(cases),'hits':sum(bool(r['intersectionsMm3']) for r in row['segments']),'nativeBlocked':bool(case['nativeContacts'])}),flush=True)
 if i==0 and (any(r['intersectionsMm3'] for r in row['segments']) or row['betweenSegmentsMm3']):
  print('Neutral local-loop failure saved; stopped before broader poses. Diagnose before next token.',flush=True);break
