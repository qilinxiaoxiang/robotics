from pathlib import Path
import json,numpy as np,trimesh,manifold3d as md
O=Path(__file__).resolve().parent;ns={'__file__':str(O/'audit_motor_interfaces.py')};exec((O/'audit_motor_interfaces.py').read_text().rsplit('rows=[]',1)[0],ns)
def man(m):return md.Manifold(md.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
report=json.loads((O/'joint-fasteners.json').read_text());out=[]
for c in report['connections']:
 if c['category']!='rear_center':continue
 body,_,idx=c['frame'].split(':');idx=int(idx.split()[0]);mot=next(m for m in ns['motors'] if m['body']==body and m['index']==idx)
 check=[]
 if c['washer_mm']:
  # annulus axis X; start at verified shoulder, positive outward direction
  ring=md.Manifold.cylinder(.5,2.5,2.5,64)-md.Manifold.cylinder(.5,1.35,1.35,64)
  mesh=ring.to_mesh();mm=trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False);T=np.array([[0,0,1,c['stack_mm'][1]],[1,0,0,0],[0,1,0,0],[0,0,0,1]],float);mm.apply_transform(T);check.append(('washer',mm))
 if c['component'].startswith('Separate'):
  for oid,offset in [(55,12.425),(59,12.)]:
   mm=ns['source_ns']['mesh']('3D/3dmodel.model',str(oid));T=np.array([[0,0,-1,offset],[1,0,0,0],[0,-1,0,0],[0,0,0,1]],float);mm.apply_transform(T);check.append(('idler_horn' if oid==55 else 'idler_cap',mm))
 for label,add in check:
  overlaps=[]
  for g,wm in ns['prints']:
   m=wm.copy().apply_transform(np.linalg.inv(mot['world']))
   if np.any(m.bounds[0]>add.bounds[1]) or np.any(m.bounds[1]<add.bounds[0]):continue
   volume=float((man(add)^man(m)).volume())
   if volume>.001:overlaps.append({'part':g['mesh'],'volume_mm3':volume})
  out.append({'servo_id':c['servo_ids'][0],'part':label,'overlaps':overlaps,'passed':not overlaps})
result={'passed':all(x['passed'] for x in out),'scope':'Native manifold intersection of selected washers and two separate idler assemblies with actual source meshes in motor-localframe; doesnotestablishphysical friction','checks':out};(O/'retainer-clearance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert result['passed']
