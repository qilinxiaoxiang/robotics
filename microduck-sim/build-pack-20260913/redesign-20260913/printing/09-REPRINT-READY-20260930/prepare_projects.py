from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,sys,hashlib,copy
import numpy as np
D=Path(__file__).resolve().parent;P=D.parent;C=P/'04-FOUR-COLOR-20260929';K=C/'07-COMPACT-CENTER-20260929'
sys.path.insert(0,str(P/'08-ORANGE-BOTTOM-AUDIT-20260930'));import analyze_bottom as a
N=a.N;E.register_namespace('',N[1:-1]);E.register_namespace('p',a.PN[1:-1])
report=json.loads((D/'orientation-audit.json').read_text());rows=report['parts']
for r in rows:
 if 'delta4x4' in r:r['candidate_delta4x4']=r.pop('delta4x4')
 r['applied_delta4x4']=r['candidate_delta4x4'] if r['decision']=='rotate' else np.eye(4).tolist()
report['coverage']={'instance_count':len(rows),'unique_manifest_instances':len({r['manifest_instance_index'] for r in rows}),'expected':89,'passed':len(rows)==89 and len({r['manifest_instance_index'] for r in rows})==89}
report['candidate_semantics']='candidate_delta4x4 and sections_after are hypothetical. applied_delta4x4 is identity for keep. Packing translation is separate.'
(D/'orientation-audit.json').write_text(json.dumps(report,indent=2)+'\n')
out=[]
for machine in ['Elegoo','Bambu']:
 for group in ['old-orange-plate1','old-black-plate5','orange','yellow','WHITE','black']:
  selected=[r for r in rows if r['group']==group];src=Path(selected[0]['source_project'])
  if machine=='Bambu':
   if group.startswith('old-'):src=P/'02-PROJECTS/Bambu/current-print-queue.3mf'
   elif group in ['WHITE','yellow']:src=K/f'Bambu/{group}/MicroDuck_Bambu_{group}_COMPACT_editable.3mf'
   else:continue
  with zipfile.ZipFile(src) as z:files={n:z.read(n) for n in z.namelist()}
  root=E.fromstring(files['3D/3dmodel.model']);st=E.fromstring(files['Metadata/model_settings.config']);ids={r['object_id'] for r in selected};inst={i.find("metadata[@key='object_id']").get('value'):i for p in st.findall('plate') for i in p.findall('model_instance')}
  for container in [root.find(N+'resources'),root.find(N+'build')]:
   for el in list(container):
    if el.get('id',el.get('objectid')) not in ids:container.remove(el)
  # Correct rotation in each machine's own frame, then center model group. Original Bambu/Elegoo transforms verified equivalent below.
  a.PROJECT=src;meshes={oid:m for oid,name,m in a.load_meshes() if oid in ids};adjust={}
  for r in selected:
   oid=r['object_id'];m=meshes[oid];T=np.eye(4)
   if r['decision']=='rotate':
    R=np.array(r['applied_delta4x4'])[:3,:3];center=m.bounds.mean(0);T[:3,:3]=R;T[:3,3]=center-R@center;m.apply_transform(T);T[2,3]-=m.bounds[0,2];m.apply_translation([0,0,-m.bounds[0,2]])
   adjust[oid]=T
  bounds=np.array([m.bounds for m in meshes.values()]);offset=np.array([128,128])-(bounds[:,0,:2].min(0)+bounds[:,1,:2].max(0))/2
  for el in root.find(N+'build'):
   oid=el.get('objectid');T=adjust[oid];T[:2,3]+=offset;M=T@a.matrix(el.get('transform'));el.set('transform',' '.join(f'{x:.12g}' for x in M[:3,:].T.ravel()))
  for el in list(st):
   if el.tag in ['plate','assemble'] or (el.tag=='object' and el.get('id') not in ids):st.remove(el)
  pe=E.SubElement(st,'plate')
  for key,val in [('plater_id','1'),('plater_name',group),('locked','false')]:E.SubElement(pe,'metadata',key=key,value=val)
  for r in selected:pe.append(copy.deepcopy(inst[r['object_id']]))
  dest=D/machine/group/f'MicroDuck_{machine}_{group}_REPRINT_editable.3mf';dest.parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
   for n,data in files.items():
    if n.startswith('Metadata/') and n not in ['Metadata/project_settings.config','Metadata/model_settings.config']:continue
    if n=='3D/3dmodel.model':data=E.tostring(root,encoding='utf-8',xml_declaration=True)
    elif n=='Metadata/model_settings.config':data=E.tostring(st,encoding='utf-8',xml_declaration=True)
    z.writestr(n,data)
  a.PROJECT=dest;loaded=a.load_meshes();checks=[]
  with zipfile.ZipFile(dest) as z:
   geometry_same=all(z.read(n)==data for n,data in files.items() if n.startswith('3D/') and n!='3D/3dmodel.model')
   settings_same=z.read('Metadata/project_settings.config')==files['Metadata/project_settings.config']
  for oid,name,m in loaded:
   expected=meshes[oid].copy();expected.apply_translation([*offset,0]);checks.append(float(np.max(np.abs(expected.vertices-m.vertices)))<1e-6)
  if group in ['orange','yellow','WHITE']:
   dest.write_bytes(src.read_bytes())
  out.append({'project_byte_identical_to_source':dest.read_bytes()==src.read_bytes(),'machine':machine,'group':group,'source':str(src),'source_sha256':a.sha(src),'project':str(dest),'sha256':a.sha(dest),'object_ids':sorted(ids,key=int),'count':len(ids),'mesh_members_byte_identical':geometry_same,'machine_process_filament_settings_byte_identical':settings_same,'transforms_verified':all(checks),'source_group_model_center_translation_mm':offset.tolist(),'note':'Model-centered preparation only. Native reslice, support/brim footprint centering and final export pending.'})
  print(machine,group,len(ids),all(checks),flush=True)
assert all(q['mesh_members_byte_identical'] and q['transforms_verified'] and q['machine_process_filament_settings_byte_identical'] for q in out)
(D/'project-preparation.json').write_text(json.dumps({'projects':out,'geometry_preparation_passed':True,'native_export_acceptance':False},indent=2)+'\n')
