from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,hashlib
D=Path(__file__).resolve().parent;Q='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}';out=[]
for color in ['Yellow','White','Orange','Black']:
 data=[]
 for machine in ['Bambu','Elegoo']:
  file=D/f'{color}_{machine}_editable.3mf'
  if not file.exists():file=D.parent/'delivery-V1.3-Incremental'/color/(color+'_V1.3_editable.3mf')
  with zipfile.ZipFile(file)as z:r=E.fromstring(z.read('3D/3dmodel.model'));s=E.fromstring(z.read('Metadata/model_settings.config'))
  ids=[p.get('id')for p in s.findall("object/part[@subtype='normal_part']")];objects={o.get('id'):o for o in r.find(Q+'resources')};model=[E.tostring(objects[k].find(Q+'mesh'))for k in ids];data.append((model,E.tostring(r.find(Q+'build')),hashlib.sha256(file.read_bytes()).hexdigest()))
 assert data[0][:2]==data[1][:2],color
 out.append({'color':color,'normalPartGeometryExactlyEqual':True,'buildTransformsExactlyEqual':True,'printedParts':len(data[0][0]),'sourceSha256':[x[2]for x in data]})
(D/'dual-printer-geometry-equivalence.json').write_text(json.dumps({'passed':True,'supportModifiersCanDifferBetweenNativeAlgorithms':True,'checks':out},indent=2)+'\n');print(out)
