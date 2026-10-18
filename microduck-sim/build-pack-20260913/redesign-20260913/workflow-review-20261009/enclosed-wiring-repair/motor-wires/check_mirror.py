from pathlib import Path
exec(Path(__file__).with_name('local_route.py').read_text().split('rows=[];solids=[]')[0])
a=json.loads((D/'local-route.json').read_text());ref=next(x for x in json.loads((OLD/'routes.json').read_text())['routes']if x['id']=='ttl-08-09');rows=[];solids=[]
def mir(v):return [v[0],-v[1],v[2]]
for row in a['strands']:
 pr=[]
 for p in row['primitives'][::-1]:
  q=dict(p);q['start']=mir(p['end']);q['end']=mir(p['start'])
  if p['kind']=='arc':q['mid']=mir(p['mid']);q['center']=mir(p['center']);q['normal']=mir(p['normal'])
  pr.append(q)
 p,t=sample(pr);m=tube(p,t);f=D/f"local-08-09-wire-{row['id']}.stl";m.export(f);s=solid(m);solids.append(s);hits=[];checks=[]
 for o in (OLD/'obstacles').glob('*.json'):
  ob=json.loads(o.read_text());bb=np.array(ob['expectedFinalBoundsMm'])
  if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
  mm=trimesh.load_mesh(ob['file'],process=True);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));b=solid(mm);cut=s^b;v=cut.volume();checks.append({'key':ob['key'],'sourceSha256':ob['sha256'],'validSolid':True,'overlapMm3':v})
  if v>1e-7:hits.append({'key':ob['key'],'volumeMm3':v,'bounds':list(cut.bounding_box())})
 for end,point in [('from',p[0]),('to',p[-1])]:
  allowed=[np.array(ref[end]['shoulder'])+k*2.5*np.array(ref[end]['width'])for k in [-1,0,1]];assert min(np.linalg.norm(point-x)for x in allowed)<1e-6
 rows.append({**row,'source':ref['from'],'target':ref['to'],'controlPoints':[mir(v)for v in row['controlPoints'][::-1]],'file':str(f.resolve()),'sha256':sha(f),'primitives':pr,'meshBoundsMm':m.bounds.tolist(),'collisions':hits,'checked':checks});print(row['id'],hits)
selfs=[{'a':i+1,'b':j+1,'overlapMm3':(solids[i]^solids[j]).volume()}for i in range(3)for j in range(i)]
(D/'mirror-route.json').write_text(json.dumps({**a,'route':'ttl-08-09','strands':rows,'wireWire':selfs,'allStaticClear':not any(x['collisions']for x in rows)and not any(x['overlapMm3']>1e-7 for x in selfs),'mirroredFromSha256':sha(D/'local-route.json'),'sourcePortEndpointsVerified':True},indent=2));print(selfs)
