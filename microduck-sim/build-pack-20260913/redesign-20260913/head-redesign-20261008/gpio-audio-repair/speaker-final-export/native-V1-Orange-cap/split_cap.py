from pathlib import Path
import zipfile,xml.etree.ElementTree as E,hashlib,json
D=Path(__file__).resolve().parent;R=D.parents[3];src=R/'printing/12-REPAIR-V1-20261008/staging-projects/MicroDuck_Elegoo_Orange_ASSEMBLY_editable.3mf';dst=D/'Orange_cap_editable.3mf';Q='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}';E.register_namespace('',Q[1:-1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with zipfile.ZipFile(src) as z:files={n:z.read(n)for n in z.namelist()}
m=E.fromstring(files['3D/3dmodel.model']);res=m.find(Q+'resources');old=res.find(Q+"object[@id='1']");before=E.tostring(old)
for obj in list(res):
 if obj.get('id')!='1':res.remove(obj)
build=m.find(Q+'build')
for item in list(build):
 if item.get('objectid')!='1':build.remove(item)
s=E.fromstring(files['Metadata/model_settings.config'])
for obj in list(s.findall('object')):
 if obj.get('id')!='1':s.remove(obj)
for plate in s.findall('plate'):
 for inst in list(plate.findall('model_instance')):
  if inst.find("metadata[@key='object_id']").get('value')!='1':plate.remove(inst)
assert before==E.tostring(res[0]);files['3D/3dmodel.model']=E.tostring(m,encoding='utf-8',xml_declaration=True);files['Metadata/model_settings.config']=E.tostring(s,encoding='utf-8',xml_declaration=True)
with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as z:
 for n,data in files.items():z.writestr(n,data)
report={'source':str(src),'sourceSha256':sha(src),'project':str(dst),'projectSha256':sha(dst),'headCapMeshAndTransformUnchanged':True,'profileBytesUnchanged':True,'removedObjects':['speaker_cradle','speaker_keeper'],'retainedObjects':['head_cap'],'purpose':'Bounded isolated cap native preflight; use already accepted separate speaker G-code once, no duplicate objects.'};(D/'split-source-binding.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
