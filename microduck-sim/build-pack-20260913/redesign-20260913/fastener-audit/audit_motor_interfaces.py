from pathlib import Path
import sys,json,hashlib,collections
import numpy as np,trimesh
OUT=Path(__file__).resolve().parent; A=OUT.parents[1]/'assembly'; SIM=OUT.parents[2]
sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'))
from assembly_fk import fk,raw,XML
ns={'__file__':str(A/'inspect_joint_interfaces.py')};exec((A/'inspect_joint_interfaces.py').read_text().split('rows=[]')[0],ns); circles=ns['circles']
source_ns={'__file__':str(A/'prepare_geometry.py')};exec((A/'prepare_geometry.py').read_text().split('rows=[]')[0],source_ns)
inventory=json.loads((A/'community-print-inventory.json').read_text())['objects']
refinements={r['id']:r for r in json.loads((A/'source-surface-refinement.json').read_text())}
b,gs=fk(); motors=[g for g in gs if g['mesh']=='xl330']; prints=[]
exclude={'xl330','np_f970','pcb__raspberry_pi_zero_2_w','elec_rpi_robot_hat_pcb','speaker','lens','m12_lens_holder','top_head_shell'}
for g in gs:
 if g['mesh'] in exclude or g['mesh'].startswith('seeed_bearing'): continue
 matched=next((r for r in inventory if r.get('reference_mesh')==g['mesh']),None)
 if matched:
  m=source_ns['mesh']('3D/3dmodel.model',str(matched['id']))
  ref=refinements.get(matched['id']);T=np.eye(4);T[:3,:3]=ref['rotation'] if ref else matched['source_to_reference_rotation'];T[:3,3]=ref['translation'] if ref else matched['source_to_reference_translation_mm'];m.apply_transform(g['world']@T);g=dict(g,source_id=matched['id'],source_name=matched['source_name'])
 else:m=raw(g['mesh']).apply_transform(g['world'])
 if g['mesh']=='motor_support':
  m=trimesh.load(A/'mouth-support/motor-support-coaxial-assembly.stl').apply_transform(b[g['body']]);g=dict(g,source_id=None,source_name='motor-support-coaxial-print.stl')
 if g['mesh']=='power_support':
  m=trimesh.load(SIM/'hardware-design-20260912/whole-robot-20260912/assembly/compact-battery/power-support-integrated-body.stl');g=dict(g,source_id=None,source_name='power-support-integrated-print.stl')
 prints.append((g,m))
rows=[]
for motor in motors:
 mi=np.linalg.inv(motor['world']); features=[]
 for g,wm in prints:
  m=wm.copy().apply_transform(mi)
  if np.any(m.bounds[0]>[24,12,12]) or np.any(m.bounds[1]<[-24,-12,-25]):continue
  for sign in [-1,1]:
   for depth in np.arange(9.125,24,.25):
    x=sign*depth
    if not m.bounds[0,0]<x<m.bounds[1,0]:continue
    for c in circles(m,0,x):
     y,z=c['center_other_axes']; r=c['radius']
     kind=None
     if abs(np.linalg.norm([y,z])-6)<.12 and .7<r<2.5:kind='output'
     if min(np.linalg.norm(np.array([y,z])-p) for p in [(8,7.5),(-8,7.5),(8,-22.5),(-8,-22.5)])<.12 and .7<r<2.5:kind='case'
     if kind and m.contains([[x,y,z]])[0]:kind='locating_peg'
     if kind:features.append(dict(part=g['mesh'],part_body=g['body'],part_index=g['index'],source_id=g.get('source_id'),kind=kind,side=sign,x=float(x),yz=[round(y,3),round(z,3)],radius=round(r,3)))
 groups=collections.defaultdict(list)
 for f in features:groups[(f['part'],f['part_body'],f['part_index'],f['kind'],f['side'],tuple(round(v,1) for v in f['yz']),round(f['radius'],1))].append(f['x'])
 holes=[dict(part=k[0],part_body=k[1],part_index=k[2],kind=k[3],side=k[4],yz=k[5],radius_mm=k[6],sampled_x_range_mm=[min(v),max(v)],sample_count=len(v)) for k,v in groups.items()]
 row=dict(motor_body=motor['body'],motor_index=motor['index'],motor_world_transform=motor['world'].tolist(),holes=holes);rows.append(row); print(motor['body'],motor['index'],len(holes),flush=True)
report={'source_xml':str(XML),'source_xml_sha256':hashlib.sha256(XML.read_bytes()).hexdigest(),'scope':'Actualcommunity3MF meshes mappedintoassembledreferenceframes using saved rigidmatches; currentpower/motor-support replacements override their supersededsourceparts. Circle range is sampled; exactheadseats are measured by followup triangleintersections.','step_mm':.25,'motor_count':len(motors),'motors':rows}
(OUT/'motor-interface-sections.json').write_text(json.dumps(report,indent=2))
