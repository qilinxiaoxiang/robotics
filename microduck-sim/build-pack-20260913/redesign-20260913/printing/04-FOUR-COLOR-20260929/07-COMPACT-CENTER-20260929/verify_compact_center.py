"""Verify only new compact centered copies and all immutable original print artifacts."""
from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as E,runpy,sys,io,base64,re
from PIL import Image
D=Path(__file__).resolve().parent;C=D.parent;N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 m=json.loads((D/'centering-manifest.json').read_text());results=[]
 for old in m['originals']:assert sha(Path(old['path']))==old['sha256'],('Original changed',old['path'])
 bambu=runpy.run_path(str(C/'05-BAMBU-WHITE-YELLOW/audit_bambu_spacing.py'))['audit_archive']
 elegoo=runpy.run_path(str(C/'audit_spacing.py'))['parse']
 for row in m['projects']:
  src=Path(row['source']);target=Path(row['project']);assert sha(src)==row['source_sha256'];assert sha(target)==row['project_sha256']
  za=zipfile.ZipFile(src);zb=zipfile.ZipFile(target);assert set(za.namelist())==set(zb.namelist())
  for n in za.namelist():
   if n!='3D/3dmodel.model':assert za.read(n)==zb.read(n),('Non-placement content changed',n)
  a=E.fromstring(za.read('3D/3dmodel.model'));b=E.fromstring(zb.read('3D/3dmodel.model'));ia=list(a.find(N+'build'));ib=list(b.find(N+'build'));assert len(ia)==len(ib)
  for before,after in zip(ia,ib):
   aa=list(map(float,before.get('transform').split()));bb=list(map(float,after.get('transform').split()));dx,dy=next(t['xy_translation_mm'] for t in row['transforms'] if t['objectid']==before.get('objectid'))
   expected=aa[:];expected[9]+=dx;expected[10]+=dy;assert max(abs(x-y) for x,y in zip(expected,bb))<1e-8
   after.set('transform',before.get('transform'))
  assert E.tostring(a)==E.tostring(b),'Geometry, identities or build attributes changed'
  archive=target.parent/row['native_archive_name'];assert archive.is_file(),str(archive)
  z=zipfile.ZipFile(archive);gn=[n for n in z.namelist() if n.endswith('.gcode')];assert len(gn)==1
  cfg=json.loads(z.read('Metadata/project_settings.config'));assert cfg['print_sequence']=='by layer'
  assert cfg['printer_settings_id']==json.loads(za.read('Metadata/project_settings.config'))['printer_settings_id']
  oldarchive=(C/'05-BAMBU-WHITE-YELLOW'/row['color']/f"MicroDuck_Bambu_{row['color']}.gcode.3mf") if row['printer']=='Bambu' else (C/row['color']/f"MicroDuck-{row['color']}-GUI.gcode.3mf")
  oldcfg=json.loads(zipfile.ZipFile(oldarchive).read('Metadata/project_settings.config'))
  differences={k:[oldcfg.get(k),cfg.get(k)] for k in set(oldcfg)|set(cfg) if oldcfg.get(k)!=cfg.get(k)}
  allowed={'filament_settings_id','print_settings_id','flush_volumes_vector','print_compatible_printers'}
  assert set(differences)<=allowed,('Print/process/machine setting changed',differences)
  for k in ['filament_settings_id','print_settings_id']:
   if k in differences:
    normalize=lambda v:[re.sub(r'\([^()]*\.3mf\)','',x) for x in (v if isinstance(v,list) else [v])]
    assert normalize(differences[k][0])==normalize(differences[k][1])
  if 'flush_volumes_vector' in differences:assert set(differences['flush_volumes_vector'][0])==set(differences['flush_volumes_vector'][1])
  if row['printer']=='Bambu':
   result=bambu(archive,len(ia));assert result['passed'];parts=result['objects'];bounds=[min(p['extrusion_bounds_mm'][i] for p in parts) if i<2 else max(p['extrusion_bounds_mm'][i] for p in parts) for i in range(4)]
   thumbnails=[n for n in z.namelist() if n.endswith('.png') and '/plate_' in n];assert thumbnails and all(z.read(n).startswith(b'\x89PNG') for n in thumbnails)
  else:
   extracted=target.parent/'audit-extracted.gcode';extracted.write_bytes(z.read(gn[0]));result,*_=elegoo(extracted);assert result['passed_nonoverlap_and_inside_bed'];assert result['object_count']==len(ia);bounds=result['actual_extrusion_bounds_conservative_mm'];thumbnails=[n for n in z.namelist() if n.endswith('.png') and '/plate_' in n];assert thumbnails and all(z.read(n).startswith(b'\x89PNG') for n in thumbnails)
  decoded=[]
  for n in thumbnails:
   image=Image.open(io.BytesIO(z.read(n)));image.load();assert min(image.size)>=32;assert any(hi>lo for lo,hi in image.convert('RGB').getextrema());decoded.append({'member':n,'size':list(image.size),'format':image.format})
  embedded=[]
  if row['printer']=='Elegoo':
   text=z.read(gn[0]).decode()
   for match in re.finditer(r'; thumbnail begin (\d+)x(\d+) \d+\n(.*?); thumbnail end',text,re.S):
    encoded=''.join(line.lstrip('; ').strip() for line in match[3].splitlines());im=Image.open(io.BytesIO(base64.b64decode(encoded)));im.load();assert im.size==(int(match[1]),int(match[2]));assert any(hi>lo for lo,hi in im.convert('RGB').getextrema());embedded.append(list(im.size))
   assert embedded,'Missing decodable embedded Elegoo Gcode thumbnail'
  center=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2];error=max(abs(v-128) for v in center);assert error<=2.0,('Native regenerated support footprint morethan2mmfrombedcenter',row['printer'],row['color'],center)
  gap=result.get('minimum_interobject_gap_lower_bound_mm',result.get('minimum_interobject_extrusion_gap_lower_bound_mm'));assert gap>=4,('Actual gap below4mm',row['printer'],row['color'],gap)
  baseline=row['baseline_width_height_mm'];newspan=[bounds[2]-bounds[0],bounds[3]-bounds[1]];assert max(newspan)<max(baseline)-1,('No meaningful max-span improvement',row['color'])
  oldreport=json.loads((C/'06-CENTERED-20260929/centering-verification.json').read_text());oldbounds=next(p['actual_footprint_bounds_mm'] for p in oldreport['projects'] if p['printer']==row['printer'] and p['color']==row['color'])
  margins=lambda b:{'left':b[0],'right':256-b[2],'front':b[1],'rear':256-b[3]}
  threshold=35 if row['color']=='yellow' else 55
  assert min(margins(bounds).values())>=threshold,('Insufficientallsideclearance',row['printer'],row['color'])
  assert min(margins(bounds).values())-min(margins(oldbounds).values())>=10,('Minimumedgeimprovementbelow10mm',row['color'])
  code=z.read(gn[0]).decode();times=[line for line in code.splitlines() if 'total estimated time:' in line or 'estimated printing time (normal mode)' in line]
  results.append({'side_margins_mm':margins(bounds),'baseline_side_margins_mm':margins(oldbounds),'width_height_mm':newspan,'native_time_estimate':times,'printer':row['printer'],'color':row['color'],'object_count':len(ia),'translation_only_preserved':True,'baseline_width_height_mm':row['baseline_width_height_mm'],'optimization_trials':row['optimization_trials'],'settings_preserved':True,'actual_footprint_bounds_mm':bounds,'actual_footprint_center_mm':center,'center_error_max_mm':error,'archive':str(archive),'archive_sha256':sha(archive),'gcode_sha256':hashlib.sha256(z.read(gn[0])).hexdigest(),'native_thumbnails':decoded,'embedded_gcode_thumbnails':embedded,'process_settings_equal_except_filename_metadata':True,'harmless_setting_differences':differences,'spacing_audit':result})
 copies=[]
 for row in results:
  archive=Path(row['archive']);primary=row['printer']=='Bambu' or row['color']=='orange';folder=D/('READY-TO-PRINT' if primary else 'ALTERNATE-ELEGOO');folder.mkdir(exist_ok=True)
  if row['printer']=='Bambu':name=archive.name;data=archive.read_bytes()
  else:
   name=f"MicroDuck_Elegoo_{row['color']}_COMPACT.gcode";z=zipfile.ZipFile(archive);data=z.read(next(n for n in z.namelist() if n.endswith('.gcode')))
  target=folder/name
  if target.exists():assert target.read_bytes()==data,('Existing handoff copy changed',str(target))
  else:target.write_bytes(data)
  assert target.read_bytes()==data
  copies.append({'path':str(target),'sha256':sha(target),'source_archive':str(archive),'byte_identical':True,'primary':primary})
 startup=D/'start-lines-evidence.txt';assert startup.is_file()
 native=next(r for r in results if r['printer']=='Bambu' and r['color']=='WHITE');zz=zipfile.ZipFile(native['archive']);code=zz.read(next(n for n in zz.namelist() if n.endswith('.gcode'))).decode()
 for token in [';===== nozzle load line','G1 X18.0 Y1.0','G0 X240 E15','M1002 judge_flag extrude_cali_flag','M622 J1']:
  assert token in code and token in startup.read_text(),('Startup explanation source mismatch',token)
 out={'startup_explanation_evidence':str(startup),'startup_explanation_evidence_sha256':sha(startup),'passed':True,'status':'COMPACT_CENTER_ACCEPTANCE_PASS','original_files_unchanged':len(m['originals']),'live_jobs_modified':False,'center_target_mm':[128,128],'regenerated_support_center_tolerance_mm':2,'clearance_threshold_mm':{'yellow':35,'WHITE':55,'orange':55},'minimum_edge_improvement_required_mm':10,'minimum_interobject_gap_required_mm':4,'support_regeneration_observations':json.loads((D/'support-regeneration-observations.json').read_text()),'scope':'Five new compact centered copies only; two Bambu and three Elegoo. Existing files and live black/white jobs untouched.','projects':results,'handoff_copies':copies};(D/'compact-verification.json').write_text(json.dumps(out,indent=2)+'\n');print('COMPACT_CENTER_ACCEPTANCE_PASS '+json.dumps({k:v for k,v in out.items() if k!='projects'}));print(json.dumps([{k:v for k,v in r.items() if k!='spacing_audit'} for r in results],indent=2));return out
if __name__=='__main__':verify()
