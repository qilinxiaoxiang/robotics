from pathlib import Path
import sys,json,trimesh
H=Path(__file__).resolve().parent;O=H.parents[1]/'hardware-design-20260912/whole-robot-20260912'
sys.path.insert(0,str(O/'assembly'));from assembly_fk import fk,raw
sys.path.insert(0,str(O/'electrical/head-layout'));from geometry import man,hits
new=man(trimesh.load(H/'mouth-support/motor-support-coaxial-assembly.stl'))
g=next(g for g in fk()[1] if g['body']=='jaw_soft' and g['mesh']=='motor_support');added=new-man(raw(g['mesh']).apply_transform(g['local']))
fixed=[]
for x in fk()[1]:
 if x['body']=='jaw_soft' and x['mesh'] not in ['motor_support','seeed_bearing__configuration_default']:
  m=raw(x['mesh']).apply_transform(x['local']);fixed.append((x['mesh']+str(x['index']),m,man(m)))
for p in (O/'electrical/head-layout/final').glob('*_assembly.stl'):
 if p.name.startswith('head_cap_'):p=H/'mouth-clearance/head-cap-mouth-clearance-assembly.stl'
 m=trimesh.load(p,force='mesh');fixed.append((p.name,m,man(m)))
r={'added_material_hits':hits(added,fixed),'checked_objects':len(fixed),'basis':'Added bushing material against all source head parts and current head assembly envelopes; only replaced mouth bearing omitted.'};(H/'mouth-support/static-check.json').write_text(json.dumps(r,indent=2));print(r);assert not r['added_material_hits']
