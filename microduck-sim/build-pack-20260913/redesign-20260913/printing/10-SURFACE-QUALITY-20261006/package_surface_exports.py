"""Package native exports after GUI generation; never edits native payloads."""
from pathlib import Path
import json,hashlib,zipfile,shutil,re
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
prep=json.loads((D/'projects/project-preparation.json').read_text())
variants=[];ready=[]
for row in prep['variants']:
 p,g=row['printer'],row['group'];dest=D/'native'/p/g;dest.mkdir(parents=True,exist_ok=True)
 archive=dest/f'MicroDuck_{p}_{g}_SURFACE.gcode.3mf'
 reused=p=='Elegoo' and g=='WHITE'
 if reused:
  shutil.copy2(row['source_archive'],archive)
 if not archive.exists():raise FileNotFoundError(f'Native GUI export pending: {archive}')
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  members=[n for n in z.namelist() if n.endswith('.gcode')];assert len(members)==1
  data=z.read(members[0]);code=data.decode()
  cfg=json.loads(z.read('Metadata/project_settings.config'))
  assert 'G1 ' in code
  thumbnails=[n for n in z.namelist() if re.fullmatch(r'Metadata/plate_\d+\.png',n)]
  assert thumbnails
  for n in thumbnails:(dest/'native-thumbnail.png').write_bytes(z.read(n))
 v={k:row[k] for k in ['printer','group','source_project','source_project_sha256','project','expected_count','primary']}
 v.update(project_sha256=sha(row['project']),archive=str(archive),archive_sha256=sha(archive),gcode_member=members[0],gcode_sha256=hashlib.sha256(data).hexdigest(),native_reused=reused,process_changes=row.get('process_changes',{}),intentional_export_metadata_delta=row.get('intentional_export_metadata_delta',{}))
 if reused:v['native_source']=row['source_archive'];v['native_source_sha256']=sha(row['source_archive'])
 time=re.findall(r'^; estimated printing time.*?= (.*)$',code,re.M) or re.findall(r'total estimated time: ([^;\n]+)',code);assert time,'Native time estimate missing';v['estimated_time']=time[0]
 v['physical_color']='orange' if 'orange' in g else 'black' if 'black' in g else 'yellow' if g=='yellow' else 'white'
 v['printer_profile']=cfg.get('printer_settings_id');v['nozzle_diameter']=cfg.get('nozzle_diameter');v['build_plate']=cfg.get('curr_bed_type');v['filament_type']=cfg.get('filament_type')
 native=archive
 if p=='Elegoo':
  native=dest/f'MicroDuck_{p}_{g}_SURFACE.gcode';native.write_bytes(data);v['gcode']=str(native)
 if v['primary']:
  copy=D/'READY-TO-PRINT'/native.name;shutil.copy2(native,copy)
  ready.append(dict(printer=p,group=g,count=v['expected_count'],project=v['project'],project_sha256=v['project_sha256'],archive=v['archive'],archive_sha256=v['archive_sha256'],archive_member=members[0],copy=str(copy),sha256=sha(copy),physical_color=v['physical_color'],estimated_time=v['estimated_time'],printer_profile=v['printer_profile'],nozzle_diameter=v['nozzle_diameter'],build_plate=v['build_plate']))
 variants.append(v)
manifest={'variants':variants,'primary_count':89,'variant_count':10,'source_packaging':prep['source_packaging'],'source_packaging_sha256':prep['source_packaging_sha256'],'project_preparation_sha256':sha(D/'projects/project-preparation.json'),'scope':'Digital native print-file handoff; physical adhesion, support removal and assembly fit unverified.','problem_ids':['P5','P6'],'printer_started':False}
(D/'packaging.json').write_text(json.dumps(manifest,indent=2)+'\n')
(D/'handoff-index.json').write_text(json.dumps(dict(count=89,primary_files=ready,packaging_sha256=sha(D/'packaging.json')),indent=2)+'\n')
print('Packaged',len(variants),'native variants;',len(ready),'primary jobs;',sum(x['count'] for x in ready),'instances')
