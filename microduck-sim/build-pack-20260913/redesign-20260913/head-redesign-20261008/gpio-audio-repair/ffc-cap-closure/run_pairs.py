"""Only run once a real complete200mm FFC has frozen source-bound acceptance."""
from pathlib import Path
import json,subprocess,concurrent.futures,argparse,sys
from contracts import sha,load_contract
D=Path(__file__).resolve().parent;H=D.parents[1]
p=argparse.ArgumentParser();p.add_argument('--contract',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--jobs',type=int,choices=[1,2],default=2);a=p.parse_args();contract=load_contract(a.contract);inv=D/'moving-inventory.json';plan=json.loads(inv.read_text());a.output.mkdir(parents=True,exist_ok=True)
def run(key):
 dest=a.output/(key+'.json');resource=a.output/(key+'-resource.json');cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','60','--max-mib','512','--seconds','120','--report',str(resource),'--','/tmp/microduck-cad-venv/bin/python',str(D/'check_pair.py'),'--inventory',str(inv),'--contract',str(a.contract),'--key',key,'--output',str(dest)]
 # No stale successful receipt reuse: current inventory+contract are bound per pair.
 if dest.exists():
  old=json.loads(dest.read_text());hs=old.get('sourceHashes',{})
  if old.get('complete')and old.get('passed')and hs.get(str(inv))==sha(inv)and hs.get(str(a.contract))==sha(a.contract)and all(sha(f)==h for f,h in hs.items()):return {'key':key,'exitCode':0,'reusedExactBoundReceipt':True}
 c=subprocess.run(cmd,text=True,capture_output=True);(a.output/(key+'.log')).write_text(c.stdout+c.stderr);print(key,c.returncode,flush=True);return {'key':key,'exitCode':c.returncode,'reusedExactBoundReceipt':False}
first=run('validate-ffc');assert first['exitCode']==0,'FFC closed-geometry input validation failed'
with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs)as ex:done=list(ex.map(run,[r['key']for r in plan['movingEntities']]))
records=[];passed=True
for row in plan['movingEntities']:
 q=a.output/(row['key']+'.json');resource=a.output/(row['key']+'-resource.json');r=json.loads(q.read_text())if q.exists()else {};hs=r.get('sourceHashes',{});exitcode=next(x['exitCode']for x in done if x['key']==row['key']);ok=exitcode==0 and r.get('complete')and r.get('passed')and len(r.get('rows',[]))==161 and hs.get(str(inv))==sha(inv)and hs.get(str(a.contract))==sha(a.contract)and hs.get(row['path'])==row['sha256']and all(sha(f)==h for f,h in hs.items())
 passed=passed and bool(ok);records.append({'key':row['key'],'group':row['group'],'report':str(q),'reportSha256':sha(q)if q.exists()else None,'passed':bool(ok),'complete':r.get('complete',False),'sampleCount':len(r.get('rows',[])),'peak':r.get('peak'),'resourceReport':str(resource)})
report={'newFfcObstacleClosurePassed':passed,'wholeHeadAccepted':False,'inventorySha256':sha(inv),'ffcContractSha256':sha(a.contract),'ffcMeshSha256':contract['meshSha256'],'sampleCountPerEntity':161,'movingEntityCount':148,'expectedEntitySamples':23828,'actualEntitySamples':sum(r['sampleCount']for r in records),'groups':plan['groups'],'pairs':records,'execution':done,'excludedFixedObstacles':'Only preexisting root-owned43pair receipts are referenced by inventory. No claim those cover unrelated pose changes.','continuousPathClaim':False,'contactWaivers':[]};(a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in('pairs','execution')},indent=2));sys.exit(0 if passed else 2)
