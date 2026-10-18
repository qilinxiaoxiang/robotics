"""New wire saddle: no scene cache, full finite domain in bounded chunks."""
import argparse,json,sys,gc
from pathlib import Path
import bounded_amp_check as c
import check_speaker_rewire as s
import precision_mesh as pm
D=Path(__file__).resolve().parent;H=D.parent;O=D/'speaker-rewire';p=argparse.ArgumentParser();p.add_argument('--key',required=True);p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=80);a=p.parse_args();assert a.count<=80;c.guarded_import();scene=json.loads((O/'scene-plan.json').read_text());targetfile=O/'speaker-tie-receiving-world.stl';target=pm.load(c,targetfile);row=scene['rows'][a.key];obstacle=s.solid(row)
fkfile=H.parent.parents[1]/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py';sys.path.insert(0,str(fkfile.parent));from assembly_fk import fk
base,_=fk();ib={k:c.np.linalg.inv(v) for k,v in base.items()};body=row.get('body') or json.loads(Path(row['dataFile']).read_text())['body'];domain=json.loads(c.DOMAIN.read_text());cases=domain['samples'];rows=[];out=O/f'tie-domain-{a.key}-{a.start}.json';bindings=c.fingerprint([Path(__file__),O/'scene-plan.json',targetfile,c.DOMAIN,fkfile,row['path'] if row.get('path') else row['dataFile']]);report={'inputHashes':bindings,'start':a.start,'count':a.count,'key':a.key,'rows':rows,'passed':False,'integrationReady':False}
for i in range(a.start,min(a.start+a.count,len(cases))):
 q=cases[i]['jointDegrees'];posed,_=fk({k:c.np.deg2rad(v) for k,v in q.items()});Th=posed['jaw_soft']@ib['jaw_soft'];T=c.np.linalg.inv(Th)@posed[body]@ib[body];moved=obstacle.transform(T[:3]);v,bb=c.volume_pair(target,moved);rows.append({'pose':i,'volumeMm3':v,'bounds':bb});c.atomic_json(out,report);del moved;gc.collect()
 if v>1e-4:break
report['passed']=len(rows)==min(a.count,len(cases)-a.start) and all(r['volumeMm3']<=1e-4 for r in rows);c.atomic_json(out,report);print(json.dumps({'key':a.key,'start':a.start,'rows':len(rows),'passed':report['passed'],'failed':[r for r in rows if r['volumeMm3']>1e-4]}));raise SystemExit(0 if report['passed'] else 2)
