exec(open(__file__.replace('probe_turn.py','probe_exit.py')).read().split('head=np.array')[0])
for node in ast.parse((H/'usb-access/full-harness/build_harness.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['arc','tube']:exec(compile(ast.Module(body=[node],type_ignores=[]),'<geometry>','exec'))
ptail=np.array([1e9]*3);rows=[]
for direction in [[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]]:
 for R in [8.,11.,16.,25.]:
  head=np.array([-31.,23.2,125]);p,L=arc(head,np.array([-1.,0,0]),np.array(direction,float),R);p=np.vstack([p,p[-1]+np.array(direction)*25]);s=man(tube(p,7));hh=[]
  for i,q in enumerate(cases):
   poses,_=fk({k:np.deg2rad(v) for k,v in q.items()});Ts={k:poses[k]@inv[k] for k in poses};T=Ts['jaw_soft'];m=s.transform(T[:3]);bad={}
   for k,o in obs.items():
    v=hits(m,o.transform(Ts[body[k]][:3]))
    if v>1e-4:bad[k]=v
   if bad:hh.append({'case':i,'q':q,'hits':bad,'rigid':bool(rigid['samples'][i]['rigidIntersectionsMm3'])})
  rows.append({'direction':direction,'R':R,'fails':hh,'validFails':sum(not r['rigid'] for r in hh)});print(direction,R,rows[-1]['validFails'],flush=True)
(N/'turn-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
