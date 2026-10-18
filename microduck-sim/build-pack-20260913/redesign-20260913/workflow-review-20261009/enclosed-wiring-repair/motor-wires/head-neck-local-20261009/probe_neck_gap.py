from check_local import *
plan=json.loads((D/'plan.json').read_text());rows=[];probes=[]
# Cross-section-visible channel between the neck cutout and motor15 left flank.
# A finite six-position section measurement, not a routing search.
for x,y in [(12,12),(16,12),(20,12),(24,12),(28,12),(32,12)]:
 m=trimesh.creation.cylinder(radius=1.26,height=38,sections=32);m.apply_translation([x,y,114]);probes.append((x,y,m,solid(m)))
for o in plan['obstacles']:
 m=load(o)
 for x,y,p,a in probes:
  if not overlap(p.bounds,m.bounds):continue
  b=solid(m);c=a^b;v=c.volume()
  if v>1e-7:rows.append({'center':[x,y],'obstacle':o['key'],'volumeMm3':v,'boundsMm':list(c.bounding_box())})
(D/'neck-corridor-gap-probe.json').write_text(json.dumps({'verticalRangeMm':[95,133],'radiusMm':1.26,'positions':[[x,y]for x,y,_,_ in probes],'hits':rows,'planSha256':sha(D/'plan.json')},indent=2)+'\n');print(json.dumps(rows,indent=2))
