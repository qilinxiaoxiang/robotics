from pathlib import Path
import json,numpy as np
O=Path(__file__).resolve().parent;ns={'__file__':str(O/'audit_motor_interfaces.py')};exec((O/'audit_motor_interfaces.py').read_text().rsplit('rows=[]',1)[0],ns)
rows=[]
for mot in ns['motors']:
 candidates=[]
 for g,wm in ns['prints']:
  m=wm.copy().apply_transform(np.linalg.inv(mot['world']))
  if np.any(m.bounds[0]>[20,3,3]) or np.any(m.bounds[1]<[9,-3,-3]):continue
  a=np.arange(16)*np.pi/8+.123;orig=np.c_[np.full(16,-50),np.c_[np.cos(a),np.sin(a)]*1.6]
  hits,rays,_=m.ray.intersects_location(orig,np.tile([1,0,0],(16,1)));vals=[[float(x) for x in hits[rays==i,0] if 9<x<18] for i in range(16)] if len(hits) else []
  full=[sorted(v) for v in vals if len(v)>=2]
  if len(full)<12:continue
  centers=np.array([[np.mean(v),0,0] for v in full]);free=not any(m.contains(centers))
  if not free:continue
  candidates.append(dict(component=g['mesh'],source_id=g.get('source_id'),source_name=g.get('source_name'),ray_intersections_mm=full,seat_mm=[min(max(v) for v in full),max(max(v) for v in full)]))
 rows.append(dict(motor_body=mot['body'],motor_index=mot['index'],integral_retainer_candidates=candidates))
(O/'passive-centers.json').write_text(json.dumps({'method':'16exactraysatradius1.6aroundrearaxis; sourceprintedpartcenterfree;capturedshouldersinrearaxialrange9..18mm','motor_centers':rows},indent=2))
for r in rows:print(r['motor_body'],r['motor_index'],[(c['component'],c['seat_mm']) for c in r['integral_retainer_candidates']])
