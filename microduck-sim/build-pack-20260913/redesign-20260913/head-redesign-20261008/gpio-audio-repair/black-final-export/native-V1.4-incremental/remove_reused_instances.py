"""Remove only audited reused object instances; retain all other geometry, poses and profiles."""
from pathlib import Path
import argparse,zipfile,xml.etree.ElementTree as E,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--remove',nargs='+',required=True);p.add_argument('--audit',type=Path,required=True);a=p.parse_args();assert a.source.resolve()!=a.output.resolve();assert a.audit.is_file()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();N='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';Q='{'+N+'}';E.register_namespace('',N)
with zipfile.ZipFile(a.source)as z:members={x.filename:(x,z.read(x.filename))for x in z.infolist()}
root=E.fromstring(members['3D/3dmodel.model'][1]);settings=E.fromstring(members['Metadata/model_settings.config'][1]);resources=root.find(Q+'resources');build=root.find(Q+'build');objects={r.get('id'):r for r in resources.findall(Q+'object')};remove={i for i,o in objects.items()if o.get('name')in a.remove};assert len(remove)==len(a.remove),('remove key missing or duplicated',a.remove)
assert all(objects[i].find(Q+'components')is None for i in remove),'Compound object removal requires explicit review'
kept={i:E.tostring(o)for i,o in objects.items()if i not in remove};keptbuild={i.get('objectid'):dict(i.attrib)for i in build if i.get('objectid')not in remove};keptsettings={o.get('id'):E.tostring(o)for o in settings.findall('object')if o.get('id')not in remove}
for i in remove:resources.remove(objects[i])
for i in list(build):
 if i.get('objectid')in remove:build.remove(i)
for o in list(settings.findall('object')):
 if o.get('id')in remove:settings.remove(o)
for plate in settings.findall('plate'):
 for inst in list(plate.findall('model_instance')):
  if any(m.get('key')=='object_id'and m.get('value')in remove for m in inst.findall('metadata')):plate.remove(inst)
assert kept=={o.get('id'):E.tostring(o)for o in resources.findall(Q+'object')}
assert keptbuild=={i.get('objectid'):dict(i.attrib)for i in build}
assert keptsettings=={o.get('id'):E.tostring(o)for o in settings.findall('object')}
updates={'3D/3dmodel.model':E.tostring(root,encoding='utf-8',xml_declaration=True),'Metadata/model_settings.config':E.tostring(settings,encoding='utf-8',xml_declaration=True)};a.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(a.output,'w',zipfile.ZIP_DEFLATED)as z:
 for name,(info,data)in members.items():z.writestr(info,updates.get(name,data))
with zipfile.ZipFile(a.output)as z:
 for name,(_,data)in members.items():
  if name not in updates:assert z.read(name)==data
r={'source':str(a.source.resolve()),'sourceSha256':sha(a.source),'audit':str(a.audit.resolve()),'auditSha256':sha(a.audit),'output':str(a.output.resolve()),'outputSha256':sha(a.output),'removed':[{'id':i,'key':objects[i].get('name')}for i in sorted(remove)],'retainedCount':len(kept),'retainedGeometryExact':True,'retainedTransformsExact':True,'retainedObjectSettingsExact':True,'projectSettingsBytesUnchanged':True,'repacked':False,'resliced':False,'sourceScriptSha256':sha(Path(__file__))};a.output.with_suffix('.edit-proof.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
