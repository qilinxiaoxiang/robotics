"""Bounded Orca 2.4.2 CLI export using its required filament-ID population path."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile,re,datetime
D=Path(__file__).resolve().parent;B=D.parents[2]
MATCH=['filament_id','filament_type','filament_vendor','filament_density','filament_diameter','filament_flow_ratio','nozzle_temperature','nozzle_temperature_initial_layer','textured_plate_temp','textured_plate_temp_initial_layer','filament_max_volumetric_speed','fan_min_speed','fan_max_speed']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--project',required=True);ap.add_argument('--outputdir',required=True);ap.add_argument('--export',default='guarded-sliced.3mf');ap.add_argument('--debug',type=int,default=0);ap.add_argument('--filament',default=str(B/'printing-elegoo-20260929/filament.json'));args=ap.parse_args();project=Path(args.project).resolve();fil=Path(args.filament).resolve();out=Path(args.outputdir).resolve();out.mkdir(parents=True,exist_ok=True);profile=json.loads(fil.read_text())
 with zipfile.ZipFile(project) as z:cfg=json.loads(z.read('Metadata/project_settings.config'))
 checks={k:cfg.get(k)==profile.get(k) for k in MATCH};assert all(checks.values()),checks;assert profile.get('filament_id'),'nonempty native filament ID required';assert cfg['filament_settings_id']==[profile['name']],(cfg['filament_settings_id'],profile['name']);assert cfg['filament_type']==['PLA'];assert cfg['nozzle_diameter']==['0.4'];assert 'Centauri Carbon' in cfg['printer_settings_id']
 logdir=Path.home()/'Library/Logs/DiagnosticReports';before={str(p) for p in logdir.glob('OrcaSlicer*.ips')};cmd=['/Volumes/OrcaSlicer/OrcaSlicer.app/Contents/MacOS/OrcaSlicer','--allow-newer-file','--arrange','0','--orient','0','--slice','0','--load-filaments',str(fil),'--export-3mf',args.export,'--outputdir',str(out),str(project)];cmd[1:1]=['--debug',str(args.debug)];(out/'command.json').write_text(json.dumps({'argv':cmd,'filament_profile_checks':checks,'project_sha256':sha(project),'filament_profile_sha256':sha(fil)},indent=2)+'\n')
 with (out/'cli.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 after={str(p) for p in logdir.glob('OrcaSlicer*.ips')};report={'exit_code':r.returncode,'new_crash_reports':sorted(after-before),'project_sha256':sha(project),'filament_profile_sha256':sha(fil),'archive_exists':(out/args.export).exists()};assert r.returncode==0,report;assert not report['new_crash_reports'],report;assert report['archive_exists'],report
 with zipfile.ZipFile(out/args.export) as z:
  members=[n for n in z.namelist() if n.endswith('.gcode')];assert len(members)==1;code=z.read(members[0]).decode();ids=re.findall(r'^; filament_ids = (.+)$',code,re.M);assert ids and profile['filament_id'] in ids[0],ids;report.update(gcode_members=members,filament_ids_header=ids,archive_sha256=sha(out/args.export),gcode_sha256=hashlib.sha256(z.read(members[0])).hexdigest())
 report['passed']=True;(out/'slice-acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
