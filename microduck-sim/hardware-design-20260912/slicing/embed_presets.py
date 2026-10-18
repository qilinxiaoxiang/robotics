"""Package Bambu JSON presets and per-plate bed selection per official bbs_3mf.cpp."""
from pathlib import Path
import zipfile,json,xml.etree.ElementTree as ET,sys
P=Path(__file__).resolve().parent
src=Path(sys.argv[1]);dst=Path(sys.argv[2]);process=P/('head-process.json' if 'head' in src.name else 'process.json')
with zipfile.ZipFile(src) as z:entries={i.filename:z.read(i.filename) for i in z.infolist()}
project=json.loads(entries['Metadata/project_settings.config'])
# The GUI overlays only keys marked as changed from the inherited preset.
# Without this list, CLI slicing can use 4 walls/supports while GUI silently
# reloads the parent's 2 walls/no support. Keep the recipe values on reopen.
recipe=['wall_loops','sparse_infill_density','sparse_infill_pattern','top_shell_layers',
        'bottom_shell_layers','enable_support','support_type','support_on_build_plate_only',
        'support_threshold_angle','support_style','brim_type','brim_width']
project['different_settings_to_system']=[';'.join(k for k in recipe if k in project),'','']
entries['Metadata/project_settings.config']=json.dumps(project,indent=2).encode()
for kind,path,key in [('process',process,'print_settings_id'),('filament',P/'filament.json','filament_settings_id'),('machine',P/'machine.json','printer_settings_id')]:
 d=json.loads(path.read_text());name=project[key][0] if kind=='filament' else project[key];d.update({'from':'project','name':name,'version':'2.7.1.62',key:[name] if kind=='filament' else name})
 entries[f'Metadata/{kind}_settings_1.config']=json.dumps(d,indent=2).encode()
r=ET.fromstring(entries['Metadata/model_settings.config'])
for plate in r.findall('plate'):
 old=plate.find("metadata[@key='bed_type']")
 if old is not None:old.set('value','Cool Plate')
 else:ET.SubElement(plate,'metadata',{'key':'bed_type','value':'Cool Plate'})
entries['Metadata/model_settings.config']=ET.tostring(r,encoding='utf-8',xml_declaration=True)
# Do not alter the generated G-code. Its digest remains unchanged.
with zipfile.ZipFile(dst,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,data in entries.items():z.writestr(name,data)
print(dst)
