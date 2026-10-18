from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,hashlib,collections,io,re,sys
import numpy as np
from PIL import Image,ImageStat
D=Path(__file__).resolve().parent;N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}';PN='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((D/'conversion-manifest.json').read_text());out={'passed':False,'errors':[],'checks':[]}
def check(name,f):
 try:out['checks'].append({'name':name,'passed':True,'evidence':f()})
 except Exception as e:out['errors'].append({'name':name,'error':str(e)})
def preserved():
 rows=json.loads((D/'preserved-files.json').read_text())['files']
 for r in rows:assert sha(Path(r['path']))==r['sha256'],r['path']
 return {'unchanged_existing_project_and_print_files':len(rows)}
check('Existing Elegoo and Bambu artifacts preserved',preserved)
def convert():
 with zipfile.ZipFile(manifest['original_bambu_project']) as z:base=json.loads(z.read('Metadata/project_settings.config'))
 result=[]
 for r in manifest['colors']:
  assert sha(Path(r['source_color_project']))==r['source_sha256'];assert sha(Path(r['project']))==r['project_sha256']
  with zipfile.ZipFile(r['source_color_project']) as src,zipfile.ZipFile(r['project']) as new:
   a=E.fromstring(src.read('3D/3dmodel.model'));b=E.fromstring(new.read('3D/3dmodel.model'));aa={x.get('objectid'):x for x in a.find(N+'build')};bb={x.get('objectid'):x for x in b.find(N+'build')};assert set(aa)==set(bb) and len(aa)==r['count']
   assert E.tostring(a.find(N+'resources'))==E.tostring(b.find(N+'resources'))
   for oid in aa:
    x=np.array(list(map(float,aa[oid].get('transform').split())));y=np.array(list(map(float,bb[oid].get('transform').split())));x[10]+=25;assert np.allclose(x,y,atol=1e-7)
   for ob in b.find(N+'resources'):
    for comp in ob.find(N+'components'):
     p=comp.get(PN+'path').lstrip('/');assert new.read(p)==src.read(p)
   cfg=json.loads(new.read('Metadata/project_settings.config'));want=dict(base);want['filament_colour']=['#FFFFFF' if r['color']=='WHITE' else '#FFFF00'];want['extruder_colour']=want['filament_colour'];assert cfg==want,'Config differs beyond requested colors'
   assert cfg['printer_model']=='Bambu Lab X1 Carbon' and cfg['nozzle_diameter']==['0.4'] and cfg['curr_bed_type']=='Cool Plate' and cfg['filament_type']==['PLA']
  assert json.loads((Path(r['project']).parent/'native-exit.json').read_text())['exit_code']==0
  result.append({'color':r['color'],'instances':len(aa),'translation_mm':[0,25,0],'source_geometry_and_orientation_unchanged':True})
 return result
check('Exact 7 color-assigned instances and Bambu profile',convert)
def final():
 results=[]
 for r in manifest['colors']:
  color=r['color'];original=D/color/f'MicroDuck_Bambu_{color}.gcode.3mf';p=D/'SD-CARD'/original.name;assert p.read_bytes()==original.read_bytes()
  expected={'WHITE':{'community-76.stl','community-40.stl','community-42.stl'},'yellow':{'community-2.stl','community-4.stl','community-44.stl','community-46.stl'}}[color]
  with zipfile.ZipFile(p) as z:
   assert [n for n in z.namelist() if n.endswith('.gcode')]==['Metadata/plate_1.gcode'];g=z.read('Metadata/plate_1.gcode');txt=g.decode();assert 'M620' in txt and 'M621' in txt and 'PRINT_START' not in txt
   md5=z.read('Metadata/plate_1.gcode.md5').decode().strip();assert hashlib.md5(g).hexdigest().lower()==md5.lower()
   cfg=json.loads(z.read('Metadata/project_settings.config'))
   for key,value in [('printer_model','Bambu Lab X1 Carbon'),('curr_bed_type','Cool Plate'),('nozzle_diameter',['0.4']),('filament_type',['PLA']),('layer_height','0.2'),('wall_loops','4'),('sparse_infill_density','30%'),('print_sequence','by layer')]:assert cfg[key]==value,(key,cfg[key])
   si=E.fromstring(z.read('Metadata/slice_info.config'));plates=si.findall('plate');assert len(plates)==1;objs=plates[0].findall('object');assert len(objs)==r['count'] and {x.get('name') for x in objs}==expected and all(x.get('skipped')=='false' for x in objs)
   assert plates[0].find("metadata[@key='outside']").get('value')=='false'
   assert len(plates[0].findall('filament'))==1
   thumbs=[]
   for n in ['Metadata/plate_1.png','Metadata/plate_1_small.png']:
    data=z.read(n);im=Image.open(io.BytesIO(data));im.verify();im=Image.open(io.BytesIO(data)).convert('RGBA');assert max(ImageStat.Stat(im.convert('RGB')).var)>1 and im.getchannel('A').getbbox();thumbs.append({'name':n,'size':im.size})
   result={'color':color,'file':str(p),'sha256':sha(p),'gcode_sha256':hashlib.sha256(g).hexdigest(),'instances':len(objs),'thumbnails':thumbs,'estimated_seconds':int(plates[0].find("metadata[@key='prediction']").get('value')),'time':re.findall(r'^;.*total estimated time.*$',txt,re.M)};results.append(result)
 return results
check('Native Bambu SD packages, thumbnails, settings and coverage',final)
def spacing():
 d=json.loads((D/'spacing-verification.json').read_text());assert d['passed'] is True
 assert set(d['plates'])=={'WHITE','yellow'}
 for r in d['plates'].values():
  assert sha(Path(r['archive_path']))==r['archive_sha256']
 return {'report':str(D/'spacing-verification.json'),'sha256':sha(D/'spacing-verification.json')}
check('Actual final toolpath supports and machine exclusion clearance',spacing)
out['passed']=not out['errors'];out['status']='BAMBU_COLORS_ACCEPTANCE_PASS' if out['passed'] else 'BAMBU_COLORS_ACCEPTANCE_FAIL';(D/'bambu-colors-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));sys.exit(0 if out['passed'] else 1)
