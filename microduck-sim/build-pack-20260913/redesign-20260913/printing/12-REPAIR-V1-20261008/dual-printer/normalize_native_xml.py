from pathlib import Path
import zipfile,json,re,hashlib
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/12-REPAIR-V1-20261008/dual-printer');p=json.loads((D/'preparation.json').read_text())
for row in p['rows']:
 if row['color']not in ['Yellow','Orange']:continue
 file=Path(row['project'])
 with zipfile.ZipFile(file)as z:data={n:z.read(n)for n in z.namelist()}
 with zipfile.ZipFile(D.parent/'delivery-V1.3-Incremental'/row['color']/(row['color']+'_V1.3_editable.3mf'))as z:model=z.read('3D/3dmodel.model').decode()
 if row['machine']=='Bambu':model=model.replace('OrcaSlicer-2.4.2','BambuStudio-02.08.02.61')
 transform=row['explicitBuildTransformOnlyChange']['after']
 def edit(m):
  s=m.group(0)
  if re.search(r'objectid="1"',s):return re.sub(r'transform="[^"]+"','transform="'+transform+'"',s)
  return s
 model=re.sub(r'<item\b[^>]+>',edit,model);data['3D/3dmodel.model']=model.encode()
 with zipfile.ZipFile(file,'w',zipfile.ZIP_DEFLATED)as z:
  for n,b in data.items():z.writestr(n,b)
 row['projectSha256']=hashlib.sha256(file.read_bytes()).hexdigest()
(D/'preparation.json').write_text(json.dumps(p,indent=2)+'\n')
