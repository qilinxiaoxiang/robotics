"""Prepare all10 variants without changing source mesh bytes or original projects."""
from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,numpy as np,hashlib
D=Path(__file__).resolve().parents[1];P=D.parent;N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}';PN='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}';E.register_namespace('',N[1:-1]);E.register_namespace('p',PN[1:-1])
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def matrix(s):
 m=np.eye(4);m[:3,:]=np.array(list(map(float,s.split()))).reshape(4,3).T;return m
def settyped(cfg,k,value):
 old=cfg.get(k);cfg[k]=[str(value) for _ in old] if isinstance(old,list) else str(value)
def meshvertices(members,obj):
 arrays=[]
 for c in obj.find(N+'components'):
  rt=E.fromstring(members[c.get(PN+'path').lstrip('/')]);mesh=next(x for x in rt.find(N+'resources') if x.get('id')==c.get('objectid')).find(N+'mesh');v=np.array([[float(x.get(k)) for k in ['x','y','z']] for x in mesh.find(N+'vertices')]);t=matrix(c.get('transform'));arrays.append(v@t[:3,:3].T+t[:3,3])
 return np.concatenate(arrays)
def main():
 sourcepack=json.loads((P/'09-REPRINT-READY-20260930/packaging.json').read_text());nom=json.loads((D/'geometry/nominations.json').read_text());pose={(r['group'],r['object_id']):r for r in nom['pose_candidates']};rows=[]
 for v in sourcepack['variants']:
  machine,group=v['printer'],v['group'];source=Path(v['project']);out=D/'projects'/machine/group;out.mkdir(parents=True,exist_ok=True);dest=out/f'MicroDuck_{machine}_{group}_SURFACE_editable.3mf'
  with zipfile.ZipFile(source) as z:members={n:z.read(n) for n in z.namelist()}
  root=E.fromstring(members['3D/3dmodel.model']);objects={o.get('id'):o for o in root.find(N+'resources')};cfg=json.loads(members['Metadata/project_settings.config']);st=E.fromstring(members['Metadata/model_settings.config']);names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in st.findall('object')};changes=[]
  for item in root.find(N+'build'):
   oid=item.get('objectid');old=matrix(item.get('transform'));verts=meshvertices(members,objects[oid]);before=verts@old[:3,:3].T+old[:3,3];original_center=(before.min(0)+before.max(0))/2;m=old.copy();key=(group,oid);r=pose.get(key)
   if r:
    delta=np.array(r['delta4x4']);assert np.allclose(delta[:3,:3].T@delta[:3,:3],np.eye(3),atol=1e-7);m=delta@m;vv=verts@m[:3,:3].T+m[:3,3];center=(vv.min(0)+vv.max(0))/2;m[:2,3]+=original_center[:2]-center[:2];m[2,3]-=vv[:,2].min();item.set('transform',' '.join(f'{x:.15g}' for x in m[:3,:].T.ravel()))
   after=verts@m[:3,:3].T+m[:3,3];changes.append({'object_id':oid,'name':names[oid],'nomination_selected':r is not None,'manifest_instance_index':r['manifest_instance_index'] if r else None,'source_build_transform4x4':old.tolist(),'prepared_build_transform4x4':m.tolist(),'applied_rotation_matches_nomination':bool(not r or np.allclose((m@np.linalg.inv(old))[:3,:3],np.array(r['delta4x4'])[:3,:3],atol=1e-7)),'new_bounds_mm':[after.min(0).tolist(),after.max(0).tolist()],'original_center_xy_mm':original_center[:2].tolist(),'new_center_xy_mm':((after.min(0)+after.max(0))/2)[:2].tolist(),'minimum_z_mm':float(after[:,2].min())})
  enhancements={}
  if group in ['old-orange-plate1','orange','black','yellow']:
   values={'support_top_z_distance':'.2','support_interface_top_layers':'3','support_interface_spacing':'.15','bridge_speed':'30','internal_bridge_speed':'100%','support_interface_speed':'40'}
   for k,value in values.items():enhancements[k]={'before':cfg.get(k),'after':value};settyped(cfg,k,value)
   cfg['brim_type']='auto_brim'
  if machine=='Bambu' and group=='yellow':
   # Exact closure-seat native control: restore local support/interface instead of suppressing it.
   for k in ['support_remove_small_overhang','support_interface_not_for_body']:
    enhancements[k]={'before':cfg.get(k),'after':'0'};settyped(cfg,k,'0')
  
  if machine=='Elegoo':
   profile=json.loads((P.parent/'printing-elegoo-20260929/filament.json').read_text());assert cfg['filament_id']==profile['filament_id']=='EPLAB00';cfg['filament_ids']=[profile['filament_id']]
  cfg['filament_colour']=[{'old-orange-plate1':'#FF8000','orange':'#FF8000','old-black-plate5':'#202020','black':'#202020','yellow':'#FFFF00','WHITE':'#FFFFFF'}[group]]
  
  if machine=='Bambu':
   for plate in st.findall('plate'):
    meta=plate.find("metadata[@key='bed_type']")
    if meta is None:meta=E.SubElement(plate,'metadata',{'key':'bed_type','value':'Cool Plate'})
    else:meta.set('value','Cool Plate')
   members['Metadata/model_settings.config']=E.tostring(st,encoding='utf-8',xml_declaration=True)
  cfg['filename_format']=f'MicroDuck_{machine}_{group}_SURFACE.gcode';members['Metadata/project_settings.config']=json.dumps(cfg,indent=2).encode();members['3D/3dmodel.model']=E.tostring(root,encoding='utf-8',xml_declaration=True)
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
   for n,data in members.items():
    if not n.endswith('.gcode'):z.writestr(n,data)
  with zipfile.ZipFile(dest) as z:identical=all(z.read(n)==data for n,data in members.items() if n.startswith('3D/Objects/'))
  row={'printer':machine,'group':group,'source_project':str(source),'source_project_sha256':sha(source),'project':str(dest),'project_sha256':sha(dest),'expected_count':v['expected_count'],'primary':v['primary'],'mesh_members_byte_identical':identical,'object_transforms':changes,'process_changes':enhancements,'source_archive':v['archive'],'native_export_pending':True,'filename':dest.name};assert len(changes)==row['expected_count'];assert all(r['applied_rotation_matches_nomination'] for r in changes);rows.append(row);print(machine,group,len(changes),'ready',flush=True)
 assert sum(r['expected_count'] for r in rows if r['primary'])==89
 (D/'projects/project-preparation.json').write_text(json.dumps({'variants':rows,'source_packaging':str(P/'09-REPRINT-READY-20260930/packaging.json'),'source_packaging_sha256':sha(P/'09-REPRINT-READY-20260930/packaging.json'),'nomination_sha256':sha(D/'geometry/nominations.json'),'primary_count':89,'variant_count':10,'digital_native_acceptance_pending':True},indent=2)+'\n')
if __name__=='__main__':main()
