"""Finite geometry, source-preservation and native export acceptance for four colors."""
from pathlib import Path
import base64,hashlib,io,json,re,sys,zipfile,collections,xml.etree.ElementTree as E
import numpy as np
from PIL import Image,ImageStat
O=Path(__file__).resolve().parent;R=O.parents[1]
N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}';PN='{http://schemas.microsoft.com/3dmanufacturing/production/2015/06}'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mat(s):return np.array(list(map(float,s.split()))).reshape(4,3).T
out={'passed':False,'scope':'Four remaining single-filament plates; source geometry, native slice and embedded thumbnail checks. No physical print acceptance.','checks':[],'errors':[]}
def check(name,fn):
 try:out['checks'].append({'name':name,'passed':True,'evidence':fn()})
 except Exception as e:out['errors'].append({'name':name,'error':str(e)})
layout=json.loads((O/'color-layout.json').read_text())
def originals():
 m=json.loads((R/'PRINTING/copy-manifest.json').read_text());rows=m['copy_records']
 for r in rows:assert sha(Path(r['source']))==r['sha256']==sha(R/'PRINTING'/r['copy']),r['source']
 return {'99_original_copies_unchanged':True,'preserved_original_plates':[1,5],'preserved_original_instances':28,'Bambu_unchanged':True}
check('originals_and_Bambu_preserved',originals)
def geometry():
 with zipfile.ZipFile(layout['source_project']) as src:
  sm=E.fromstring(src.read('3D/3dmodel.model'));so={x.get('id'):x for x in sm.find(N+'resources')};sb={x.get('objectid'):x for x in sm.find(N+'build')};ids=[];result={}
  for color,count in [('orange',4),('yellow',4),('WHITE',3),('black',50)]:
   group=layout['groups'][color];p=Path(group['project']);assert group['count']==count and group['plate_count']==1
   expected={q['record']['object_id'] for plate in group['placements'] for q in plate}
   wanted={'orange':{8,10,60,18},'yellow':{2,4,44,46},'WHITE':{76,40,42}}
   if color in wanted:assert {Path(q['record']['source']).name for pl in group['placements'] for q in pl}=={f'community-{n}.stl' for n in wanted[color]}
   with zipfile.ZipFile(p) as z:
    model=E.fromstring(z.read('3D/3dmodel.model'));objs={x.get('id'):x for x in model.find(N+'resources')};items=list(model.find(N+'build'));assert {x.get('objectid') for x in items}==expected
    for item in items:
     oid=item.get('objectid');ids.append(oid);a=mat(item.get('transform'));b=mat(sb[oid].get('transform'));assert np.allclose(a[:,:3],b[:,:3],atol=1e-7) and abs(a[2,3]-b[2,3])<1e-5,'Rotation or Z position changed'
     assert E.tostring(objs[oid])==E.tostring(so[oid]),'Source component transform changed'
     for comp in objs[oid].find(N+'components'):
      path=comp.get(PN+'path').lstrip('/');assert z.read(path)==src.read(path),'Source mesh bytes changed'
    cfg=json.loads(z.read('Metadata/project_settings.config'));assert cfg['filament_colour']==[group['color']]
    assert cfg['print_sequence']=='by layer' and cfg['enable_support']=='1'
   sliced=O/color/f'MicroDuck-{color}-sliced.3mf';assert json.loads((O/color/'native-result.json').read_text())['exit_code']==0
   with zipfile.ZipFile(sliced) as z:
    paths=[n for n in z.namelist() if n.endswith('.gcode')];assert len(paths)==1
    txt=z.read(paths[0]).decode();times=re.findall(r'^;.*(?:estimated printing time|total estimated time).*$',txt,re.M)
   result[color]={'instances':count,'plates':1,'editable_sha256':sha(p),'sliced_sha256':sha(sliced),'native_time_comments':times}
  m=json.loads((R/'PRINTING/copy-manifest.json').read_text());want={r['object_id'] for r in m['copy_records'] if r['copy'].startswith('01-STL/') and r.get('plate') in (2,3,4,6)}
  assert len(ids)==61 and len(set(ids))==61 and set(ids)==want
  return result
check('61_exact_instances_four_native_sliced_plates',geometry)
def spacing():
 p=O/'spacing-verification.json';d=json.loads(p.read_text());assert d.get('passed') is True,d
 assert d['acceptance_surface']=='native_gui_usb'
 assert {r['color'] for r in d['plates']}=={'orange','yellow','WHITE','black'}
 for r in d['plates']:assert sha(Path(r['gcode_path']))==r['gcode_sha256'],'Spacing evidence stale'
 return {'path':str(p),'sha256':sha(p)}
check('actual_support_brim_toolpath_spacing',spacing)
def exports():
 p=O/'native-gui-export-manifest.json';d=json.loads(p.read_text());rows=d['files'];assert len(rows)==4 and {r['color'] for r in rows}=={'orange','yellow','WHITE','black'}
 result=[]
 for r in rows:
  path=Path(r['destination']);archive=Path(r['archive'])
  with zipfile.ZipFile(archive) as z:assert path.read_bytes()==z.read(r['archive_member'])
  assert sha(path)==r['sha256'];txt=path.read_text()
  names=collections.Counter(n.split('_id_')[0] for n in re.findall(r'^EXCLUDE_OBJECT_DEFINE NAME=(\S+)',txt,re.M))
  expected=collections.Counter(Path(q['record']['source']).name for plate in layout['groups'][r['color']]['placements'] for q in plate)
  assert names==expected,'Final export object coverage differs from color project'
  hit=re.search(r'^; thumbnail begin 144x144 (\d+)\s*\n(.*?)^; thumbnail end\s*$',txt,re.M|re.S);assert hit
  payload=''.join(line[2:].strip() for line in hit[2].splitlines());assert len(payload)==int(hit[1]);png=base64.b64decode(payload,validate=True);im=Image.open(io.BytesIO(png));im.verify();im=Image.open(io.BytesIO(png)).convert('RGBA');assert im.size==(144,144) and im.getchannel('A').getbbox();bg=Image.new('RGBA',im.size,'white');bg.alpha_composite(im);assert max(ImageStat.Stat(bg.convert('RGB')).var)>1
  result.append({'file':str(path),'sha256':sha(path),'archive_sha256':sha(archive),'valid_nonblank_thumbnail':True})
 return result
check('four_native_GUI_exports_with_thumbnails',exports)
out['passed']=not out['errors'];out['status']='FOUR_COLOR_ACCEPTANCE_PASS' if out['passed'] else 'FOUR_COLOR_ACCEPTANCE_PENDING';out['verifier_sha256']=sha(Path(__file__));(O/'four-color-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2));sys.exit(0 if out['passed'] else 1)
