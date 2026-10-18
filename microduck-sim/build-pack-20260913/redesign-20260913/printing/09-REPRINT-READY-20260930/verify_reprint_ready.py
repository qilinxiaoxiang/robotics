"""Verify packaged native reprint jobs. Reads artifacts; writes acceptance evidence only."""
from pathlib import Path
import sys,json,zipfile,xml.etree.ElementTree as E,hashlib,re,io,base64,traceback
from collections import Counter
import numpy as np
from PIL import Image
from shapely.ops import unary_union
D=Path(__file__).resolve().parent;P=D.parent
sys.path.insert(0,str(P/'08-ORANGE-BOTTOM-AUDIT-20260930'));import analyze_bottom as a
from native_tools import normalize_bambu,parse
sys.path.insert(0,str(P/'04-FOUR-COLOR-20260929/05-BAMBU-WHITE-YELLOW'));from audit_bambu_spacing import audit_archive
N=a.N
class TextPath:
 def __init__(self,text):self.text=text
 def open(self):return io.StringIO(self.text)
 def read_bytes(self):return self.text.encode()
def png(data):
 im=Image.open(io.BytesIO(data));im.load();arr=np.asarray(im.convert('RGB'));return {'size':list(im.size),'nonblank':bool(np.ptp(arr.reshape(-1,3),axis=0).max()>0),'format':im.format}
def model(path):
 with zipfile.ZipFile(path) as z:
  root=E.fromstring(z.read('3D/3dmodel.model'));cfg=json.loads(z.read('Metadata/project_settings.config'));st=E.fromstring(z.read('Metadata/model_settings.config'));members={n:z.read(n) for n in z.namelist() if n.startswith('3D/') and n!='3D/3dmodel.model'}
 return root,cfg,st,members
def unique_first(code,printer,project):
 if printer=='Bambu':code=normalize_bambu(code,project)
 labels=re.findall(r'^EXCLUDE_OBJECT_DEFINE NAME=(\S+)',code,re.M)
 # Original helper splits at _id_; replace whole labels with unique plain tokens first.
 lookup={label:f'instance-{i}' for i,label in enumerate(labels)}
 for label,key in sorted(lookup.items(),key=lambda p:-len(p[0])):code=code.replace('NAME='+label,'NAME='+key)
 paths=a.first_layer_paths(code);out=[]
 for label,key in lookup.items():
  kinds=paths.get(key,{});m=unary_union([s for k,s in kinds.items() if not any(t in k.lower() for t in ['support','brim','skirt'])]);s=unary_union([s for k,s in kinds.items() if 'support' in k.lower()]);out.append({'native_label':label,'model_area_mm2':m.area,'support_area_mm2':s.area,'contact_present':m.area+s.area>0})
 return out

def main():
 package=json.loads((D/'packaging.json').read_text());variants=package.get('variants',package.get('files',[]));prep=json.loads((D/'project-preparation.json').read_text())['projects'];audit=json.loads((D/'orientation-audit.json').read_text());rows=audit['parts'];results=[]
 for v in variants:
  result={'printer':v['printer'],'group':v['group'],'checks':{},'errors':[]};results.append(result);check=result['checks']
  try:
   printer=v['printer'];group=v['group'];project=Path(v['project']);archive=Path(v['archive']);count=v.get('expected_count',v.get('expectedcount'));pr=next(q for q in prep if q['machine']==printer and q['group']==group);source=Path(pr['source']);result.update(project=str(project),project_sha256=a.sha(project),archive=str(archive),archive_sha256=a.sha(archive))
   check['original_source_hash_unchanged']=a.sha(source)==pr['source_sha256']
   if v.get('native_reused'):check['reused_native_archive_exact']=archive.read_bytes()==Path(v['native_source']).read_bytes()
   rt,cfg,st,members=model(project);srt,scfg,sst,smembers=model(source);check['mesh_members_exact']=all(n in smembers and data==smembers[n] for n,data in members.items())
   expected={r['object_id']:r for r in rows if r['group']==group};items={i.get('objectid'):i for i in rt.find(N+'build')};srcitems={i.get('objectid'):i for i in srt.find(N+'build')};check['exact_object_coverage']=set(items)==set(expected) and len(items)==count
   objects={i.get('id'):i for i in rt.find(N+'resources')};srcobjects={i.get('id'):i for i in srt.find(N+'resources')}
   check['components_unchanged']=all(E.tostring(objects[oid].find(N+'components'))==E.tostring(srcobjects[oid].find(N+'components')) for oid in items)
   transform=[]
   yaw_by_id={}
   if group=='black' and printer=='Elegoo':
    packing=json.loads((D/'black-packing-candidate.json').read_text());assert packing['feasible'];yaw_by_id={q['oid']:q['angle'] for q in packing['placements']}
   for oid,item in items.items():
    current=a.matrix(item.get('transform'));old=a.matrix(srcitems[oid].get('transform'));delta=current@np.linalg.inv(old);want=np.array(expected[oid]['applied_delta4x4'])[:3,:3]
    angle=np.deg2rad(yaw_by_id.get(oid,0));yaw=np.array([[np.cos(angle),-np.sin(angle),0],[np.sin(angle),np.cos(angle),0],[0,0,1]]);want=yaw@want
    transform.append({'object_id':oid,'documented_z_yaw_degrees':yaw_by_id.get(oid,0),'rotation_matches_intended':bool(np.allclose(delta[:3,:3],want,atol=2e-6)),'rigid':bool(np.allclose(delta[:3,:3].T@delta[:3,:3],np.eye(3),atol=2e-6) and abs(np.linalg.det(delta[:3,:3])-1)<2e-6)})
   result['transforms']=transform;check['only_intended_rigid_rotations']=all(t['rotation_matches_intended'] and t['rigid'] for t in transform)
   a.PROJECT=project;meshes=a.load_meshes();check['all_landed_on_bed']=all(abs(m.bounds[0,2])<.015 for _,_,m in meshes)
   result['minimum_z_mm']={oid:float(m.bounds[0,2]) for oid,_,m in meshes}
   with zipfile.ZipFile(archive) as z:
    gn=[n for n in z.namelist() if n.endswith('.gcode')];assert len(gn)==1,gn;data=z.read(gn[0]);code=data.decode();nativecfg=json.loads(z.read('Metadata/project_settings.config'));th=[png(z.read(n)) for n in z.namelist() if re.search(r'plate_\d+\.png$',n)];result['native_thumbnails']=th;check['native_nonblank_png']=bool(th) and all(t['format']=='PNG' and t['nonblank'] for t in th)
   check['build_plate_matches_project']=nativecfg.get('curr_bed_type')==cfg.get('curr_bed_type');result['gcode_sha256']=hashlib.sha256(data).hexdigest();check['machine_profile_matches_project']=nativecfg.get('printer_settings_id')==cfg.get('printer_settings_id') and nativecfg.get('nozzle_diameter')==cfg.get('nozzle_diameter');check['source_machine_profile_retained']=cfg.get('printer_settings_id')==scfg.get('printer_settings_id') and cfg.get('nozzle_diameter')==scfg.get('nozzle_diameter');check['pla_profile']=all('PLA' in x.upper() for x in nativecfg.get('filament_type',[])) and bool(nativecfg.get('filament_type'));check['by_layer']=nativecfg.get('print_sequence')=='by layer'
   if printer=='Elegoo':
    gcode=Path(v['gcode']);check['gcode_exact_native_bytes']=gcode.read_bytes()==data;thumb=[]
    for m in re.finditer(r'; thumbnail begin (\d+)x(\d+) \d+\s*\n(.*?); thumbnail end',code,re.S):
     raw=''.join(re.sub(r'^;\s*','',line).strip() for line in m.group(3).splitlines());t=png(base64.b64decode(raw,validate=True));thumb.append(t)
    result['embedded_thumbnails']=thumb;check['embedded_144_png']=any(t['size']==[144,144] and t['nonblank'] and t['format']=='PNG' for t in thumb);spacing=parse(TextPath(code))[0];gap=spacing['minimum_interobject_extrusion_gap_lower_bound_mm'];check['spacing_native_valid']=spacing['passed_nonoverlap_and_inside_bed'];check['native_object_count']=spacing['object_count']==count and spacing['extruding_objects']==count
   else:
    spacing=audit_archive(archive,count);gap=spacing['minimum_interobject_gap_lower_bound_mm'];check['spacing_native_valid']=spacing['passed'];check['native_object_count']=spacing['object_count']==count and spacing['extruding_object_count']==count
   result['spacing']=spacing;check['at_least_4mm_spacing']=gap>=4-.001
   first=unique_first(code,printer,project);result['first_layer_instances']=first;check['native_exact_part_names']=Counter(f['native_label'].split('_id_')[0] for f in first)==Counter(r['name'] for r in expected.values());check['unique_first_layer_coverage']=len(first)==count and len({f['native_label'] for f in first})==count and all(f['contact_present'] for f in first)
   check['corrected64_66_broad_contact']=all(f['model_area_mm2']>200 for f in first if any(n in f['native_label'] for n in ['community-64.stl','community-66.stl']))
   result['object_ids']=sorted(items,key=int);result['manifest_instance_indices']=[expected[o]['manifest_instance_index'] for o in items];result['primary']=v.get('primary',printer=='Elegoo')
  except Exception as exc:result['errors'].append(str(exc));result['traceback']=traceback.format_exc()
  result['passed']=bool(check) and all(check.values()) and not result['errors'];print(v['printer'],v['group'],result['passed'],[k for k,x in check.items() if not x],result['errors'],flush=True)
 primary=[i for r in results if r.get('primary') for i in r.get('manifest_instance_indices',[])];coverage=len(primary)==89 and len(set(primary))==89
 handoff={'passed':False,'errors':[]}
 try:
  index=json.loads((D/'handoff-index.json').read_text());primary_variants=[v for v in variants if v.get('primary')];entries=index['primary_files'];assert len(entries)==6 and index['count']==89;assert index['packaging_sha256']==a.sha(D/'packaging.json');assert {(e['printer'],e['group']) for e in entries}=={(v['printer'],v['group']) for v in primary_variants};assert {p.resolve() for p in (D/'READY-TO-PRINT').iterdir() if p.is_file()}=={Path(e['copy']).resolve() for e in entries}
  readme=(D/'README.md').read_text()
  for e in entries:
   v=next(v for v in primary_variants if v['printer']==e['printer'] and v['group']==e['group']);assert e['count']==v['expected_count'];assert e['archive']==v['archive'] and e['project']==v['project'];assert a.sha(Path(e['archive']))==e['archive_sha256'];assert a.sha(Path(e['project']))==e['project_sha256'];payload=Path(e['copy']).read_bytes();assert hashlib.sha256(payload).hexdigest()==e['sha256']
   if e['printer']=='Elegoo':
    with zipfile.ZipFile(e['archive']) as z:assert payload==z.read(e['archive_member'])
   else:assert payload==Path(e['archive']).read_bytes()
   assert str(Path(e['copy']).relative_to(D)) in readme
  for v in variants:
   assert str(Path(v['project']).relative_to(D)) in readme
   native=v['gcode'] if v['printer']=='Elegoo' else v['archive'];assert str(Path(native).relative_to(D)) in readme
  handoff.update(passed=True,index_sha256=a.sha(D/'handoff-index.json'),ready_file_count=len(entries))
 except Exception as exc:handoff['errors'].append(str(exc) or traceback.format_exc())
 report={'handoff':handoff,'passed':len(results)==10 and all(r['passed'] for r in results) and coverage and handoff['passed'],'primary_89_instance_coverage':coverage,'primary_instance_count':len(primary),'variant_count':len(results),'scope':'Digital native print-file readiness only; physical adhesion and assembly unproven.','packaging_sha256':a.sha(D/'packaging.json'),'variants':results}
 (D/'reprint-verification.json').write_text(json.dumps(report,indent=2)+'\n');print('REPRINT_READY_ACCEPTANCE_PASS' if report['passed'] else 'REPRINT_READY_ACCEPTANCE_FAIL');return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
