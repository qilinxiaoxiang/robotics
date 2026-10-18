"""Read-only Bambu native archive extrusion-spacing verification.
Usage: python audit_bambu_spacing.py --white PATH --yellow PATH
"""
from pathlib import Path
import argparse,hashlib,itertools,json,math,re,zipfile
import numpy as np
from shapely.geometry import MultiLineString,MultiPoint,Polygon
NUM=re.compile(r'([XYZEIJ])([-+]?\d*\.?\d+)')
HERE=Path(__file__).resolve().parent

def audit_archive(path,expected):
 z=zipfile.ZipFile(path);names=[n for n in z.namelist() if n.endswith('.gcode')];assert len(names)==1,names
 data=z.read(names[0]);settings=json.loads(z.read('Metadata/project_settings.config'))
 polygons=lambda key:Polygon([tuple(float(c) for c in p.split('x')) for p in settings[key]])
 bed=polygons('printable_area');exclusion=polygons('bed_exclude_area')
 cur=None;feature='';x=y=0.;paths={};maxwidth=0.;unowned=[];objects=set();active_model=False
 for line in data.decode().splitlines():
  if line.startswith('M82'):raise RuntimeError('Unexpected absolute extrusion mode')
  if line.startswith('; start printing object, unique label id:'):
   cur=line.rsplit(':',1)[1].strip();objects.add(cur);active_model=True;continue
  if line.startswith('; stop printing object, unique label id:'):cur=None;continue
  if line.startswith('; FEATURE:'):feature=line.split(':',1)[1].strip();continue
  if line.startswith('; LINE_WIDTH:'):maxwidth=max(maxwidth,float(line.split(':',1)[1]));continue
  if not re.match(r'^G[0123] ',line):continue
  cmd=line.split()[0];v={k:float(t) for k,t in NUM.findall(line.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);pts=[(x,y),(xx,yy)]
  if cmd in ['G2','G3'] and ('I' in v or 'J' in v):
   cx=x+v.get('I',0);cy=y+v.get('J',0);rad=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sgn=1 if cmd=='G3' else -1;span=((b-a)*sgn)%(2*math.pi)
   if span<1e-8:span=2*math.pi
   step=2*math.acos(max(-1,min(1,1-.02/max(rad,.02))));n=max(1,math.ceil(span/max(step,.01)));pts=[(cx+rad*math.cos(a+sgn*span*i/n),cy+rad*math.sin(a+sgn*span*i/n)) for i in range(n+1)];pts[0]=(x,y);pts[-1]=(xx,yy)
  if v.get('E',0)>0 and feature!='Custom' and (xx!=x or yy!=y or cmd in ['G2','G3']):
   if cur:paths.setdefault(cur,[]).append(pts)
   elif active_model:unowned.append({'feature':feature,'line':line})
  x,y=xx,yy
 shapes={k:MultiLineString(v) for k,v in paths.items()};hulls={k:MultiPoint(np.concatenate(v)).convex_hull for k,v in paths.items()};radius=max(.3,maxwidth/2)+.02
 pairs=[]
 for a,b in itertools.combinations(shapes,2):
  gap=hulls[a].distance(hulls[b])-2*radius;method='convex_hull_lower_bound'
  if gap<0:gap=shapes[a].distance(shapes[b])-2*radius;method='sampled_path_lower_bound'
  pairs.append({'object_a':a,'object_b':b,'gap_lower_bound_mm':gap,'method':method})
 details=[]
 for name,h in hulls.items():
  envelope=h.buffer(radius);edge=bed.boundary.distance(envelope) if bed.covers(envelope) else -envelope.difference(bed).area
  egap=h.distance(exclusion)-radius
  if egap<0:egap=shapes[name].distance(exclusion)-radius
  details.append({'object_label':name,'extrusion_bounds_mm':list(envelope.bounds),'bed_margin_mm':edge,'exclusion_clearance_lower_bound_mm':egap})
 passed=len(objects)==expected and len(shapes)==expected and not unowned and min(p['gap_lower_bound_mm'] for p in pairs)>=0 and all(d['bed_margin_mm']>=0 and d['exclusion_clearance_lower_bound_mm']>=0 for d in details) and settings.get('print_sequence')=='by layer'
 result={'archive_path':str(path.resolve()),'archive_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'gcode_member':names[0],'gcode_sha256':hashlib.sha256(data).hexdigest(),'object_count':len(objects),'extruding_object_count':len(shapes),'unowned_noncustom_extrusion_count':len(unowned),'unowned_examples':unowned[:8],'print_sequence':settings.get('print_sequence'),'printer_settings_id':settings.get('printer_settings_id'),'bed_type':settings.get('curr_bed_type'),'bed_polygon_mm':list(bed.exterior.coords),'exclusion_polygon_mm':list(exclusion.exterior.coords),'maximum_declared_width_mm':maxwidth,'conservative_bead_radius_including_arc_error_mm':radius,'minimum_interobject_gap_lower_bound_mm':min(p['gap_lower_bound_mm'] for p in pairs),'minimum_bed_margin_mm':min(d['bed_margin_mm'] for d in details),'minimum_exclusion_clearance_lower_bound_mm':min(d['exclusion_clearance_lower_bound_mm'] for d in details),'pairs':pairs,'objects':details,'passed':passed}
 return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--white',required=True,type=Path);ap.add_argument('--yellow',required=True,type=Path);args=ap.parse_args()
 report={'schema_version':1,'acceptance_surface':'native_bambu_archives','method':'All model/support/brim positive XY extrusion paths across all layers. Arc chord error <=0.02 mm. Extrusion radius uses max(0.3 mm, largest declared width/2)+0.02 mm. Conservative convex hull separation; exact sampled paths if hulls cannot prove separation. Startup/custom machine purge excluded. Native bed and exclusion polygons read from each archive.','plates':{}}
 for color,path,count in [('WHITE',args.white,3),('yellow',args.yellow,4)]:
  print('Auditing',color,flush=True);report['plates'][color]=audit_archive(path,count)
 report['passed']=all(p['passed'] for p in report['plates'].values());(HERE/'spacing-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
