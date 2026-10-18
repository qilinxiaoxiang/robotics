"""Sample entry of one complete loose USB cable against one closed-head obstacle."""
from pathlib import Path
import argparse,json,hashlib,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('span',type=int);p.add_argument('group',choices=['sc','ac']);p.add_argument('obstacle');p.add_argument('--stop-on-hit',action='store_true');p.add_argument('--plan',type=Path,default=D/'lowered-side-edge-aligned-plan.json');p.add_argument('--exports',type=Path,default=D/'circumscribed-exports');p.add_argument('--obstacle-file',type=Path);p.add_argument('--output',type=Path,default=D/'assembly-entry');a=p.parse_args();hashes={}
def bind(p):
 p=Path(p);hashes[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest();return p
def read(p):return json.loads(bind(p).read_text())
def solid(path):
 m=tm.load(bind(path),force='mesh');assert m.is_watertight and m.is_volume,('Invalid solid',path)
 s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
plan=read(a.plan);domain=read(D/'current-obstacle-plan-v2.json')
exports=a.exports/f'span-{a.span}-diagnostic';r=read(exports/'export.json')
for f,h in r['sourceHashes'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,('Stale cable export',f)
parts={name:solid(exports/(name+'.stl')) for name in (['scMicroBReceiving','scFlexibleReceiving','scFemaleReceiving'] if a.group=='sc' else ['acUsbCReceiving','acFlexibleReceiving','acMaleReceiving'])}
obstaclePath=a.obstacle_file or domain['obstacles'][a.obstacle]['source'];ob=solid(obstaclePath)
if a.group=='sc':axis=np.array(plan['piPlugOutwardAxis']);distance=30.
else:axis=np.array(read(D.parent/'full-harness/published-usbc-verification.json')['outwardAxis']);distance=40.
out=a.output;out.mkdir(exist_ok=True,parents=True);records=[];n=int(distance/.25)+1;bb=np.array(ob.bounding_box()).reshape(2,3)
with (out/f'{a.span}-{a.group}-{a.obstacle}.jsonl').open('w') as stream:
 for shift in np.linspace(distance,0,n):
  hit=False
  for name,part in parts.items():
   moving=part.translate(axis*shift);mb=np.array(moving.bounding_box()).reshape(2,3);volume=0.
   if np.all(mb[0]<bb[1]) and np.all(bb[0]<mb[1]):
    intersection=moving^ob;assert intersection.status()==mf.Error.NoError;volume=max(0.,intersection.volume())
   row={'moving':name,'obstacle':a.obstacle,'offsetMm':float(shift),'overlapMm3':volume};records.append(row);stream.write(json.dumps(row)+'\n');stream.flush();hit|=volume>1e-5
  if hit and a.stop_on_hit:break
bind(__file__);report={'spanMm':a.span,'looseCableGroup':a.group,'obstacle':a.obstacle,'operation':'Close cap with USB cables not yet installed; insert complete loose cable via service port, before external USB-A mating.','movingMembers':list(parts),'axis':axis.tolist(),'entryDistanceMm':distance,'stepMm':.25,'expectedPairs':n*len(parts),'completedPairs':len(records),'coverageComplete':len(records)==n*len(parts),'hits':[r for r in records if r['overlapMm3']>1e-5],'allClear':len(records)==n*len(parts) and not any(r['overlapMm3']>1e-5 for r in records),'sourceHashes':hashes,'assemblyAccepted':False,'boundary':'One closed-head obstacle and discrete entry samples only; final USB-A mating and other obstacles not implied.'};(out/f'{a.span}-{a.group}-{a.obstacle}.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'allClear':report['allClear'],'completed':len(records),'firstHits':report['hits'][:3]}))
