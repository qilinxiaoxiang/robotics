"""Finite finalclosure for sourcebound localdogleg; does notfreezeprinting."""
from pathlib import Path
import json,struct,math,subprocess,sys,concurrent.futures
from contracts import sha,load_contract
D=Path(__file__).resolve().parent;H=D.parents[1];F=H/'camera-ribbon-repair/fixed-pose-local-bend';A=H/'gpio-audio-repair/ffc-terminal-adjustment';O=A/'final-closure';O.mkdir(exist_ok=True)
receipt=A/'dogleg-0.25-check.json';rr=json.loads(receipt.read_text());mesh=Path(rr['fullMesh']);proof=A/'prefix-inheritance.json';a={'mode':'local-geometric-candidate','candidateOnly':True,'wholeHarnessAccepted':False,'completePath':True,'lengthMm':200,'mesh':str(mesh),'meshSha256':rr['fullMeshSha256'],'localReceipt':str(receipt),'sourceHashes':{str(p):sha(p)for p in [receipt,mesh,A/'dogleg-0.25.json',proof,F/'spacer2-tilted-complete-static.json',F/'spacer2-tilted-complete-localization.json']},'scope':'Newsourcebound complete lengthpreserving developable candidate; finalgeometryonly, no physicalbendstrength orprintingrelease.','staticRemaining':[]}
cp=O/'input-contract.json';cp.write_text(json.dumps(a,indent=2)+'\n');load_contract(cp)
inv=D/'moving-inventory.json';plan=json.loads(inv.read_text())
for f,h in plan['sourceHashes'].items():assert sha(f)==h
# Surface triangle clipping to1mm infinite Y slabs yields bounding boxes enclosing each
# slab of the entire bounded solid: any interior cross-section extrema lie on its surface.
def triangles(p):
 data=p.read_bytes()
 if len(data)>=84 and len(data)==84+50*struct.unpack_from('<I',data,80)[0]:
  for off in range(84,len(data),50):
   x=struct.unpack_from('<12f',data,off);yield [list(x[i:i+3]) for i in (3,6,9)]
 else:
  tri=[]
  for l in data.decode().splitlines():
   if l.strip().startswith('vertex '):
    tri.append(list(map(float,l.split()[1:])))
    if len(tri)==3:yield tri;tri=[]
def clip(poly,y,above):
 out=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  ip=p[1]>=y if above else p[1]<=y;iq=q[1]>=y if above else q[1]<=y
  if ip:out.append(p)
  if ip!=iq:
   t=(y-p[1])/(q[1]-p[1]);out.append([p[k]+t*(q[k]-p[k]) for k in range(3)])
 return out
slabs={};triCount=0
for tri in triangles(mesh):
 triCount+=1
 for i in range(math.floor(min(p[1] for p in tri)),math.floor(max(p[1] for p in tri))+1):
  poly=clip(clip(tri,i,True),i+1,False)
  if not poly:continue
  b=slabs.setdefault(i,[[float('inf')]*3,[-float('inf')]*3])
  for v in poly:
   for k in range(3):b[0][k]=min(b[0][k],v[k]-1e-8);b[1][k]=max(b[1][k],v[k]+1e-8)
boxes=list(slabs.values());globalbb=[[min(b[0][k]for b in boxes)for k in range(3)],[max(b[1][k]for b in boxes)for k in range(3)]]
def apart(a,b):return any(a[1][k]<b[0][k] or b[1][k]<a[0][k] for k in range(3))
rows=[];near=[]
for r in plan['movingEntities']:
 assert sha(r['path'])==r['sha256'];b=[list(x)for x in r['boundsMm']];b[1][2]+=40
 overall=apart(b,globalbb);fine=overall or all(apart(b,q)for q in boxes)
 row={'key':r['key'],'group':r['group'],'movingSha256':r['sha256'],'sweptBoundsMm':b,'sweptOverallSeparated':overall,'sweptSlabSeparated':fine,'continuousSeparationProved':fine,'sampleCountCovered':161 if fine else 0}
 rows.append(row)
 if not fine:near.append(r['key'])
(O/'broadphase.json').write_text(json.dumps({'candidateOnly':True,'wholeHarnessAccepted':False,'contractSha256':sha(cp),'inventorySha256':sha(inv),'sourceScriptSha256':sha(__file__),'triangles':triCount,'slabAxis':'Y','slabWidthMm':1,'slabBoundsMm':boxes,'entities':rows,'exactNeeded':near},indent=2)+'\n');print('exact needed',len(near),near,flush=True)
def run(key):
 out=O/(key+'.json');res=O/(key+'-resource.json');cmd=[sys.executable,str(H/'run_bounded_cad.py'),'--parallel-light','--wait-lock-seconds','60','--max-mib','512','--seconds','120','--report',str(res),'--','/tmp/microduck-cad-venv/bin/python',str(D/'check_pair.py'),'--inventory',str(inv),'--contract',str(cp),'--key',key,'--output',str(out)]
 r=subprocess.run(cmd,text=True,capture_output=True);(O/(key+'.log')).write_text(r.stdout+r.stderr);print(key,r.returncode,flush=True);return {'key':key,'exitCode':r.returncode}
validate=run('validate-ffc');assert validate['exitCode']==0
with concurrent.futures.ThreadPoolExecutor(max_workers=2)as ex:results=list(ex.map(run,near))
for r in rows:
 if r['continuousSeparationProved']:r['passed']=True;continue
 p=O/(r['key']+'.json');v=json.loads(p.read_text())if p.exists()else {};execution=next(z for z in results if z['key']==r['key']);r.update(exactReport=str(p),exactReportSha256=sha(p)if p.exists()else None,passed=execution['exitCode']==0 and v.get('complete',False) and v.get('passed',False),sampleCountCovered=len(v.get('rows',[])),peak=v.get('peak'))
summary={'candidateOnly':True,'wholeHarnessAccepted':False,'printingUnlocked':False,'diagnosticClosureClear':all(r['passed']for r in rows),'expectedSamples':23828,'samplesCovered':sum(r['sampleCountCovered']for r in rows),'continuousBroadphaseEntities':sum(r['continuousSeparationProved']for r in rows),'exactEntities':len(near),'sourceHashes':{str(p):sha(p)for p in [cp,inv,Path(__file__),O/'broadphase.json']},'entities':rows,'scope':a['scope'],'staticRemaining':a['staticRemaining']};(O/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:v for k,v in summary.items()if k not in ['entities','sourceHashes','staticRemaining']},indent=2))
