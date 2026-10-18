"""Read final digital handoff and source/functional/native acceptance; never starts printer."""
from pathlib import Path
import argparse,sys,json,hashlib,zipfile,re,io,base64,traceback
import numpy as np
from PIL import Image
D=Path(__file__).resolve().parent;P=D.parent
sys.path.insert(0,str(D/'geometry'));import verify_final_geometry as geometry
sys.path.insert(0,str(P/'09-REPRINT-READY-20260930'));from native_tools import normalize_bambu,parse
sys.path.insert(0,str(P/'08-ORANGE-BOTTOM-AUDIT-20260930'));import analyze_bottom as bottom
sys.path.insert(0,str(D/'scripts'));from native_material_spacing import audit_archive
from shapely.ops import unary_union
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
class TextPath:
 def __init__(self,text):self.text=text
 def open(self):return io.StringIO(self.text)
 def read_bytes(self):return self.text.encode()
def png(data):
 im=Image.open(io.BytesIO(data));im.load();ar=np.asarray(im.convert('RGB'));return dict(size=list(im.size),format=im.format,nonblank=bool(np.ptp(ar.reshape(-1,3),axis=0).max()>0))
def first_layers(code,printer,project):
 if printer=='Bambu':code=normalize_bambu(code,project)
 labels=re.findall(r'^EXCLUDE_OBJECT_DEFINE NAME=(\S+)',code,re.M);lookup={l:f'instance-{i}' for i,l in enumerate(labels)}
 for l,k in sorted(lookup.items(),key=lambda x:-len(x[0])):code=code.replace('NAME='+l,'NAME='+k)
 paths=bottom.first_layer_paths(code);rows=[]
 for label,key in lookup.items():
  kinds=paths.get(key,{});m=unary_union([s for k,s in kinds.items() if not any(t in k.lower() for t in ['support','brim','skirt'])]);s=unary_union([s for k,s in kinds.items() if 'support' in k.lower()]);rows.append(dict(native_label=label,model_area_mm2=m.area,support_area_mm2=s.area,contact_present=m.area+s.area>0))
 return rows

def native(pack):
 rows=[]
 for v in pack['variants']:
  row=dict(printer=v['printer'],group=v['group'],errors=[]);rows.append(row)
  try:
   project=Path(v['project']);archive=Path(v['archive']);assert sha(project)==v['project_sha256'];assert sha(archive)==v['archive_sha256']
   with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None;names=[n for n in z.namelist() if n.endswith('.gcode')];assert len(names)==1
    data=z.read(names[0]);cfg=json.loads(z.read('Metadata/project_settings.config'));th=[png(z.read(n)) for n in z.namelist() if re.fullmatch(r'Metadata/plate_\d+\.png',n)];assert th and all(t['nonblank'] and t['format']=='PNG' for t in th)
   code=data.decode();assert hashlib.sha256(data).hexdigest()==v['gcode_sha256'];assert cfg['print_sequence']=='by layer'
   with zipfile.ZipFile(project) as pz: projectcfg=json.loads(pz.read('Metadata/project_settings.config'))
   assert cfg.get('filament_colour')==projectcfg.get('filament_colour'),'Native preview color does not match saved project color'
   assert len(cfg.get('filament_ids',[]))==len(cfg['filament_type'])==1 # GUI custom identity may be an empty string, never an empty vector.
   row.update(archive_sha256=sha(archive),project_sha256=sha(project),gcode_sha256=v['gcode_sha256'],native_thumbnails=th,estimated_time=v['estimated_time'])
   if v['native_reused']:assert archive.read_bytes()==Path(v['native_source']).read_bytes()
   if v['printer']=='Elegoo':
    assert Path(v['gcode']).read_bytes()==data
    thumbs=[]
    for m in re.finditer(r'; thumbnail begin (\d+)x(\d+) \d+\s*\n(.*?); thumbnail end',code,re.S):
     raw=''.join(re.sub(r'^;\s*','',x).strip() for x in m.group(3).splitlines());thumbs.append(png(base64.b64decode(raw,validate=True)))
    assert any(t['size']==[144,144] and t['nonblank'] and t['format']=='PNG' for t in thumbs)
    spacing=parse(TextPath(code))[0];assert spacing['passed_nonoverlap_and_inside_bed'];assert spacing['object_count']==spacing['extruding_objects']==v['expected_count'];gap=spacing['minimum_interobject_extrusion_gap_lower_bound_mm'];bounds=spacing['actual_extrusion_bounds_conservative_mm']
   else:
    spacing=audit_archive(archive,v['expected_count']);assert spacing['passed'];gap=spacing['minimum_interobject_gap_lower_bound_mm'];boxes=[r['extrusion_bounds_mm'] for r in spacing['objects']];bounds=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)]
   assert gap>=3.999;center=[(bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2];assert all(abs(c-128)<=1 for c in center)
   first=first_layers(code,v['printer'],project);assert len(first)==v['expected_count'] and all(r['contact_present'] for r in first)
   assert all(r['model_area_mm2']>200 for r in first if any(k in r['native_label'] for k in ['community-64.stl','community-66.stl']))
   row.update(spacing=spacing,complete_footprint_center_xy_mm=center,first_layer_instances=first)
  except Exception as ex:row['errors'].append(str(ex) or traceback.format_exc())
  row['passed']=not row['errors'];print(row['printer'],row['group'],'native',row['passed'],row['errors'],flush=True)
 return dict(passed=len(rows)==10 and all(r['passed'] for r in rows),variants=rows,packaging_sha256=sha(D/'packaging.json'))

def handoff(pack):
 index=json.loads((D/'handoff-index.json').read_text());assert index['packaging_sha256']==sha(D/'packaging.json')
 ready=index['primary_files'];assert len(ready)==6 and sum(x['count'] for x in ready)==89
 assert {p.resolve() for p in (D/'READY-TO-PRINT').iterdir() if p.is_file()}=={Path(x['copy']).resolve() for x in ready}
 readme=(D/'README.md').read_text()
 for r in ready:
  assert sha(r['copy'])==r['sha256'];assert sha(r['archive'])==r['archive_sha256'];assert sha(r['project'])==r['project_sha256'];assert str(Path(r['copy']).relative_to(D)) in readme
  v=next(v for v in pack['variants'] if v['printer']==r['printer'] and v['group']==r['group']);assert v['primary'] and v['expected_count']==r['count']
  assert Path(r['copy']).read_bytes()==Path(v['gcode'] if v['printer']=='Elegoo' else v['archive']).read_bytes()
 for v in pack['variants']:
  assert str(Path(v['project']).relative_to(D)) in readme;assert str(Path(v['gcode'] if v['printer']=='Elegoo' else v['archive']).relative_to(D)) in readme
 assert 'physical' in readme.lower() and '0.4' in readme and 'PLA' in readme
 return dict(passed=True,ready_file_count=6,primary_instance_count=89,index_sha256=sha(D/'handoff-index.json'))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=['audit','native','handoff','all'],default='all');args=ap.parse_args();pack=json.loads((D/'packaging.json').read_text());passed=True
 if args.scope in ['audit','all']:
  r=geometry.verify(D/'packaging.json');(D/'geometry/final-geometry-verification.json').write_text(json.dumps(r,indent=2)+'\n');passed &=r['passed'];print('SURFACE_AUDIT_PASS' if r['passed'] else 'SURFACE_AUDIT_FAIL')
 if args.scope in ['native','all']:
  r=native(pack)
  features=json.loads((D/'geometry/native-functional-verification.json').read_text())
  try:
   assert features['passed'] and features['complete_ten_variants'] and features['complete_primary_89']
   assert features['manifest_sha256']==sha(D/'packaging.json')
   assert len(features['variants'])==10
   for v in pack['variants']:
    f=next(f for f in features['variants'] if f['printer']==v['printer'] and f['group']==v['group'])
    assert f['passed'] and f['project_sha256']==sha(v['project']) and f['native_sha256']==sha(v['archive'])
   r['native_functional_features_passed']=True
   r['native_functional_report_sha256']=sha(D/'geometry/native-functional-verification.json')
  except Exception as ex:r['passed']=False;r['native_functional_features_passed']=False;r['native_functional_error']=str(ex) or traceback.format_exc()
  (D/'native-verification.json').write_text(json.dumps(r,indent=2)+'\n');passed &=r['passed'];print('NATIVE_SURFACE_PACK_PASS' if r['passed'] else 'NATIVE_SURFACE_PACK_FAIL')
 if args.scope in ['handoff','all']:
  try:r=handoff(pack)
  except Exception as ex:r=dict(passed=False,error=str(ex) or traceback.format_exc())
  (D/'handoff-verification.json').write_text(json.dumps(r,indent=2)+'\n');passed &=r['passed'];print('SURFACE_HANDOFF_PASS' if r['passed'] else 'SURFACE_HANDOFF_FAIL',r)
 return 0 if passed else 1
if __name__=='__main__':sys.exit(main())
