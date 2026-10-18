from pathlib import Path
import json,numpy as np
O=Path(__file__).resolve().parent; ns={'__file__':str(O/'audit_motor_interfaces.py')};exec((O/'audit_motor_interfaces.py').read_text().rsplit('rows=[]',1)[0],ns)
rows=[]
for mot in ns['motors']:
 local=[(g,m.copy().apply_transform(np.linalg.inv(mot['world']))) for g,m in ns['prints']]; local=[(g,m) for g,m in local if np.all(m.bounds[0]<[18,11,10]) and np.all(m.bounds[1]>[-18,-11,-25])]
 for sign in [-1,1]:
  for yz in [(8,7.5),(-8,7.5),(8,-22.5),(-8,-22.5)]:
   a=np.arange(8)*np.pi/4+.123; origin=np.c_[np.full(8,-50),np.array(yz)+np.c_[np.cos(a),np.sin(a)]*1.5]; target=[]
   for g,m in local:
    hits,rays,_=m.ray.intersects_location(origin,np.tile([1,0,0],(8,1)))
    if not len(hits):continue
    vals=[[float(x*sign) for x in sorted(hits[rays==i,0]) if 11.49<x*sign<18] for i in range(8)]
    pairs=[sorted(v) for v in vals if len(v)>=2 and max(v)-min(v)>.3]
    if len(pairs)<3:continue
    mid=np.median([np.mean(v) for v in pairs]);solid=bool(m.contains([[sign*mid,*yz]])[0])
    if solid:continue
    target.append(dict(part=g['mesh'],part_body=g['body'],part_index=g['index'],source_id=g.get('source_id'),rays=vals,occupied_rays=len(pairs),outer_face_range_mm=[min(max(v) for v in pairs),max(max(v) for v in pairs)]))
   rows.append(dict(motor_body=mot['body'],motor_index=mot['index'],side=sign,yz=yz,parts=target))
(O/'all-case-candidates.json').write_text(json.dumps({'method':'All120motorcasecorneraxes: centerfreeand>=3of8radialrayscrossprintedwebwithin11.49..18mmfrommotormidplane; directrayconfirmationcatchesopenUslots too. Excludesintegrallocatingpins.','candidates':rows},indent=2))
for r in rows:
 if r['parts']:print(r['motor_body'],r['motor_index'],r['side'],r['yz'],[(p['part'],p['occupied_rays'],p['outer_face_range_mm']) for p in r['parts']])
