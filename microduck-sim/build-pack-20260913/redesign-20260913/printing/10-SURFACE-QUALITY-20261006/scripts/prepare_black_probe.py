from pathlib import Path
import sys,json,zipfile,xml.etree.ElementTree as E,numpy as np
from prepare_surface_projects import matrix,meshvertices,N,PN
D=Path(__file__).resolve().parents[1];source=D/'projects/Elegoo/black/MicroDuck_Elegoo_black_SURFACE_editable.3mf';out=D/'intermediate/Elegoo/black/three-rotated-probe';out.mkdir(parents=True,exist_ok=True);selected={'36':(42,42),'40':(112,42),'42':(182,42)}
with zipfile.ZipFile(source) as z:members={n:z.read(n) for n in z.namelist()}
rt=E.fromstring(members['3D/3dmodel.model']);st=E.fromstring(members['Metadata/model_settings.config']);objects={x.get('id'):x for x in rt.find(N+'resources')};E.register_namespace('',N[1:-1]);E.register_namespace('p',PN[1:-1])
for i in list(rt.find(N+'build')):
 oid=i.get('objectid')
 if oid not in selected:rt.find(N+'build').remove(i);continue
 m=matrix(i.get('transform'));v=meshvertices(members,objects[oid]);vv=v@m[:3,:3].T+m[:3,3];center=(vv.min(0)+vv.max(0))/2;m[:2,3]+=np.array(selected[oid])-center[:2];i.set('transform',' '.join(f'{x:.15g}' for x in m[:3,:].T.ravel()))
for o in list(rt.find(N+'resources')):
 if o.get('id') not in selected:rt.find(N+'resources').remove(o)
for o in list(st):
 if o.tag=='object' and o.get('id') not in selected:st.remove(o)
for plate in st.findall('plate'):
 for i in list(plate):
  if i.tag=='model_instance' and i.find("metadata[@key='object_id']").get('value') not in selected:plate.remove(i)
cfg=json.loads(members['Metadata/project_settings.config']);cfg['filename_format']='black-three-rotated-probe.gcode';members['Metadata/project_settings.config']=json.dumps(cfg).encode();members['3D/3dmodel.model']=E.tostring(rt,encoding='utf-8',xml_declaration=True);members['Metadata/model_settings.config']=E.tostring(st,encoding='utf-8',xml_declaration=True);dest=out/'black-three-rotated-probe.3mf'
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
 for n,data in members.items():z.writestr(n,data)
print(dest)
