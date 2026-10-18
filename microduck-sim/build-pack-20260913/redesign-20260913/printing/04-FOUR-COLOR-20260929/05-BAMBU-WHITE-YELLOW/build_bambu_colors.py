from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,copy,subprocess,hashlib
D=Path(__file__).resolve().parent;C=D.parent;R=C.parents[1]
N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
E.register_namespace('',N[1:-1]);E.register_namespace('p','http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=R/'current-print-queue.3mf'
with zipfile.ZipFile(source) as z:orig={n:z.read(n) for n in z.namelist()}
original_files=[p for p in (R/'PRINTING').rglob('*') if p.is_file() and p.suffix in ('.3mf','.gcode') and D not in p.parents]
snapshot={'files':[{ 'path':str(p),'sha256':sha(p)} for p in original_files]}
(D/'preserved-files.json').write_text(json.dumps(snapshot,indent=2))
rows=[]
for color,h in [('WHITE','#FFFFFF'),('yellow','#FFFF00')]:
 d=D/color;d.mkdir(exist_ok=True);src=C/color/f'MicroDuck-{color}-editable.3mf'
 with zipfile.ZipFile(src) as z:
  model=E.fromstring(z.read('3D/3dmodel.model'));colorst=E.fromstring(z.read('Metadata/model_settings.config'))
 ids={x.get('objectid') for x in model.find(N+'build')}
 for it in model.find(N+'build'):
  a=list(map(float,it.get('transform').split()));a[10]+=25;it.set('transform',' '.join(f'{v:.9g}' for v in a))
 st=E.fromstring(orig['Metadata/model_settings.config'])
 for x in list(st):
  if x.tag in ('plate','assemble') or (x.tag=='object' and x.get('id') not in ids):st.remove(x)
 plate=copy.deepcopy(colorst.find('plate'));plate.find("metadata[@key='plater_name']").set('value',f'{color}-Bambu');st.append(plate)
 cfg=json.loads(orig['Metadata/project_settings.config']);cfg['filament_colour']=[h];cfg['extruder_colour']=[h]
 project=d/f'MicroDuck_Bambu_{color}_editable.3mf'
 with zipfile.ZipFile(project,'w',zipfile.ZIP_DEFLATED) as z:
  for n,data in orig.items():
   if n.startswith('Metadata/') and n not in ('Metadata/project_settings.config','Metadata/model_settings.config'):continue
   if n=='3D/3dmodel.model':data=E.tostring(model,encoding='utf-8',xml_declaration=True)
   if n=='Metadata/model_settings.config':data=E.tostring(st,encoding='utf-8',xml_declaration=True)
   if n=='Metadata/project_settings.config':data=json.dumps(cfg).encode()
   z.writestr(n,data)
 rows.append({'color':color,'source_color_project':str(src),'source_sha256':sha(src),'project':str(project),'project_sha256':sha(project),'count':len(ids),'whole_plate_translation_mm':[0,25,0]})
(D/'conversion-manifest.json').write_text(json.dumps({'original_bambu_project':str(source),'original_bambu_sha256':sha(source),'colors':rows},indent=2))
for r in rows:
 d=Path(r['project']).parent;name=f'MicroDuck_Bambu_{r["color"]}.gcode.3mf'
 cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--arrange','0','--orient','0','--slice','1','--min-save','--export-3mf',name,'--outputdir',str(d),r['project']]
 (d/'command.json').write_text(json.dumps(cmd,indent=2))
 with (d/'slice.log').open('w') as log:run=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 (d/'native-exit.json').write_text(json.dumps({'exit_code':run.returncode}));print(r['color'],'native slice exit',run.returncode,flush=True)
