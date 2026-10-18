from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,hashlib,itertools,runpy,sys,subprocess
D=Path(__file__).resolve().parent;C=D.parent;OLD=C/'06-CENTERED-20260929';N='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
E.register_namespace('',N[1:-1]);E.register_namespace('p','http://schemas.microsoft.com/3dmanufacturing/production/2015/06')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pack(parts):
 candidates=[]
 for perm in itertools.permutations(parts):
  for cuts in range(1<<(len(parts)-1)):
   groups=[[perm[0]]]
   for i,p in enumerate(perm[1:]):
    if cuts&(1<<i):groups.append([])
    groups[-1].append(p)
   for columns in [False,True]:
    sizes=[(sum(p['h' if columns else 'w'] for p in g)+4.5*(len(g)-1),max(p['w' if columns else 'h'] for p in g)) for g in groups]
    across=max(w for w,h in sizes);along=sum(h for w,h in sizes)+4.5*(len(groups)-1);placed=[];y=0
    for group,(w,h) in zip(groups,sizes):
     x=(across-w)/2
     for p in group:
      placed.append({**p,'x':y if columns else x,'y':x if columns else y});x+=p['h' if columns else 'w']+4.5
     y+=h+4.5
    width,height=(along,across) if columns else (across,along);score=(max(width,height),width*height,abs(width-height))
    candidates.append((score,width,height,placed))
 _,w,h,p=min(candidates,key=lambda v:v[0]);return w,h,p,len(candidates)
def run():
 if '--slice' in sys.argv:
  m=json.loads((D/'centering-manifest.json').read_text())
  for r in m['projects']:
   if r['printer']!='Bambu':continue
   out=Path(r['project']).parent;cmd=['/Applications/BambuStudio.app/Contents/MacOS/BambuStudio','--arrange','0','--orient','0','--slice','1','--min-save','--export-3mf',r['native_archive_name'],'--outputdir',str(out),r['project']];(out/'native-command.json').write_text(json.dumps(cmd,indent=2))
   with (out/'slice.log').open('w') as log:p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
   (out/'native-result.json').write_text(json.dumps({'exit_code':p.returncode}));print(r['printer'],r['color'],p.returncode,flush=True)
  return
 old=json.loads((OLD/'centering-manifest.json').read_text());audits=json.loads((OLD/'centering-verification.json').read_text());parser=runpy.run_path(str(C/'audit_spacing.py'))['parse'];rows=[]
 originals=[{'path':str(p),'sha256':sha(p)} for p in C.rglob('*') if p.is_file() and D not in p.parents and p.suffix in ['.3mf','.gcode']]
 for r in old['projects']:
  printer,color=r['printer'],r['color'];src=Path(r['project']);a=next(a for a in audits['projects'] if a['printer']==printer and a['color']==color)
  z=zipfile.ZipFile(src);files={n:z.read(n) for n in z.namelist()};st=E.fromstring(files['Metadata/model_settings.config']);names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in st.findall('object')};parts=[]
  if printer=='Bambu':
   labels={i.find("metadata[@key='object_id']").get('value'):i.find("metadata[@key='identify_id']").get('value') for i in st.findall('plate/model_instance')};boxes={p['object_label']:p['extrusion_bounds_mm'] for p in a['spacing_audit']['objects']};byid={k:boxes[v] for k,v in labels.items()}
  else:
   _,hulls,_,rad=parser(src.parent/'audit-extracted.gcode');byid={k:list(next(h for label,h in hulls.items() if label.startswith(name+'_id_')).buffer(rad).bounds) for k,name in names.items()}
  for key,b in byid.items():parts.append({'objectid':key,'name':names[key],'source_bbox':b,'w':b[2]-b[0],'h':b[3]-b[1]})
  width,height,placed,trials=pack(parts);model=E.fromstring(files['3D/3dmodel.model']);moves={p['objectid']:[128-width/2+p['x']-p['source_bbox'][0],128-height/2+p['y']-p['source_bbox'][1]] for p in placed};trans=[]
  for it in model.find(N+'build'):
   v=list(map(float,it.get('transform').split()));before=v[:];dx,dy=moves[it.get('objectid')];correction=json.loads((D/'native-centering-corrections.json').read_text()).get(printer+'/'+color,[0,0]) if (D/'native-centering-corrections.json').exists() else [0,0];dx+=correction[0];dy+=correction[1];v[9]+=dx;v[10]+=dy;it.set('transform',' '.join(f'{x:.14g}' for x in v));trans.append({'objectid':it.get('objectid'),'before':before,'after':v,'xy_translation_mm':[dx,dy]})
  out=D/printer/color;out.mkdir(parents=True,exist_ok=True);dst=out/f'MicroDuck_{printer}_{color}_COMPACT_editable.3mf'
  with zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED) as zz:
   for n,data in files.items():zz.writestr(n,E.tostring(model,encoding='utf-8',xml_declaration=True) if n=='3D/3dmodel.model' else data)
  before=a['actual_footprint_bounds_mm'];rows.append({'printer':printer,'color':color,'source':str(src),'source_sha256':sha(src),'project':str(dst),'project_sha256':sha(dst),'transforms':trans,'native_archive_name':f'MicroDuck_{printer}_{color}_COMPACT.gcode.3mf','baseline_width_height_mm':[before[2]-before[0],before[3]-before[1]],'predicted_width_height_mm':[width,height],'predicted_min_bed_margin_mm':(256-max(width,height))/2,'placement':placed,'optimization_trials':trials,'objective':'Minimize max(width,height), then area, then aspect difference over every order/row partition and column partition. Fixed orientation, per-object XY translation only. Conservative support/bead boxes separated4.5mm to target>=4mm after native regeneration.'});print(dst,flush=True)
 (D/'centering-manifest.json').write_text(json.dumps({'problem_ids':['P5','P6'],'originals':originals,'projects':rows},indent=2)+'\n')
if __name__=='__main__':run()
