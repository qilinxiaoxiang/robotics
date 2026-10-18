exec(open(__file__.replace('check_provisional_pi_domain.py','probe_exit.py')).read().split('head=np.array')[0])
p=H/'camera-ribbon-repair/refined-pi-core-probe-world.stl';s=man(load(p));rows=[]
for i,q in enumerate(cases):
 poses,_=fk({k:np.deg2rad(v) for k,v in q.items()});Ts={k:poses[k]@inv[k] for k in poses};m=s.transform(Ts['jaw_soft'][:3]);hh={}
 for k,o in obs.items():
  if body[k]=='jaw_soft':continue
  v=hits(m,o.transform(Ts[body[k]][:3]))
  if v>1e-4:hh[k]=v
 rows.append({'q':q,'hits':hh,'rigidBaselineBlocked':bool(rigid['samples'][i]['rigidIntersectionsMm3'])})
r={'source':str(p.relative_to(H)),'sourceHashes':hashes,'rows':rows,'accepted':False,'scope':'Only proposed bare Pi core against parts on other bodies, not the full connector envelope or fixed-head fit','newCollisionCases':sum(bool(x['hits']) and not x['rigidBaselineBlocked'] for x in rows)};(N/'provisional-pi-domain.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps([x for x in rows if x['hits']],indent=2),flush=True)
