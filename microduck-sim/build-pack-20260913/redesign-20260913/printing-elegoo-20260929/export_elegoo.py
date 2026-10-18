from pathlib import Path
import json,zipfile,hashlib,subprocess
P=Path(__file__).resolve().parent
R=P.parent
profiles=Path.home()/'Library/Application Support/OrcaSlicer/system/Elegoo'
exe='/Volumes/OrcaSlicer/OrcaSlicer.app/Contents/MacOS/OrcaSlicer'
index={json.loads(p.read_text()).get('name'):p for p in profiles.rglob('*.json')}
used={}
def resolve(name):
 p=index[name];d=json.loads(p.read_text());used[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
 result=resolve(d['inherits']) if d.get('inherits') else {}
 result.update(d);result.pop('inherits',None)
 return result
machine=resolve('Elegoo Centauri Carbon 0.4 nozzle')
process=resolve('0.20mm Standard @Elegoo CC 0.4 nozzle')
process.update(name='MicroDuck 0.20mm 4 walls 30% gyroid @Elegoo CC',wall_loops='4',sparse_infill_density='30%',sparse_infill_pattern='gyroid',enable_support='1',support_type='tree(auto)',support_style='tree_hybrid',enable_prime_tower='0',brim_type='auto_brim',print_sequence='by layer')
filament=resolve('Elegoo PLA @ECC')
# Conservative ordinary PLA recipe; retain manufacturer cooling/start routines.
filament.update(name='MicroDuck Generic PLA @Elegoo CC',filament_vendor=['Generic'],filament_max_volumetric_speed=['12'],nozzle_temperature=['220'],nozzle_temperature_initial_layer=['220'],enable_pressure_advance=['0'],filament_settings_id=['MicroDuck Generic PLA @Elegoo CC'])
for key in ['textured_plate_temp','textured_plate_temp_initial_layer']:filament[key]=['55']
settings={**machine,**process,**filament,'printer_settings_id':machine['name'],'print_settings_id':process['name'],'filament_settings_id':[filament['name']],'curr_bed_type':'Textured PEI Plate','filament_colour':['#00AE42']}
for name,d in [('machine',machine),('process',process),('filament',filament)]:
 (P/(name+'.json')).write_text(json.dumps(d,indent=2))
(P/'profile-sources.json').write_text(json.dumps(used,indent=2))
bambu=[R/'current-print-queue.3mf',*(R/'printing-20260926/SD-CARD').glob('*'),R/'printing-20260926/MicroDuck-current-89-six-plates-sliced.3mf']
(P/'bambu-preserved-sha256.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in bambu},indent=2))
source=P/'MicroDuck-Centauri-Carbon-Orca.3mf'
with zipfile.ZipFile(R/'current-print-queue.3mf') as zin,zipfile.ZipFile(source,'w',zipfile.ZIP_DEFLATED) as zout:
 for member in zin.infolist():
  data=zin.read(member.filename)
  if member.filename=='Metadata/project_settings.config':data=json.dumps(settings,indent=2).encode()
  elif member.filename=='Metadata/model_settings.config':data=data.replace(b'value="Cool Plate"',b'value="Textured PEI Plate"')
  zout.writestr(member,data)
command=[exe,'--allow-newer-file','--arrange','0','--slice','0','--load-settings',str(P/'machine.json')+';'+str(P/'process.json'),'--load-filaments',str(P/'filament.json'),'--export-3mf','MicroDuck-Centauri-Carbon-sliced.3mf','--outputdir',str(P),str(source)]
(P/'native-command.json').write_text(json.dumps(command,indent=2))
with (P/'slice.log').open('w') as out:
 r=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT)
(P/'native-result.json').write_text(json.dumps({'exit_code':r.returncode,'command':command},indent=2))
print('Orca native exit',r.returncode,flush=True)
assert r.returncode==0,'See slice.log'
with zipfile.ZipFile(P/'MicroDuck-Centauri-Carbon-sliced.3mf') as z:
 files=[n for n in z.namelist() if n.endswith('.gcode')]
 print('Native G-code files',files,flush=True)
 assert len(files)==6
 # CLI does not render embedded thumbnails. These are intermediate files only.
 d=P/'CLI-GCODE-NO-PREVIEWS';d.mkdir(exist_ok=True)
 for n in files:
  num=Path(n).stem.split('_')[-1]
  (d/f'MicroDuck_Elegoo_plate_{num}.gcode').write_bytes(z.read(n))
print('Six intermediate slices created. Open the sliced 3MF in OrcaSlicer, Slice all, then File > Export > Export all plate sliced file. Final printer handoff requires embedded thumbnails validated by PRINTING/verify_organized_printing.py. Existing USB-PRINT files were not overwritten.',flush=True)
