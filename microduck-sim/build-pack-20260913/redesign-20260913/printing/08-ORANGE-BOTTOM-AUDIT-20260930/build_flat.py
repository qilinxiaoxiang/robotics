from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,numpy as np
import analyze_bottom as a
D=Path(__file__).resolve().parent
E.register_namespace('',a.N[1:-1]);E.register_namespace('p',a.PN[1:-1])
c=json.loads((D/'orientation-candidates.json').read_text()); chosen=c['parts'][0];assert chosen['name']=='community-8.stl'
with zipfile.ZipFile(a.PROJECT) as z:files={n:z.read(n) for n in z.namelist()}
r=E.fromstring(files['3D/3dmodel.model']);changes=[]
for it in r.find(a.N+'build'):
 old=a.matrix(it.get('transform'));new=old.copy()
 if it.get('objectid')==chosen['object_id']:new=np.array(chosen['rigid_world_delta_transform_4x4'])@old
 it.set('transform',' '.join(f'{v:.15g}' for v in new[:3,:].T.ravel()))
 changes.append({'objectid':it.get('objectid'),'before':old.tolist(),'after':new.tolist()})
files['3D/3dmodel.model']=E.tostring(r,encoding='utf-8',xml_declaration=True)
out=D/'MicroDuck_Elegoo_orange_FLAT_editable.3mf'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for n,v in files.items():
  if n.startswith('Metadata/') and n not in ['Metadata/model_settings.config','Metadata/project_settings.config']:continue
  z.writestr(n,v)
(D/'adjustment.json').write_text(json.dumps({'source':str(a.PROJECT),'source_sha256':a.sha(a.PROJECT),'changes':changes,'cut_mm':0,'project':str(out)},indent=2))
print(out)
