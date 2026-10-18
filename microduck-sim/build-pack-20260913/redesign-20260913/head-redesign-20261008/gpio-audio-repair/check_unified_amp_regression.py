"""One target/one foreign obstacle,12 recorded native-clear negative states."""
import argparse,json,sys,os
from pathlib import Path
import unify_amp_cap as u
p=argparse.ArgumentParser();p.add_argument('--target',choices=['cap','post0','post1','screws'],required=True);p.add_argument('--obstacle',choices=['head_yaw_link','motor13'],required=True);a=p.parse_args();u.core.guarded_import();c=u.core
planfile=u.OUT/'finite-stage-plan.json';plan=json.loads(planfile.read_text());domain=Path(plan['domainPath']);assert c.sha(domain)==plan['domainSha256'];cases=plan['regressionCases'];assert len(cases)==12
files={'cap':'cap-current-audio-usb-world.stl','post0':'amp-new-post-0-world.stl','post1':'amp-new-post-1-world.stl','screws':'amp-new-two-screws-world.stl'};targetfile=u.OUT/files[a.target];target=u.load(targetfile)
data=json.loads(c.SOURCE.read_text());config=json.loads(c.CONFIG.read_text());index=c.scene_index(data,config);row=index[a.obstacle];obstacle=c.solid(row)
SIM=u.H.parent.parents[1];fkfile=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py';sys.path.insert(0,str(fkfile.parent));from assembly_fk import fk
B,_=fk();ib={k:c.np.linalg.inv(v) for k,v in B.items()};body=row['body'];assert body in B
bindings=u.inputs([Path(__file__),planfile,domain,c.SOURCE,c.CONFIG,fkfile,targetfile]);rows=[];negative=None;trace=u.OUT/f'regression-{a.target}-{a.obstacle}.jsonl';reportfile=trace.with_suffix('.json')
with trace.open('w') as f:
 for r in cases:
  q=r['jointDegrees'];posed,_=fk({k:c.np.deg2rad(v) for k,v in q.items()});Th=posed['jaw_soft']@ib['jaw_soft'];T=c.np.linalg.inv(Th)@posed[body]@ib[body];moved=obstacle.transform(T[:3]);v,bb=c.volume_pair(target,moved)
  if a.target=='cap' and negative is None:
   old=u.load(u.BASE);nv,_=c.volume_pair(old,moved);negative={'sourcePoseIndex':r['sourcePoseIndex'],'volumeMm3':nv};del old;assert nv>1e-4,'Old-cap negative not reproduced'
  rowout={'sourcePoseIndex':r['sourcePoseIndex'],'jointDegrees':q,'volumeMm3':v,'boundsMm':bb,'failed':v>1e-4};rows.append(rowout);f.write(json.dumps(rowout)+'\n');f.flush();os.fsync(f.fileno());del moved
  report={'target':a.target,'obstacle':a.obstacle,'completed':len(rows)==12,'passed':len(rows)==12 and not any(x['failed'] for x in rows),'rows':rows,'oldCapNegativeControl':negative,'inputHashes':bindings,'integrationReady':False};c.atomic_json(reportfile,report)
  if v>1e-4:break
print(json.dumps({'report':str(reportfile),'pairs':len(rows),'passed':report['passed'],'peakMm3':max(r['volumeMm3'] for r in rows),'negative':negative}));sys.exit(0 if report['passed'] else 2)
