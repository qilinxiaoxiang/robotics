from pathlib import Path
import json,numpy as np,trimesh,manifold3d as md,cadquery as cq
O=Path(__file__).resolve().parent;ns={'__file__':str(O/'audit_motor_interfaces.py')};exec((O/'audit_motor_interfaces.py').read_text().rsplit('rows=[]',1)[0],ns)
def man(m):return md.Manifold(md.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
report=json.loads((O/'joint-fasteners.json').read_text());out=[]
# Manufacturer motor solids; separate optional rear horn/cap/retainer omitted.
shape=cq.importers.importStep(str(O/'sources/X330_3d.stp')).val()
Tsource=np.array([[0,0,-1,-8],[-1,0,0,0],[0,1,0,0],[0,0,0,1]],float)
rear_screw=shape.Solids()[12].BoundingBox()
assert abs(rear_screw.xlen-5.5)<1e-4 and abs(rear_screw.ylen-5.5)<1e-4
assert 0 < -20.7-rear_screw.zmin < 1.6
head_shape=shape.Solids()[12].intersect(cq.Workplane('XY').box(10,10,4).translate((0,0,-22.7)).val())
v,f=head_shape.tessellate(.01)
rear_head=trimesh.Trimesh([[q.x,q.y,q.z] for q in v],f,process=False).apply_transform(Tsource)
parts=[]
for i,s in enumerate(shape.Solids()):
 if i in (10,11,12):continue
 v,f=s.tessellate(.03); parts.append(trimesh.Trimesh([[q.x,q.y,q.z] for q in v],f,process=False))
motor_native=trimesh.util.concatenate(parts).apply_transform(Tsource)

for c in report['connections']:
 body,_,idx=c['frame'].split(':');idx=int(idx.split()[0]);mot=next(m for m in ns['motors'] if m['body']==body and m['index']==idx);side=c['side'];yz=c['hole_centers_mm'][0][1:];datum=14.5 if c['category']=='horn' else 11.5
 p=(max(c['stack_mm'])+c['washer_mm']) if c['category']=='rear_center' else datum+max(c['stack_mm'])
 diameter,height=(5.5,1.6) if c['category']=='rear_center' else (4,1.72)
 h=md.Manifold.cylinder(height,diameter/2,diameter/2,64);mesh=h.to_mesh();mm=trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False)
 T=np.array([[0,0,side,side*p],[1,0,0,yz[0]],[0,side,0,yz[1]],[0,0,0,1]],float);mm.apply_transform(T)
 if c['category']=='rear_center':
  mm=rear_head.copy();mm.apply_translation([p-12.7,0,0])
 a=man(mm);bad=[]
 for g,wm in ns['prints']:
  m=wm.copy().apply_transform(np.linalg.inv(mot['world']))
  if np.any(m.bounds[0]>mm.bounds[1]) or np.any(m.bounds[1]<mm.bounds[0]):continue
  vol=float((a^man(m)).volume())
  if vol>.01:bad.append(dict(part=g['mesh'],part_body=g['body'],volume_mm3=vol))
 for other in ns['motors']:
  m=motor_native.copy().apply_transform(np.linalg.inv(mot['world'])@other['world'])
  if np.any(m.bounds[0]>mm.bounds[1]) or np.any(m.bounds[1]<mm.bounds[0]):continue
  vol=float((a^man(m)).volume())
  if vol>.01:bad.append(dict(part='manufacturer_motor',part_body=other['body'],part_index=other['index'],volume_mm3=vol))
 out.append(dict(id=c['id'],servo=c['servo_ids'][0],part=c['component'],category=c['category'],head_diameter_mm=diameter,head_height_mm=height,overlaps=bad))
r={'passed':all(not x['overlaps'] for x in out),'head_envelope_mm':{'M2':{'diameter':4,'height':1.72},'M2.6':{'diameter':5.5,'height':1.6}},'rear_head_profile':'Actual manufacturer STEP solid12 clipped at under-head plane z=-20.7, not bounding cylinder; requires matching ROBOTIS BHS profile', 'motor_geometry':'Manufacturer X330 STEP solids excluding optional rear horn/cap/retainer, transformed into each installed motor frame','checks':out};(O/'screw-head-clearance.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='checks'}));print(json.dumps([x for x in out if x['overlaps']],indent=2))
