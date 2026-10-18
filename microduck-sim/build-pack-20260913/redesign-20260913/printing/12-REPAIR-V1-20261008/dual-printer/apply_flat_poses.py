from pathlib import Path
import json,zipfile,hashlib,xml.etree.ElementTree as E
D=Path(__file__).resolve().parent;V=D.parent;H=V.parents[1]/'head-redesign-20261008';S=V/'delivery-V1.3-Incremental';N={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
source=H/'gpio-audio-repair/orientation-readonly-review/flat-base-pose-candidates.json'; poses=json.loads(source.read_text())['parts']; prep=json.loads((D/'preparation.json').read_text());rows=prep['rows'];changes=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for pose in poses:
 for machine in ['Bambu','Elegoo']:
  color=pose['color']; oldrow=next((r for r in rows if r['color']==color and r['machine']==machine),None)
  src=Path(oldrow['project']) if oldrow else S/color/f'{color}_V1.3_editable.3mf'; dst=D/f'{color}_{machine}_editable.3mf'
  with zipfile.ZipFile(src) as z:content={n:z.read(n)for n in z.namelist()}
  with zipfile.ZipFile(pose['sourceProject']) as z:
   # Prove candidate refers to exactly this mesh; Application metadata and transforms may differ.
   for n in content:
    if n.startswith('3D/'):
     a=E.fromstring(content[n]);b=E.fromstring(z.read(n));assert E.tostring(a.find('m:resources',N))==E.tostring(b.find('m:resources',N)),n
  root=E.fromstring(content['3D/3dmodel.model']);item=next(i for i in root.find('m:build',N)if i.get('objectid')==pose['objectId']);old=item.get('transform');item.set('transform',pose['candidateBuildTransform'])
  content['3D/3dmodel.model']=E.tostring(root,encoding='utf-8',xml_declaration=True)
  before=sha(src)
  with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED)as z:
   for n,b in content.items():z.writestr(n,b)
  row=dict(oldrow)if oldrow else {'color':color,'machine':machine,'source':str(src),'sourceSha256':before,'configDiff':{}}
  row.update(project=str(dst),projectSha256=sha(dst),geometryAndTransformsRetained=False,geometryRetained=True,orientationEvidence=str(source),orientationEvidenceSha256=sha(source),explicitBuildTransformOnlyChange={'objectId':pose['objectId'],'before':old,'after':pose['candidateBuildTransform']})
  if oldrow:rows.remove(oldrow)
  rows.append(row);changes.append(row)
prep['rows']=rows;(D/'preparation.json').write_text(json.dumps(prep,indent=2)+'\n');(D/'flat-pose-application.json').write_text(json.dumps(changes,indent=2)+'\n');print([(r['color'],r['machine'])for r in changes])
