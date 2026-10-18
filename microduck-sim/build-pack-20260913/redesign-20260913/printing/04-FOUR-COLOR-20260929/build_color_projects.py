from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,hashlib,copy,subprocess
import numpy as np
O=Path(__file__).resolve().parent;R=O.parents[1];P=R/'printing-elegoo-20260929';src=P/'MicroDuck-Centauri-Carbon-Orca.3mf'
NS='http://schemas.microsoft.com/3dmanufacturing/core/2015/02';PN='http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
E.register_namespace('',NS);E.register_namespace('p',PN)
def tag(s):return '{'+NS+'}'+s
def mat(s):
 m=np.eye(4);m[:3,:]=np.array(list(map(float,s.split()))).reshape(4,3).T;return m
def fmt(m):return ' '.join(f'{v:.9g}' for v in m[:3,:].T.ravel())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
records=[r for r in json.loads((R/'PRINTING/copy-manifest.json').read_text())['copy_records'] if r['copy'].startswith('01-STL/') and r['plate'] in (2,3,4,6)]
assign={'orange':{8,10,60,18},'yellow':{2,4,44,46},'WHITE':{76,40,42}}
colors={'orange':'#FF8000','yellow':'#FFFF00','WHITE':'#FFFFFF','black':'#202020'}
def color(r):
 for c,ids in assign.items():
  if Path(r['source']).name in {f'community-{i}.stl' for i in ids}:return c
 return 'black'
with zipfile.ZipFile(src) as z:files={n:z.read(n) for n in z.namelist()}
model=E.fromstring(files['3D/3dmodel.model']);settings=E.fromstring(files['Metadata/model_settings.config']);resources=model.find(tag('resources'));build=model.find(tag('build'));objects={x.get('id'):x for x in resources};items={x.get('objectid'):x for x in build};inst={x.find("metadata[@key='object_id']").get('value'):x for p in settings.findall('plate') for x in p.findall('model_instance')}
bounds={}
for r in records:
 oid=r['object_id'];verts=[]
 for comp in objects[oid].find(tag('components')):
  child=E.fromstring(files[comp.get('{'+PN+'}path').lstrip('/')]);ob=next(x for x in child.find(tag('resources')) if x.get('id')==comp.get('objectid'));v=np.array([[float(q.get(k)) for k in ('x','y','z')] for q in ob.find(tag('mesh')).find(tag('vertices'))]);m=mat(items[oid].get('transform'))@mat(comp.get('transform'));verts.append(v@m[:3,:3].T+m[:3,3])
 v=np.concatenate(verts);bounds[oid]=np.array([v.min(0),v.max(0)])
# Reserve measured original support/brim footprints; actual new slice is checked again.
spacing=json.loads((R/'PRINTING/analysis-spacing-20260929.json').read_text())
extensions={}
for plate in spacing['gcode_measurements']:
 for q in plate.get('details',[]):
  name=q['name'].split('_id_')[0];ext=np.maximum(0,q['extension_beyond_model_bbox_mm']);extensions[name]=np.maximum(extensions.get(name,np.zeros(4)),ext)
footprints={}
for r in records:
 oid=r['object_id'];ext=extensions[Path(r['source']).name];box=bounds[oid].copy();box[0,:2]-=ext[:2];box[1,:2]+=ext[2:];footprints[oid]=box
summary={'source_project':str(src),'source_sha256':sha(src),'requested_support_footprint_gap_mm':4,'bed_margin_mm':10,'preserved_original_plates':[1,5],'preserved_instance_count':28,'regrouped_instance_count':61,'groups':{}}
for c,hexcolor in colors.items():
 selected=[r for r in records if color(r)==c];placed=[];remaining=sorted(selected,key=lambda r:-np.prod((footprints[r['object_id']][1]-footprints[r['object_id']][0])[:2]));plates=[]
 while remaining:
  placed=[];later=[]
  for r in remaining:
   oid=r['object_id'];w,h=(footprints[oid][1]-footprints[oid][0])[:2];best=None
   xs=sorted({10.,*(q['x']+q['w']+4 for q in placed)});ys=sorted({10.,*(q['y']+q['h']+4 for q in placed)})
   for y in ys:
    for x in xs:
     if x+w>246 or y+h>246:continue
     if any(not(x+w+4<=q['x']+1e-6 or q['x']+q['w']+4<=x+1e-6 or y+h+4<=q['y']+1e-6 or q['y']+q['h']+4<=y+1e-6) for q in placed):continue
     score=(max(y+h,max([q['y']+q['h'] for q in placed] or [0])),x)
     if best is None or score<best[0]:best=(score,x,y)
   if best:placed.append(dict(record=r,x=best[1],y=best[2],w=float(w),h=float(h)))
   else:later.append(r)
  assert placed,'Part too large for build area';plates.append(placed);remaining=later
 if c=='black':
  candidate=spacing['scope_update_20260929']['black_single_plate_candidate']['candidate'];lookup={(r['plate'],Path(r['source']).name+'_id_'+str(int(Path(r['copy']).name.split('_')[0])-1)+'_copy_0'):r for r in selected};placed=[]
  detail_lookup={(pn,q['name']):q for pn,plate in enumerate(spacing['gcode_measurements'],1) for q in plate.get('details',[])}
  for q in candidate:
   r=lookup[(q['source_plate'],q['id'])];oid=r['object_id'];detail=detail_lookup[(q['source_plate'],q['id'])];modelbox=detail['model_polygon_bbox_mm'];sourcebox=q['source_bbox'];footprints[oid]=bounds[oid].copy();footprints[oid][0,:2]+=np.array(sourcebox[:2])-np.array(modelbox[:2]);footprints[oid][1,:2]=footprints[oid][0,:2]+[q['w'],q['h']]
   placed.append(dict(record=r,x=q['x'],y=q['y'],w=q['w'],h=q['h']))
  assert len(placed)==50;plates=[placed]
 d=O/c;d.mkdir(exist_ok=True);mo=copy.deepcopy(model);res=mo.find(tag('resources'));bu=mo.find(tag('build'));ids={r['object_id'] for r in selected}
 for el in list(res):
  if el.get('id') not in ids:res.remove(el)
 for el in list(bu):
  if el.get('objectid') not in ids:bu.remove(el)
 st=copy.deepcopy(settings)
 for el in list(st):
  if el.tag in ('plate','assemble') or (el.tag=='object' and el.get('id') not in ids):st.remove(el)
 for pn,plate in enumerate(plates,1):
  pe=E.SubElement(st,'plate')
  for key,val in [('plater_id',str(pn)),('plater_name',f'{c}-{pn}'),('locked','false')]:E.SubElement(pe,'metadata',key=key,value=val)
  for q in plate:
   oid=q['record']['object_id'];item=next(x for x in bu if x.get('objectid')==oid);m=mat(item.get('transform'));m[0,3]+=q['x']-footprints[oid][0,0]+(pn-1)*307.2;m[1,3]+=q['y']-footprints[oid][0,1];item.set('transform',fmt(m));pe.append(copy.deepcopy(inst[oid]));q['new_transform']=fmt(m)
 cfg=json.loads(files['Metadata/project_settings.config']);cfg['filament_colour']=[hexcolor];cfg['extruder_colour']=[hexcolor]
 project=d/f'MicroDuck-{c}-editable.3mf'
 with zipfile.ZipFile(project,'w',zipfile.ZIP_DEFLATED) as out:
  for n,data in files.items():
   if n.startswith('Metadata/') and n!='Metadata/project_settings.config' and n!='Metadata/model_settings.config':continue
   if n=='3D/3dmodel.model':data=E.tostring(mo,encoding='utf-8',xml_declaration=True)
   elif n=='Metadata/model_settings.config':data=E.tostring(st,encoding='utf-8',xml_declaration=True)
   elif n=='Metadata/project_settings.config':data=json.dumps(cfg).encode()
   out.writestr(n,data)
 filament=json.loads((P/'filament.json').read_text());filament['filament_colour']=[hexcolor];(d/'filament.json').write_text(json.dumps(filament,indent=2))
 summary['groups'][c]={'count':len(selected),'reserved_footprint_gap_mm':2 if c=='black' else 4,'plate_count':len(plates),'color':hexcolor,'project':str(project),'project_sha256':sha(project),'placements':plates}
(O/'color-layout.json').write_text(json.dumps(summary,indent=2)+'\n')
print({c:(g['count'],g['plate_count']) for c,g in summary['groups'].items()},flush=True)
for c,g in summary['groups'].items():
 if '--black-only' in __import__('sys').argv and c!='black':continue
 d=O/c;cmd=['/Volumes/OrcaSlicer/OrcaSlicer.app/Contents/MacOS/OrcaSlicer','--allow-newer-file','--arrange','0','--orient','0','--slice','0','--load-settings',str(P/'machine.json')+';'+str(P/'process.json'),'--load-filaments',str(d/'filament.json'),'--export-3mf',f'MicroDuck-{c}-sliced.3mf','--outputdir',str(d),g['project']]
 (d/'native-command.json').write_text(json.dumps(cmd,indent=2))
 with (d/'slice.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 (d/'native-result.json').write_text(json.dumps({'exit_code':r.returncode},indent=2));print(c,'slice exit',r.returncode,flush=True)
