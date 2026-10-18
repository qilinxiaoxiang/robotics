"""Finite connector breakout check: four orthogonal first bends at each actual port."""
from check_local import *
from wire_geometry import primitives,sample,tube
plan=json.loads((D/'plan.json').read_text());top=json.loads((D.parent/'active-topology.json').read_text());candidates=[]
for key,p in plan['ports'].items():
 if '--long13' in sys.argv and not key.startswith('motor-13-'):continue
 A=np.array(p['shoulder'])-.6*np.array(p['outward']);out=np.array(p['outward']);wid=np.array(p['width']);up=np.cross(out,wid)
 for j,direction in enumerate([wid,-wid,up,-up]):
  lead=7 if '--long13' in sys.argv else 3
  pts=[A,A+out*lead,A+out*lead+direction*10];pr=primitives(pts,R=2);m=tube(*sample(pr));candidates.append({'port':key,'direction':direction.tolist(),'controlPoints':np.array(pts).tolist(),'m':m,'a':solid(m),'hits':[]})
for o in plan['obstacles']:
 m=load(o);near=[p for p in candidates if overlap(p['m'].bounds,m.bounds)]
 if not near:continue
 assert m.is_volume,o['key'];b=solid(m)
 for p in near:
  cut=p['a']^b;v=cut.volume()
  if v>1e-7:p['hits'].append({'key':o['key'],'volumeMm3':v,'boundsMm':list(cut.bounding_box())})
 del b,m;gc.collect()
rows=[{k:v for k,v in p.items()if k not in ['m','a']}for p in candidates]
(D/('breakout-long13.json'if '--long13' in sys.argv else 'breakout-probes.json')).write_text(json.dumps({'rows':rows,'scope':'center conductor only, not full three-wire route','sourceHashes':{str(D/'plan.json'):sha(D/'plan.json')}},indent=2))
for p in rows:print(p['port'],p['direction'],[(x['key'],round(x['volumeMm3'],3))for x in p['hits']],flush=True)
