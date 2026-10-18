from pathlib import Path
import json,hashlib,zipfile,xml.etree.ElementTree as E,subprocess,sys
D=Path(__file__).resolve().parent;C=D.parent
N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
E.register_namespace('',N[1:-1]);E.register_namespace('p','http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 if '--slice' in sys.argv:
  manifest=json.loads((D/'centering-manifest.json').read_text())
  for row in manifest['projects']:
   if '--bambu-only' in sys.argv and row['printer']!='Bambu':continue
   out=Path(row['project']).parent
   if row['printer']=='Bambu':cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--arrange','0','--orient','0','--slice','1','--min-save','--export-3mf',row['native_archive_name'],'--outputdir',str(out),row['project']]
   else:
    cmd=json.loads((C/row['color']/'native-command.json').read_text());cmd[cmd.index('--export-3mf')+1]=row['native_archive_name'];cmd[cmd.index('--outputdir')+1]=str(out);cmd[-1]=row['project']
   (out/'native-command.json').write_text(json.dumps(cmd,indent=2)+'\n')
   with (out/'slice.log').open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
   (out/'native-result.json').write_text(json.dumps({'exit_code':p.returncode})+'\n');print(row['printer'],row['color'],p.returncode,flush=True)
  return
 existing=[p for p in C.rglob('*') if p.is_file() and D not in p.parents and p.suffix in ['.3mf','.gcode']]
 saved=[{'path':str(p),'sha256':sha(p)} for p in existing];rows=[]
 er=json.loads((C/'spacing-verification.json').read_text());br=json.loads((C/'05-BAMBU-WHITE-YELLOW/spacing-verification.json').read_text())
 for printer,colors in [('Bambu',['WHITE','yellow']),('Elegoo',['orange','yellow','WHITE'])]:
  for color in colors:
   if printer=='Bambu':
    src=C/'05-BAMBU-WHITE-YELLOW'/color/f'MicroDuck_Bambu_{color}_editable.3mf';objects=br['plates'][color]['objects'];bounds=[min(o['extrusion_bounds_mm'][i] for o in objects) if i<2 else max(o['extrusion_bounds_mm'][i] for o in objects) for i in range(4)]
   else:src=C/color/f'MicroDuck-{color}-editable.3mf';bounds=next(x for x in er['plates'] if x['color']==color)['actual_extrusion_bounds_conservative_mm']
   delta=[128-(bounds[0]+bounds[2])/2,128-(bounds[1]+bounds[3])/2];out=D/printer/color;out.mkdir(parents=True,exist_ok=True);target=out/f'MicroDuck_{printer}_{color}_CENTERED_editable.3mf'
   with zipfile.ZipFile(src) as z:files={n:z.read(n) for n in z.namelist()}
   model=E.fromstring(files['3D/3dmodel.model']);transforms=[]
   for it in model.find(N+'build'):
    a=list(map(float,it.get('transform').split()));old=a[:];a[9]+=delta[0];a[10]+=delta[1];it.set('transform',' '.join(f'{v:.14g}' for v in a));transforms.append({'objectid':it.get('objectid'),'before':old,'after':a})
   with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
    for n,data in files.items():z.writestr(n,E.tostring(model,encoding='utf-8',xml_declaration=True) if n=='3D/3dmodel.model' else data)
   rows.append({'printer':printer,'color':color,'source':str(src),'source_sha256':sha(src),'project':str(target),'project_sha256':sha(target),'original_actual_extrusion_bounds_mm':bounds,'group_xy_translation_mm':delta,'predicted_center_mm':[128,128],'predicted_bounds_mm':[bounds[0]+delta[0],bounds[1]+delta[1],bounds[2]+delta[0],bounds[3]+delta[1]],'transforms':transforms,'native_archive_name':f'MicroDuck_{printer}_{color}_CENTERED.gcode.3mf'})
   print(target,flush=True)
 (D/'centering-manifest.json').write_text(json.dumps({'problem_ids':['P5','P6'],'scope':'New centered copies only. Existing live black/white jobs and original artifacts untouched.','originals':saved,'projects':rows},indent=2)+'\n')
if __name__=='__main__':run()
