from pathlib import Path
import json,numpy as np,hashlib
OUT=Path(__file__).resolve().parent
ns={'__file__':str(OUT/'audit_motor_interfaces.py')};exec((OUT/'audit_motor_interfaces.py').read_text().rsplit('rows=[]',1)[0],ns)
report=json.loads((OUT/'motor-interface-sections.json').read_text());rows=[]
for motor in report['motors']:
 for h in motor['holes']:
  if h['radius_mm']>1.5:continue
  p,m=next((g,m) for g,m in ns['prints'] if g['mesh']==h['part'] and g['body']==h['part_body'] and g['index']==h['part_index'])
  m=m.copy().apply_transform(np.linalg.inv(motor['motor_world_transform'])); yz=np.array(h['yz']); a=np.arange(8)*np.pi/4+.123
  origins=np.c_[np.full(8,-100),yz+np.c_[np.cos(a),np.sin(a)]*1.5]
  hits,rays,_=m.ray.intersects_location(origins,np.tile([1,0,0],(8,1)))
  span=h['sampled_x_range_mm']; vals=[sorted(hits[rays==i,0]) for i in range(8)]
  near=[[x for x in v if span[0]-.35<x<span[1]+.35] for v in vals]
  depths=[v[-1]-v[0] for v in near if len(v)==2]
  row=dict(h, motor_body=motor['motor_body'],motor_index=motor['motor_index'],source_id=p.get('source_id'),source_name=p.get('source_name'),radial_probe_mm=1.5,ray_boundaries_mm=near,wall_thickness_range_mm=[round(min(depths),5),round(max(depths),5)] if depths else None)
  if depths:
   row['nominal_stack_mm']=round(float(np.median(depths)),3)
   outer=[max(abs(v[0]),abs(v[-1])) for v in near if len(v)==2]
   datum=14.5 if h['kind']=='output' else 11.5
   row['head_seat_from_motor_face_mm']=[round(min(outer)-datum,5),round(max(outer)-datum,5)]
  mid=np.array([np.mean(span),*yz,1]);row['world_center_mm']=(np.array(motor['motor_world_transform'])@mid)[:3].tolist();row['world_axis']=(np.array(motor['motor_world_transform'])[:3,:3]@np.array([h['side'],0,0])).tolist()
  rows.append(row)
result={'method':'Eight parallel exact triangle intersection rays 1.5 mm radially around each detected bore; candidate bore center and axis from native sections. Surface pairs restricted to section range +/-0.35 mm. No assumption about actual hardware blind-hole depth.','source_3mf_sha256':hashlib.sha256(ns['source_ns']['SOURCE'].read_bytes()).hexdigest(),'connections':rows}
(OUT/'joint-stack-measurements.json').write_text(json.dumps(result,indent=2))
for r in rows: print(r['motor_body'],r['motor_index'],r['part'],r['kind'],r['side'],r['yz'],r.get('nominal_stack_mm'))
