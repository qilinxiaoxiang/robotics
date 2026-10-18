from pathlib import Path
import json,zipfile,hashlib,xml.etree.ElementTree as E,sys
D=Path(__file__).resolve().parent;V=D.parent;P=V.parent;R=P.parent;S=V/'delivery-V1.3-Incremental'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cfg(p):
 with zipfile.ZipFile(p) as z:return json.loads(z.read('Metadata/project_settings.config'))
# Enumerate native machine/filament domains; take actual values from already-accepted donor projects.
BBL=Path('/Applications/BambuStudio.app/Contents/Resources/profiles/BBL');srcs={}
def resolve(p,domain):
 x=json.loads(p.read_text());srcs[str(p)]=sha(p);o={}
 if x.get('inherits'):o.update(resolve(BBL/domain/(x['inherits']+'.json'),domain))
 for n in x.get('include',[]):o.update(resolve(BBL/domain/(n+'.json'),domain))
 o.update(x);return o
bmachine=resolve(BBL/'machine/Bambu Lab X1 Carbon 0.4 nozzle.json','machine')
bfil=resolve(BBL/'filament/Bambu PLA Basic @BBL X1C.json','filament')
ebase=R/'printing-elegoo-20260929';em=json.loads((ebase/'machine.json').read_text());ef=json.loads((ebase/'filament.json').read_text())
keys=set(bmachine)|set(bfil)|set(em)|set(ef)|{'printer_settings_id','filament_settings_id','filament_ids','filament_id','curr_bed_type','compatible_printers','compatible_printers_condition','printer_model','print_host','nozzle_diameter','extruder_offset'}
keys-= {'name','type','from','inherits','include','instantiation','version','setting_id','filament_colour'}
onlyBlack='--black-only' in sys.argv
rows=[r for r in json.loads((D/'preparation.json').read_text())['rows'] if r['color']!='Black'] if onlyBlack else []
for color,machine in [('White','Elegoo'),('Yellow','Elegoo'),('Black','Bambu'),('Orange','Bambu'),('Black','Elegoo')]:
 if onlyBlack and color!='Black':continue
 source=(D/'Black_V1.4_base.3mf') if color=='Black' and (D/'Black_V1.4_base.3mf').exists() else S/color/f'{color}_V1.3_editable.3mf';donor=S/('White'if machine=='Bambu'else'Orange')/(('White'if machine=='Bambu'else'Orange')+'_V1.3_editable.3mf');old=cfg(source);target=cfg(donor);new=dict(old)
 for k in keys:
  if k in target:new[k]=target[k]
  else:new.pop(k,None)
 # GUI-native support algorithm vocabulary follows target printer/slicer; mesh support blockers stay exact.
 new['support_style']=target['support_style'];
 for k in ['raft_first_layer_expansion','tree_support_wall_count']:
  if k in target:new[k]=target[k]
  else:new.pop(k,None)
 new['filename_format']=f'zhengxia_{color}_{machine}.gcode'
 path=D/f'{color}_{machine}_editable.3mf'
 with zipfile.ZipFile(source) as zin,zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as zout:
  for info in zin.infolist():
   b=zin.read(info.filename)
   if info.filename=='3D/3dmodel.model' and machine=='Bambu':b=b.replace(b'OrcaSlicer-2.4.2',b'BambuStudio-02.08.02.61')
   if info.filename=='Metadata/project_settings.config':b=json.dumps(new,indent=2).encode()
   elif info.filename=='Metadata/model_settings.config':
    root=E.fromstring(b)
    for elem in root.findall("plate/metadata[@key='bed_type']"):elem.set('value',new['curr_bed_type'])
    b=E.tostring(root,encoding='utf-8',xml_declaration=True)
   zout.writestr(info,b)
 with zipfile.ZipFile(source)as z1,zipfile.ZipFile(path)as z2:
  geom=[n for n in z1.namelist() if n.startswith('3D/')];assert geom and all((z1.read(n).replace(b'OrcaSlicer-2.4.2',b'BambuStudio-02.08.02.61') if machine=='Bambu' else z1.read(n))==z2.read(n) for n in geom)
  a=E.fromstring(z1.read('Metadata/model_settings.config'));b=E.fromstring(z2.read('Metadata/model_settings.config'))
  for x in [a,b]:
   for el in x.findall("plate/metadata[@key='bed_type']"):el.set('value','TARGET_BED')
  assert E.tostring(a)==E.tostring(b)
 diff={k:{'before':old.get(k),'after':new.get(k)}for k in set(old)|set(new)if old.get(k)!=new.get(k)}
 rows.append({'color':color,'machine':machine,'project':str(path),'source':str(source),'sourceSha256':sha(source),'projectSha256':sha(path),'donor':str(donor),'donorSha256':sha(donor),'geometryAndTransformsRetained':True,'applicationMetadataTargetNormalized':machine=='Bambu','exactModelSettingsExceptBedRetained':True,'configDiff':diff})
(D/'preparation.json').write_text(json.dumps({'rows':rows,'nativeProfileSourceHashes':srcs},indent=2)+'\n');print([(r['color'],r['machine'],len(r['configDiff']))for r in rows])
