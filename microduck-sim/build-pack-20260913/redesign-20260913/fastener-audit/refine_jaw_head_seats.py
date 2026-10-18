from pathlib import Path
import json,numpy as np,trimesh,manifold3d as md
O=Path(__file__).resolve().parent;ns={'__file__':str(O/'audit_motor_interfaces.py')};exec((O/'audit_motor_interfaces.py').read_text().rsplit('rows=[]',1)[0],ns)
def man(m):return md.Manifold(md.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
mot=next(g for g in ns['motors'] if g['body']=='jaw_soft' and g['index']==2);g,wm=next((g,m) for g,m in ns['prints'] if g['mesh']=='jaw');part=man(wm.copy().apply_transform(np.linalg.inv(mot['world'])))
rows=[]
for r in json.loads((O/'joint-stack-measurements.json').read_text())['connections']:
 if r['motor_body']!='jaw_soft' or r['motor_index']!=2 or r['kind']!='output':continue
 def overlap(seat):
  h=md.Manifold.cylinder(1.72,2,2,96);me=h.to_mesh();m=trimesh.Trimesh(me.vert_properties[:,:3],me.tri_verts,process=False);y,z=r['yz'];m.apply_transform(np.array([[0,0,-1,-14.5-seat],[1,0,0,y],[0,-1,0,z],[0,0,0,1]],float));return float((man(m)^part).volume())
 lo=max(r['head_seat_from_motor_face_mm']);hi=lo+1.;initial=overlap(lo);assert overlap(hi)<1e-5
 for _ in range(22):
  mid=(lo+hi)/2
  if overlap(mid)>1e-5:lo=mid
  else:hi=mid
 seat=hi+.001;rows.append(dict(yz=r['yz'],seat_mm=seat,initial_overlap_mm3=initial,final_overlap_mm3=overlap(seat),head_diameter_mm=4,head_height_mm=1.72))
result={'passed':all(r['final_overlap_mm3']<1e-5 for r in rows),'method':'Move nominal flat underhead bearing plane outward until exactmesh intersection of Ø4x1.72mm head becomeszero. This is actual seatingagainstcurvedsourcejaw, not a printedpartchange.0.001mm numericbuffer.','seats':rows};(O/'jaw-head-seats.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert result['passed']
