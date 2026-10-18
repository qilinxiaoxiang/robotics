from pathlib import Path
import re,math,json,hashlib,itertools,zipfile,sys
import numpy as np
from shapely.geometry import MultiLineString,MultiPoint,Polygon,box
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/PRINTING/04-FOUR-COLOR-20260929')
NUM=re.compile(r'([XYZEIJ])([-+]?\d*\.?\d+)')
def parse(p):
 objects={};cur=None;kind='';x=y=0.;paths={};unowned=0;relative=True;maxwidth=0
 for line in p.open():
  if line.startswith('M82'):raise RuntimeError('Unsupportedabsoluteextrusion')
  if line.startswith(';WIDTH:'):maxwidth=max(maxwidth,float(line.split(':')[1]))
  if line.startswith('EXCLUDE_OBJECT_DEFINE'):
   name=re.search(r'NAME=(\S+)',line)[1];objects[name]=Polygon(json.loads(line.split('POLYGON=')[1]));continue
  if line.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(\S+)',line)[1];continue
  if line.startswith('EXCLUDE_OBJECT_END'):cur=None;continue
  if line.startswith(';TYPE:'):kind=line[6:].strip();continue
  if not re.match(r'^G[0123] ',line):continue
  cmd=line.split()[0];v={k:float(t) for k,t in NUM.findall(line.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);pts=[(x,y),(xx,yy)]
  if cmd in ['G2','G3'] and ('I' in v or 'J' in v):
   cx=x+v.get('I',0);cy=y+v.get('J',0);rad=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sgn=1 if cmd=='G3' else -1;span=((b-a)*sgn)%(2*math.pi)
   if span<1e-8:span=2*math.pi
   step=2*math.acos(max(-1,min(1,1-.02/max(rad,.02))));n=max(1,math.ceil(span/max(step,.01)));pts=[(cx+rad*math.cos(a+sgn*span*i/n),cy+rad*math.sin(a+sgn*span*i/n)) for i in range(n+1)];pts[0]=(x,y);pts[-1]=(xx,yy)
  if v.get('E',0)>0 and kind!='Custom' and (xx!=x or yy!=y or cmd in ['G2','G3']):
   if cur:paths.setdefault(cur,[]).append(pts)
   else:unowned+=1
  x,y=xx,yy
 shapes={k:MultiLineString(v) for k,v in paths.items()};hulls={k:MultiPoint(np.concatenate(v)).convex_hull for k,v in paths.items()};rad=max(.3,maxwidth/2)+.02
 names=list(shapes);pairs=[]
 for a,b in itertools.combinations(names,2):
  lower=hulls[a].distance(hulls[b])-2*rad
  if lower<0:dist=shapes[a].distance(shapes[b])-2*rad;method='actualsampledextrusionpolyline'
  else:dist=lower;method='convexhullconservativelowerbound'
  pairs.append({'a':a,'b':b,'gap_lower_bound_mm':dist,'method':method})
 bounds=[min(h.bounds[0] for h in hulls.values())-rad,min(h.bounds[1] for h in hulls.values())-rad,max(h.bounds[2] for h in hulls.values())+rad,max(h.bounds[3] for h in hulls.values())+rad]
 gap=min(pairs,key=lambda v:v['gap_lower_bound_mm']);edge=min(bounds[0],bounds[1],256-bounds[2],256-bounds[3])
 exclusion=box(246,0,256,20);exclusion_gap=min(h.distance(exclusion)-rad for h in hulls.values())
 out={'bed_exclusion_area_mm':[246,0,256,20],'minimum_exclusion_clearance_mm':exclusion_gap,'gcode_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'object_count':len(objects),'extruding_objects':len(shapes),'unowned_positive_noncustom_moves':unowned,'max_gcode_width_mm':maxwidth,'bead_radius_plus_arc_error_mm':rad,'actual_extrusion_bounds_conservative_mm':bounds,'minimum_bed_edge_margin_mm':edge,'minimum_interobject_extrusion_gap_lower_bound_mm':gap['gap_lower_bound_mm'],'closest_pair':gap,'model_hull_min_gap_mm':min(a.distance(b) for a,b in itertools.combinations(objects.values(),2)),'passed_nonoverlap_and_inside_bed':gap['gap_lower_bound_mm']>=0 and edge>=0 and exclusion_gap>=0 and unowned==0,'pairs':pairs}
 return out,hulls,objects,rad
if __name__=='__main__':
 report={'schema_version':1,'acceptance_surface':'native_gui_usb' if '--gui' in sys.argv else 'native_cli_candidate','method':'All positive XY extrusions except Custom. G2/G3 arcs subdivided with at most 0.02 mm chord error; bead radius = max(0.3 mm, maximum declared width / 2) + 0.02 mm. Convex hull distances give conservative lower bounds; sampled path distance is used when hulls cannot prove separation. XY projections include every layer, support and brim. Requires by-layer printing.','plates':[]};fig,axs=plt.subplots(1,4,figsize=(16,4.5));colors=['orange','yellow','WHITE','black'];palette=['#dc7b2a','#dcc832','#adb4bd','#515866']
 for color,ax,paint in zip(colors,axs,palette):
  print('Parsing',color,flush=True);d,hulls,objects,rad=parse((R/'USB-PRINT'/f'MicroDuck_{color}.gcode') if '--gui' in sys.argv else (R/color/'plate_1.gcode'));d['color']=color;d['source']='native_gui_usb' if '--gui' in sys.argv else 'native_cli_candidate';d['gcode_path']=str((R/'USB-PRINT'/f'MicroDuck_{color}.gcode') if '--gui' in sys.argv else (R/color/'plate_1.gcode'))
  archive=R/color/(f'MicroDuck-{color}-GUI.gcode.3mf' if '--gui' in sys.argv else f'MicroDuck-{color}-sliced.3mf')
  if archive.exists():
   d['native_archive_path']=str(archive);d['native_archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest();z=zipfile.ZipFile(archive);settings=json.loads(z.read('Metadata/project_settings.config'));d['print_sequence']=settings.get('print_sequence');d['gcode_matches_native_archive']=any(hashlib.sha256(z.read(n)).hexdigest()==d['gcode_sha256'] for n in z.namelist() if n.endswith('.gcode'));d['passed_nonoverlap_and_inside_bed'] &= d['print_sequence']=='by layer' and d['gcode_matches_native_archive']
  else:d['passed_nonoverlap_and_inside_bed']=False
  report['plates'].append(d)
  for h in hulls.values():
   a=h.buffer(rad);x,y=a.exterior.xy;ax.fill(x,y,color=paint,alpha=.65,linewidth=.4,edgecolor='#28343a')
  ax.set(xlim=(0,256),ylim=(0,256),aspect='equal',title=f"{color}: {d['object_count']} parts\ngap >= {d['minimum_interobject_extrusion_gap_lower_bound_mm']:.2f} mm",xlabel='mm');ax.grid(alpha=.2)
 report['passed']=all(p['passed_nonoverlap_and_inside_bed'] for p in report['plates']) and [p['object_count'] for p in report['plates']]==[4,4,3,50]
 (R/('spacing-verification.json' if '--gui' in sys.argv else 'spacing-cli-candidate.json')).write_text(json.dumps(report,indent=2)+'\n');fig.suptitle('Conservative native extrusion outlines (all layers, supports included)');fig.tight_layout();fig.savefig(R/'spacing-four-colors.png',dpi=170)
 print(json.dumps({**report,'plates':[{k:v for k,v in p.items() if k!='pairs'} for p in report['plates']]},indent=2))
