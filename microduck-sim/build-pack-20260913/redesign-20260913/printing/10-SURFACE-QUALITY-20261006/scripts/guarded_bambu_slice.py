"""Use known Bambu2.8.2 CLI only after source filament-ID/extruder/material guards."""
from pathlib import Path
import argparse,json,zipfile,xml.etree.ElementTree as E,subprocess,hashlib,re
D=Path(__file__).resolve().parents[1]
MATERIAL=['filament_ids','filament_type','filament_vendor','filament_density','filament_diameter','filament_flow_ratio','nozzle_temperature','nozzle_temperature_initial_layer','cool_plate_temp','cool_plate_temp_initial_layer','filament_max_volumetric_speed','fan_min_speed','fan_max_speed','filament_settings_id','printer_settings_id','nozzle_diameter','curr_bed_type','extruder_offset']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project',required=True);ap.add_argument('--outputdir',required=True);ap.add_argument('--export',default='guarded-bambu-sliced.3mf');ap.add_argument('--support-flag-control-reference');args=ap.parse_args();p=Path(args.project).resolve();reference=Path(args.support_flag_control_reference).resolve() if args.support_flag_control_reference else p;rows=json.loads((D/'projects/project-preparation.json').read_text())['variants'];row=next(r for r in rows if Path(r['project']).resolve()==reference);assert row['printer']=='Bambu';source=Path(row['source_project'])
 with zipfile.ZipFile(p) as z:cfg=json.loads(z.read('Metadata/project_settings.config'));st=E.fromstring(z.read('Metadata/model_settings.config'))
 control_diff={}
 if reference!=p:
  assert row['group']=='yellow', 'Bounded control applies only to Bambu yellow'
  with zipfile.ZipFile(reference) as rz,zipfile.ZipFile(p) as cz:
   assert rz.namelist()==cz.namelist(), 'Control must retain exactly the same project members'
   for name in rz.namelist():
    if name!='Metadata/project_settings.config':assert rz.read(name)==cz.read(name),name
   rcfg=json.loads(rz.read('Metadata/project_settings.config'))
  control_diff={k:{'before':rcfg.get(k),'after':cfg.get(k)} for k in set(rcfg)|set(cfg) if rcfg.get(k)!=cfg.get(k)}
  assert set(control_diff)=={'support_remove_small_overhang','support_interface_not_for_body'},control_diff
  assert all(v=={'before':'1','after':'0'} for v in control_diff.values()),control_diff
 with zipfile.ZipFile(source) as z:scfg=json.loads(z.read('Metadata/project_settings.config'))
 checks={k:cfg.get(k)==scfg.get(k) for k in MATERIAL};assert all(checks.values()),checks;ids=cfg.get('filament_ids');assert isinstance(ids,list) and ids and all(isinstance(i,str) and i.strip() for i in ids);assert ids==['GFA00'];extruders=[int(m.get('value')) for m in st.findall("object/metadata[@key='extruder']")];assert extruders and min(extruders)>=1 and max(extruders)<=len(ids);assert cfg['filament_type']==['PLA'];assert cfg['nozzle_diameter']==['0.4'];assert 'X1 Carbon' in cfg['printer_settings_id'];assert cfg['curr_bed_type']=='Cool Plate';plate_beds=[p.find("metadata[@key='bed_type']").get('value') if p.find("metadata[@key='bed_type']") is not None else None for p in st.findall('plate')];assert plate_beds and all(v=='Cool Plate' for v in plate_beds),plate_beds;assert len(st.findall('object'))==row['expected_count'];out=Path(args.outputdir).resolve();out.mkdir(parents=True,exist_ok=True);cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--allow-newer-file','--arrange','0','--orient','0','--slice','0','--export-3mf',args.export,'--outputdir',str(out),str(p)];before={str(p) for p in (Path.home()/'Library/Logs/DiagnosticReports').glob('BambuStudio*.ips')};(out/'command.json').write_text(json.dumps({'argv':cmd,'control_reference':str(reference),'control_reference_sha256':sha(reference),'bounded_process_diff':control_diff,'source_material_checks':checks,'source_filament_ids':ids,'active_extruders':sorted(set(extruders)),'explicit_plate_bed_type':plate_beds,'project_sha256':sha(p),'source_project_sha256':sha(source)},indent=2)+'\n')
 with (out/'cli.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 after={str(p) for p in (Path.home()/'Library/Logs/DiagnosticReports').glob('BambuStudio*.ips')};report={'exit_code':r.returncode,'new_crash_reports':sorted(after-before),'project_sha256':sha(p),'source_project_sha256':sha(source),'archive_exists':(out/args.export).exists()};assert r.returncode==0,report;assert not report['new_crash_reports'],report;assert report['archive_exists'],report
 with zipfile.ZipFile(out/args.export) as z:
  members=[n for n in z.namelist() if n.endswith('.gcode')];assert len(members)==1;payload=z.read(members[0]);header=re.findall(r'^;\s*filament_ids\s*=\s*(.+)$',payload.decode(),re.M);assert header and 'GFA00' in header[0],header;report.update(gcode_members=members,filament_ids_header=header,archive_sha256=sha(out/args.export),gcode_sha256=hashlib.sha256(payload).hexdigest())
 report['passed']=True;(out/'slice-acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
