"""Isolate one preserved ankle mesh with current accepted orientation and process candidates."""
from pathlib import Path
import xml.etree.ElementTree as E,zipfile,json,hashlib,copy
D=Path(__file__).resolve().parent;BASE=D.parents[1];N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
E.register_namespace('',N[1:-1]);E.register_namespace('p','http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
SRC=BASE/'09-REPRINT-READY-20260930/Elegoo/old-orange-plate1/MicroDuck_Elegoo_old-orange-plate1_REPRINT_editable.3mf'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 with zipfile.ZipFile(SRC) as zz: original={n:zz.read(n) for n in zz.namelist()}
 rt=E.fromstring(original['3D/3dmodel.model']);build=rt.find(N+'build');item=next(i for i in build if i.get('objectid')=='20');v=list(map(float,item.get('transform').split()));v[9]=128;v[10]=128;item.set('transform',' '.join(map(str,v)))
 for i in list(build):
  if i is not item:build.remove(i)
 for o in list(rt.find(N+'resources')):
  if o.get('id')!='20':rt.find(N+'resources').remove(o)
 st=E.fromstring(original['Metadata/model_settings.config'])
 for o in list(st):
  if o.tag=='object' and o.get('id')!='20':st.remove(o)
 for plate in st.findall('plate'):
  for i in list(plate):
   if i.tag=='model_instance' and i.find("metadata[@key='object_id']").get('value')!='20':plate.remove(i)
 cfg=json.loads(original['Metadata/project_settings.config']);rows=[]
 candidates={'baseline':{},'dense_interface_bridge30':{'support_interface_top_layers':'3','support_interface_spacing':'0.15','bridge_speed':'30','internal_bridge_speed':'100%'},'dense_interface_bridge30_gap016':{'support_interface_top_layers':'3','support_interface_spacing':'0.15','bridge_speed':'30','internal_bridge_speed':'100%','support_top_z_distance':'0.16'}}
 for name,patch in candidates.items():
  out=D/name;out.mkdir(exist_ok=True);setting=copy.deepcopy(cfg);setting.update(patch);setting['filename_format']=name+'.gcode';setting['print_sequence']='by layer';setting['filament_colour']=['#FF8000'];p=out/('ankle66-'+name+'.3mf')
  with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as zz:
   for member,data in original.items():
    if member.endswith('.gcode'):continue
    if member=='3D/3dmodel.model':data=E.tostring(rt,encoding='utf-8',xml_declaration=True)
    elif member=='Metadata/model_settings.config':data=E.tostring(st,encoding='utf-8',xml_declaration=True)
    elif member=='Metadata/project_settings.config':data=json.dumps(setting,indent=2).encode()
    zz.writestr(member,data)
  mesh_members=[n for n in original if n.startswith('3D/Objects/')];same=all(zipfile.ZipFile(p).read(n)==original[n] for n in mesh_members)
  rows.append({'name':name,'project':str(p),'project_sha256':sha(p),'changes':patch,'mesh_members_byte_identical':same,'selected_object_id':'20','name_in_project':'community-66.stl','rotation_preserved_from_09':True,'source':str(SRC),'source_sha256':sha(SRC),'purpose':'isolated digital experiment, not accepted print file'})
 (D/'ankle-candidate-preparation.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
