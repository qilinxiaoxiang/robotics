from pathlib import Path
import json,hashlib,trimesh as tm,numpy as np,zipfile,shutil
P=Path(__file__).resolve().parent;R=P.parent.parent
rows=json.loads((P/'orientation-preparation.json').read_text())['parts'];seen=set();reports=[]
for r in rows:
 key='neck_m2_spacer' if r['key'].startswith('neck_m2_spacer_') else r['key']
 if key in seen:continue
 seen.add(key);source=R/r['source'];m=tm.load(source,force='mesh');assert m.is_watertight and m.is_volume
 m.apply_transform(np.array(r['printTransform']));target=P/'delivery'/r['color']/(key+('_qty4' if key=='neck_m2_spacer' else '_qty1')+'.stl')
 with target.open('w') as f:
  f.write('solid MicroDuck_V1p1\n')
  for normal,triangle in zip(m.face_normals,m.triangles):
   f.write(' facet normal '+' '.join(repr(float(x)) for x in normal)+'\n  outer loop\n')
   for v in triangle:f.write('   vertex '+' '.join(repr(float(x)) for x in v)+'\n')
   f.write('  endloop\n endfacet\n')
  f.write('endsolid MicroDuck_V1p1\n')
 read=tm.load(target,force='mesh');assert read.is_watertight and read.is_volume,(key,read.is_watertight)
 reports.append({'key':key,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'watertight':True,'volume':True,'format':'ASCII STL float64 coordinates','sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'triangles':len(read.faces)})
for f in (P/'staging-projects').glob('*.3mf'):
 color=next(c for c in ['Yellow','White','Orange','Black'] if '_'+c+'_' in f.name);shutil.copyfile(f,P/'delivery'/color/(color+'_V1_editable.3mf'))
(P/'delivery-stl-readback-v11.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps({'parts':len(reports),'allReadbackWatertight':True}))
