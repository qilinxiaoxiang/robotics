from pathlib import Path
import json,copy,hashlib,ast,math
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();src=(M/'local_route.py').read_text()
for n in ast.parse(src).body:
 if isinstance(n,ast.FunctionDef)and n.name in['sample','tube','solid']:exec(ast.get_source_segment(src,n))
top=json.loads((M/'active-topology.json').read_text());right=json.loads((D/'joint-right.json').read_text());mapping={'ttl-04-03':('ttl-09-08','motor-9-socket-13','motor-8-socket-13'),'ttl-03-02':('ttl-08-07','motor-8-socket-14','motor-7-socket-13'),'ttl-02-01':('ttl-07-06','motor-7-socket-14','motor-6-socket-14')};rows=[]
def mirror(v):return[v[0],-v[1],v[2]]
for w in right['strands']:
 assert sha(w['file'])==w['sha256'];rid,fr,to=mapping[w['routeId']];q=copy.deepcopy(w);q.update(key=rid+'-'+str(w['wireSlot']+2),routeId=rid,source=top['ports'][fr],target=top['ports'][to]);q['controls']=[mirror(v)for v in w['controls']]
 for p in q['primitives']:
  for k in['start','end','mid','center']:
   if k in p:p[k]=mirror(p[k])
  if 'normal'in p:p['normal']=[-x for x in mirror(p['normal'])]
 pts,tt=sample(q['primitives']);m=tube(pts,tt);f=D/f'{rid}-strand-{w["wireSlot"]+2}.stl';m.export(f);q.update(file=str(f),sha256=sha(f),boundsMm=m.bounds.tolist(),checks=[])
 for end,p,offset in [('source',pts[0],0),('target',pts[-1],-.6 if rid=='ttl-07-06'else 0)]:
  port=q[end];possible=[np.array(port['shoulder'])+k*2.5*np.array(port['width'])+offset*np.array(port['outward'])for k in[-1,0,1]];assert min(np.linalg.norm(p-v)for v in possible)<1e-5,(q['key'],end,p,possible)
 rows.append(q)
(D/'joint-left.json').write_text(json.dumps({'status':'Mirrored candidate, independently checked against original left obstacles','sourceRightSha256':sha(D/'joint-right.json'),'strands':rows},indent=2));print(len(rows))
