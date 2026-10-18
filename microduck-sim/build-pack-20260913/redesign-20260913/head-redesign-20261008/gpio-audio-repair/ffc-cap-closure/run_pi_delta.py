from pathlib import Path
import json,sys,subprocess,concurrent.futures
from contracts import sha
from prepare_inventory import bounds
D=Path(__file__).resolve().parent;H=D.parents[1];C=H/'camera-ribbon-repair';F=C/'fixed-pose-local-bend';O=D/'diagnostic-pi-spacer2';O.mkdir(exist_ok=True)
inv=D/'moving-inventory.json';plan=json.loads(inv.read_text());pose=F/'pi-spacer2-pose.json';pm=C/'positive-x225/pi-geometry-manifest.json';parts=F/'pi-spacer2-parts.json';T=json.loads(pose.read_text());delta=T['translationFromPositiveX225Mm'];base=C/T['basePoseFile'];assert sha(base)==T['basePoseSha256'];hs={str(p):sha(p)for p in [inv,pose,pm,parts,base,Path(__file__)]}
for f,h in plan['sourceHashes'].items():assert sha(f)==h
fixed=[]
for r in json.loads(pm.read_text())['parts']:
 p=H/r['mesh'];assert sha(p)==r['sha256'];b=bounds(p);fixed.append({'key':r['key'],'path':str(p),'sha256':sha(p),'translationMm':delta,'boundsMm':[[v[k]+delta[k]for k in range(3)]for v in b]})
for r in json.loads(parts.read_text())['rows']:
 for suffix,field in [('screw','screwMesh'),('spacer','spacerMesh')]:
  p=H/r[field];fixed.append({'key':r['id']+'_'+suffix,'path':str(p),'sha256':sha(p),'translationMm':[0,0,0],'boundsMm':bounds(p)})
def apart(a,b):return any(a[1][k]<b[0][k] or b[1][k]<a[0][k]for k in range(3))
rows=[];jobs=[]
for m in plan['movingEntities']:
 assert sha(m['path'])==m['sha256'];b=[list(v)for v in m['boundsMm']];b[1][2]+=40
 for f in fixed:
  key=m['key']+'--'+f['key'];sep=apart(b,f['boundsMm']);row={'key':key,'moving':m['key'],'fixed':f['key'],'sweptSeparationProved':sep,'samplesCovered':161 if sep else 0,'passed':sep};rows.append(row)
  if not sep:
   job={'moving':m,'fixed':f,'sourceHashes':hs|{m['path']:m['sha256'],f['path']:f['sha256']}};p=O/(key+'-input.json');p.write_text(json.dumps(job,indent=2)+'\n');jobs.append((key,p))
(O/'inventory.json').write_text(json.dumps({'fixed':fixed,'movingInventorySha256':sha(inv),'pairs':rows,'sourceHashes':hs,'expectedPairs':len(rows),'expectedSamples':len(rows)*161},indent=2)+'\n');print('fixed',len(fixed),'pairs',len(rows),'exact',len(jobs),flush=True)
def run(item):
 key,p=item;out=O/(key+'.json');resource=O/(key+'-resource.json');cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','60','--max-mib','512','--seconds','120','--report',str(resource),'--','/tmp/microduck-cad-venv/bin/python',str(D/'check_delta_pair.py'),str(p),str(out)];q=subprocess.run(cmd,text=True,capture_output=True);(O/(key+'.log')).write_text(q.stdout+q.stderr);print(key,q.returncode,flush=True);return key,q.returncode
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as ex:done=dict(ex.map(run,jobs))
for r in rows:
 if r['sweptSeparationProved']:continue
 p=O/(r['key']+'.json');a=json.loads(p.read_text())if p.exists()else {};r.update(passed=done[r['key']]==0 and a.get('complete',False) and a.get('passed',False),samplesCovered=len(a.get('rows',[])),report=str(p),reportSha256=sha(p)if p.exists()else None,peak=a.get('peak'))
s={'candidateOnly':True,'wholeHarnessAccepted':False,'printingUnlocked':False,'deltaPiClosureClear':all(r['passed']for r in rows),'fixedCount':len(fixed),'pairCount':len(rows),'exactPairCount':len(jobs),'samplesCovered':sum(r['samplesCovered']for r in rows),'expectedSamples':len(rows)*161,'sourceHashes':hs,'pairs':rows,'boundary':'Only changedPi+2mm rigidreceiving andsixnew hardware solids versus populatedcap. No inheritance ofoldPi43receipts. Full component andmale conservativeboxes retained; clear proves clearance from these overbounds, contact would require actualcomponentclassification.'};(O/'summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps({k:v for k,v in s.items()if k not in ['pairs','sourceHashes']},indent=2))
