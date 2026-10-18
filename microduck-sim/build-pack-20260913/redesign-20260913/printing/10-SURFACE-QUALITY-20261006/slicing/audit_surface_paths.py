"""Measure actual native paths at every Z; digital diagnostics, never physical acceptance.
Usage: python audit_surface_paths.py --gcode FILE [--project FILE --printer Bambu] --output JSON
Support coverage means sampled MODEL path has a nearby support-interface bead at its
expected support top Z, not that the manufactured underside will be smooth. Model
holes and mechanically important seats require separate exact-mesh region checks.
"""
from pathlib import Path
import argparse,collections,hashlib,json,math,re,sys,zipfile
import numpy as np
from scipy.spatial import cKDTree
D=Path(__file__).resolve().parent; P=D.parents[1]
def normalize_bambu(code,project):
 import xml.etree.ElementTree as ET
 with zipfile.ZipFile(project) as zz: st=ET.fromstring(zz.read('Metadata/model_settings.config'))
 names={o.get('id'):o.find("metadata[@key='name']").get('value') for o in st.findall('object')}
 labels={i.find("metadata[@key='identify_id']").get('value'):names[i.find("metadata[@key='object_id']").get('value')] for i in st.findall('plate/model_instance')}
 out=[f'EXCLUDE_OBJECT_DEFINE NAME={name}_id_{label}_copy_0' for label,name in labels.items()]
 for line in code.splitlines():
  if line.startswith('; start printing object, unique label id:'):
   label=line.rsplit(':',1)[1].strip();line=f'EXCLUDE_OBJECT_START NAME={labels[label]}_id_{label}_copy_0'
  elif line.startswith('; stop printing object, unique label id:'):line='EXCLUDE_OBJECT_END'
  elif line.startswith('; FEATURE:'):line=';TYPE:'+line.split(':',1)[1].strip()
  elif line.startswith('; LINE_WIDTH:'):line=';WIDTH:'+line.split(':',1)[1].strip()
  elif line.startswith('; LAYER_HEIGHT:'):line=';HEIGHT:'+line.split(':',1)[1].strip()
  out.append(line)
 return '\n'.join(out)
FIELDS=['layer_height','support_top_z_distance','support_bottom_z_distance','support_interface_spacing','support_bottom_interface_spacing','support_interface_top_layers','support_interface_bottom_layers','support_object_xy_distance','support_type','support_style','bridge_flow','bridge_speed','internal_bridge_speed','bottom_shell_layers','bottom_shell_thickness','bottom_surface_pattern','enable_support','support_threshold_angle','thick_bridges','independent_support_layer_height']
def number(v,default):
 try:return float(v[0] if isinstance(v,list) else v)
 except (ValueError,TypeError):return default
def read_code(path,project=None,printer='Elegoo'):
 path=Path(path);payload=path.read_bytes();cfg={}
 if zipfile.is_zipfile(path):
  with zipfile.ZipFile(path) as z:
   names=[n for n in z.namelist() if n.endswith('.gcode')];assert len(names)==1,names;data=z.read(names[0]);cfg=json.loads(z.read('Metadata/project_settings.config'))
 else:data=payload
 if project:
  with zipfile.ZipFile(project) as z:cfg=json.loads(z.read('Metadata/project_settings.config'))
 code=data.decode()
 if not cfg:
  cfg={m[1]:m[2] for m in re.finditer(r'^; (\w+) = (.*)$',code,re.M)}
 if printer=='Bambu':
  assert project,'Bambu requires project to resolve numeric native labels'
  code=normalize_bambu(code,project)
 return code,cfg,hashlib.sha256(payload).hexdigest(),hashlib.sha256(data).hexdigest()
def samples(points,step=.25):
 out=[]
 for a,b in zip(points,points[1:]):
  dist=math.dist(a,b); n=max(1,math.ceil(dist/step));out.extend([(a[0]+(b[0]-a[0])*(j+.5)/n,a[1]+(b[1]-a[1])*(j+.5)/n) for j in range(n)])
 return out
def parse(code,collect_all=False):
 cur=None;kind='Custom';x=y=z=0.;width=.4;height=.2;feed=0.;relative=False;ev=0.;paths=collections.defaultdict(lambda:collections.defaultdict(list));features=collections.defaultdict(lambda:collections.defaultdict(lambda:{'length_mm':0.,'min_speed_mm_s':float('inf'),'max_speed_mm_s':0.,'segments':0}))
 names=set()
 for line in code.splitlines():
  if line.startswith('EXCLUDE_OBJECT_DEFINE'):names.add(re.search(r'NAME=(\S+)',line)[1])
  if line.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(\S+)',line)[1]
  if line.startswith('EXCLUDE_OBJECT_END'):cur=None
  if line.startswith(';TYPE:'):kind=line[6:].strip()
  if line.startswith(';WIDTH:'):width=float(line.split(':')[1])
  if line.startswith(';HEIGHT:'):height=float(line.split(':')[1])
  if line.startswith('M83'):relative=True
  if line.startswith('M82'):relative=False
  if line.startswith('G92 E'):ev=float(line.split('E',1)[1].split()[0])
  if not re.match(r'^G[0123] ',line):continue
  vals={k:float(v) for k,v in re.findall(r'([XYZEIJF])([-+]?\d*\.?\d+)',line.split(';')[0])};xx=vals.get('X',x);yy=vals.get('Y',y);zz=vals.get('Z',z);feed=vals.get('F',feed)
  ex=vals.get('E',0)- (ev if not relative and 'E' in vals else 0)
  if 'E' in vals:ev=vals['E']
  if cur and ex>0 and (xx!=x or yy!=y) and kind!='Custom':
   pts=[(x,y),(xx,yy)]
   if line.startswith(('G2 ','G3 ')):
    cx=x+vals.get('I',0);cy=y+vals.get('J',0);r=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sign=1 if line.startswith('G3 ') else -1;span=((b-a)*sign)%(2*math.pi);span=span or 2*math.pi;n=max(8,math.ceil(span*r/.2));pts=[(cx+r*math.cos(a+sign*span*j/n),cy+r*math.sin(a+sign*span*j/n)) for j in range(n+1)]
   length=sum(math.dist(a,b) for a,b in zip(pts,pts[1:]));r=features[cur][kind];r['length_mm']+=length;r['min_speed_mm_s']=min(r['min_speed_mm_s'],feed/60);r['max_speed_mm_s']=max(r['max_speed_mm_s'],feed/60);r['segments']+=1
   if collect_all or kind in ['Support interface','Bridge','Internal Bridge','Bottom surface','Overhang wall'] or abs(zz-.2)<1e-5:paths[cur][round(zz,4)].append({'kind':kind,'points':pts,'width':width,'height':height,'length':length,'speed':feed/60})
  x,y,z=xx,yy,zz
 return paths,features,names

def analyze(code,cfg):
 paths,features,names=parse(code);gap=number(cfg.get('support_top_z_distance'),.2);layer=number(cfg.get('layer_height'),.2);objects=[]
 for name in sorted(names):
  layers=paths[name];interface={z:[p for p in ps if p['kind']=='Support interface'] for z,ps in layers.items()};interface={z:ps for z,ps in interface.items() if ps};trees={z:cKDTree(np.array([pt for p in ps for pt in samples(p['points'])])) for z,ps in interface.items()};surface=[]
  for z,ps in sorted(layers.items()):
   for kind in ['Bottom surface','Bridge','Internal Bridge','Overhang wall']:
    model=[p for p in ps if p['kind']==kind]
    if not model:continue
    h=float(np.median([p['height'] for p in model]));expected=z-h-gap;eligible=[sz for sz in interface if abs(sz-expected)<=.075]
    total=covered=0.;maxunsupported=0.;minspeed=min(p['speed'] for p in model);maxspeed=max(p['speed'] for p in model)
    for p in model:
     points=np.array(samples(p['points']));n=len(points);dist=np.full(n,np.inf)
     for sz in eligible:dist=np.minimum(dist,trees[sz].query(points)[0])
     # 0.25mm sampling resolution, support bead halfwidth and 0.15mm query discretization.
     sw=max([q['width'] for sz in eligible for q in interface[sz]] or [.4]);hit=dist <= (p['width']+sw)/2+.15;covered+=p['length']*float(hit.mean());total+=p['length'];run=0
     for found in hit:
      run=0 if found else run+p['length']/n;maxunsupported=max(maxunsupported,run)
    surface.append({'model_z_mm':z,'kind':kind,'model_layer_height_mm':h,'expected_interface_top_z_mm':round(expected,4),'matching_interface_z_mm':sorted(eligible),'length_mm':total,'interface_supported_length_mm':covered,'interface_coverage_fraction':covered/total if total else None,'max_contiguous_path_without_near_interface_mm':maxunsupported,'min_speed_mm_s':minspeed,'max_speed_mm_s':maxspeed,'on_bed':z<=layer+1e-4})
  fs={k:{kk:(round(v,4) if isinstance(v,float) else v) for kk,v in r.items()} for k,r in features[name].items()}
  objects.append({'native_label':name,'name':name.split('_id_')[0],'features':fs,'surface_layers':surface,'support_interface_layer_count':len(interface),'support_interface_z_mm':sorted(interface),'issues_to_review':(['exterior_bridge_paths_present'] if 'Bridge' in fs else [])+(['overhang_wall_paths_present'] if 'Overhang wall' in fs else [])+(['support_inside_part_may_need_manual_removal_access_check'] if interface else [])})
 return {'object_count':len(objects),'settings':{k:cfg.get(k) for k in FIELDS},'objects':objects,'acceptance_boundary':'Actual native extrusion diagnostics only. Interface coverage is not expected to be 100% for intentional bridges. Mesh hole/seat regions, trapped support, bead intrusion and physical finish require additional evidence. Never pass a job from these metrics alone.'}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--gcode',required=True);ap.add_argument('--project');ap.add_argument('--printer',default='Elegoo',choices=['Elegoo','Bambu']);ap.add_argument('--output',required=True);args=ap.parse_args();code,cfg,filehash,gchash=read_code(args.gcode,args.project,args.printer);result=analyze(code,cfg);result.update(gcode_file=str(Path(args.gcode).resolve()),project=args.project,printer=args.printer,file_sha256=filehash,gcode_sha256=gchash);Path(args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'output':args.output,'object_count':result['object_count']}))
if __name__=='__main__':main()
