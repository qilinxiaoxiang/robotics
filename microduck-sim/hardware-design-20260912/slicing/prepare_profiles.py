from pathlib import Path
import json
R=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL');P=Path(__file__).resolve().parent

def resolve(kind,name,stack=()):
 assert name not in stack
 x=json.loads((R/kind/(name+'.json')).read_text());out={}
 if x.get('inherits'):out.update(resolve(kind,x['inherits'],stack+(name,)))
 for inc in x.get('include',[]):out.update(resolve(kind,inc,stack+(name,)))
 out.update(x);out.pop('include',None);out.pop('inherits',None);return out
for k,name in [('machine','Bambu Lab X1 Carbon 0.4 nozzle'),('process','0.20mm Standard @BBL X1C'),('filament','Bambu PLA Basic @BBL X1C')]:
 x=resolve(k,name)
 if k=='machine':x['curr_bed_type']='Cool Plate'
 if k=='process':x.update({'wall_loops':'4','sparse_infill_density':'30%','sparse_infill_pattern':'gyroid','top_shell_layers':'5','bottom_shell_layers':'5','enable_support':'0','brim_type':'no_brim'})
 if k=='filament': assert float(x['filament_density'][0])>1
 x['from']='user'; x['instantiation']='true';x['inherits']=name;x['name']='MicroDuck '+name
 (P/(k+'.json')).write_text(json.dumps(x,indent=2))
 print(k,len(x),str(x.get('filament_density','')),len(str(x.get('machine_start_gcode',''))))
