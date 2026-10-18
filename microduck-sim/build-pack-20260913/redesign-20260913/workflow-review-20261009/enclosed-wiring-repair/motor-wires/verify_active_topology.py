import copy,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent

def check(d,source=True):
 errors=[];used=[];visited=[];edges=[]
 for b in d['branches']:
  ids=b['motorIds'];visited+=ids[1:]
  if ids[0]!=0:errors.append('branch must start at OpenRB')
  rr=[next((r for r in d['routes'] if r['id']==k),None) for k in b['routeIds']]
  if len(rr)!=len(ids)-1:errors.append('branch edge count')
  for a,z,r in zip(ids,ids[1:],rr):
   if r is None:errors.append('missing edge');continue
   p,q=d['ports'][r['fromPort']],d['ports'][r['toPort']]
   if (p['motor'],q['motor'])!=(a,z):errors.append('edge endpoint differs from branch')
   used.extend([r['fromPort'],r['toPort']]);edges.append((p['motor'],q['motor']))
 if sorted(visited)!=list(range(1,16)):errors.append('motors must occur exactly once')
 if len(used)!=len(set(used)):errors.append('physical socket reused')
 if len(edges)!=15 or len(set(edges))!=15:errors.append('expected fifteen unique cable edges')
 if (1,6) in edges or (6,1) in edges:errors.append('cross-foot edge forbidden')
 if sorted(z for a,z in edges if a==0)!=[10,15]:errors.append('two independent OpenRB branches required')
 if source:
  for f,h in d['sourceHashes'].items():
   if hashlib.sha256(Path(f).read_bytes()).hexdigest()!=h:errors.append('stale source '+f)
  old=json.loads(Path(next(f for f in d['sourceHashes'] if f.endswith('route-input.json'))).read_text())
  registry={f"motor-{p['motor']}-socket-{p['sourceSocket']}":p for group in old['ports'].values()for p in group}
  for r in d['routes']:
   for key in [r['fromPort'],r['toPort']]:
    if key.startswith('motor-0-'):continue
    current=d['ports'][key];p=registry[key]
    if any(current[k]!=p[k]for k in ['motor','sourceSocket','mouth','shoulder','outward','transform','housingLocalBounds']):errors.append('registered endpoint changed '+key)

 return errors

if __name__=='__main__':
 p=D/'active-topology.json';d=json.loads(p.read_text());errors=check(d)
 neg=copy.deepcopy(d);neg['branches'][1]['motorIds']=[1,6,7,8,9,10]
 neg_errors=check(neg,False)
 assert not errors,errors
 assert neg_errors,'old cross-foot negative control passed'
 result={'passed':True,'topologySha256':hashlib.sha256(p.read_bytes()).hexdigest(),'branches':2,'cableEdges':15,'uniqueMotors':15,'noSocketReuse':True,'registeredEndpointBindingPassed':True,'crossFootNegativeControlRejected':True,'negativeErrors':neg_errors,'scope':'Graph and source-frame consistency only; does not accept wire paths, VDD distribution or physical assembly.'}
 (D/'active-topology-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
