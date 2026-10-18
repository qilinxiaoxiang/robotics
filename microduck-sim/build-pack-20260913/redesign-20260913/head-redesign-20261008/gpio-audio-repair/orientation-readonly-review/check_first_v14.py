from pathlib import Path
import os,json,sys,re,math,zipfile,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from shapely.geometry import LineString
from shapely.ops import unary_union
D=Path(__file__).resolve().parent;H=D.parents[1];R=H.parent;P=R/'printing/12-REPAIR-V1-20261008';base=P/'dual-printer';color=sys.argv[1];printer=sys.argv[2];N=base/'native'/(color+'_'+printer);g=N/'plate_1.gcode';archive=N/'sliced.3mf';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
import xml.etree.ElementTree as ET
with zipfile.ZipFile(archive)as z:cfg=json.loads(z.read('Metadata/project_settings.config'));st=ET.fromstring(z.read('Metadata/model_settings.config'))
names={o.get('id'):o.find("metadata[@key='name']").get('value')for o in st.findall('object')};labels={i.find("metadata[@key='identify_id']").get('value'):names[i.find("metadata[@key='object_id']").get('value')]for i in st.findall('plate/model_instance')}
off=list(map(float,cfg['extruder_offset'][0].split('x')));first=float(cfg['initial_layer_print_height']);features=[]
x=y=z=0;layer=0;height=.2;width=.4;kind='Custom';cur=None;polys={};supportlayers=set();rows=[]
for no,l in enumerate(g.open(),1):
 if l.startswith('; Z_HEIGHT:'):layer=float(l.split(':')[1])
 elif l.startswith(';Z:'):layer=float(l.split(':')[1])
 elif l.startswith('; LAYER_HEIGHT:'):height=float(l.split(':')[1])
 elif l.startswith(';HEIGHT:'):height=float(l.split(':')[1])
 elif l.startswith('; LINE_WIDTH:'):width=float(l.split(':')[1])
 elif l.startswith(';WIDTH:'):width=float(l.split(':')[1])
 elif l.startswith('; FEATURE:'):kind=l.split(':',1)[1].strip()
 elif l.startswith(';TYPE:'):kind=l.split(':',1)[1].strip()
 elif l.startswith('; OBJECT_ID:'):cur=labels.get(l.split(':')[1].strip())
 elif l.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(.+)_id_',l)[1]
 elif l.startswith('EXCLUDE_OBJECT_END'):cur=None
 if layer>first+1e-6:break
 if not re.match(r'^G[0123] ',l):continue
 v={k:float(a)for k,a in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',l.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);zz=v.get('Z',z)
 if v.get('E',0)>0 and kind!='Custom'and kind.lower()not in ['brim','skirt']and layer>0 and(xx!=x or yy!=y or l.startswith(('G2 ','G3 '))):
  pts=[(x+off[0],y+off[1]),(xx+off[0],yy+off[1])]
  if l.startswith(('G2 ','G3 '))and('I'in v or'J'in v):
   cx=x+v.get('I',0);cy=y+v.get('J',0);rr=math.hypot(x-cx,y-cy);aa=math.atan2(y-cy,x-cx);bb=math.atan2(yy-cy,xx-cx);sg=1 if l.startswith('G3')else -1;span=((bb-aa)*sg)%(2*math.pi)or 2*math.pi;n=max(1,math.ceil(span/max(.001,2*math.acos(max(-1,min(1,1-.002/max(rr,.002)))))));pts=[(cx+rr*math.cos(aa+sg*span*i/n)+off[0],cy+rr*math.sin(aa+sg*span*i/n)+off[1])for i in range(n+1)]
  supp='support'in kind.lower()
  if cur and abs(layer-first)<1e-6:polys.setdefault((cur,'support'if supp else'model'),[]).append(LineString(pts).buffer(width/2,resolution=8))
  if cur=='camera_retainer'and supp:supportlayers.add(layer)
  if layer<=4.05:
   for f in features:
    if layer<f['zRange'][0]-1e-6 or layer-height>f['zRange'][1]+1e-6:continue
    cx,cy=f['xy'];r=f['radius']+width+1
    for a,b in zip(pts,pts[1:]):
     if max(a[0],b[0])<cx-r or min(a[0],b[0])>cx+r or max(a[1],b[1])<cy-r or min(a[1],b[1])>cy+r:continue
     ux=b[0]-a[0];uy=b[1]-a[1];t=max(0,min(1,((cx-a[0])*ux+(cy-a[1])*uy)/(ux*ux+uy*uy or 1)));gap=math.hypot(a[0]+t*ux-cx,a[1]+t*uy-cy)-width/2-.002
     if supp:
      if gap<f['radius']-.05:f['supportHits'].append(no)
     else:f['modelMinRadius']=min(f['modelMinRadius'],gap)
 x,y,z=xx,yy,zz
for f in features:f['supportHits']=sorted(set(f['supportHits']));f['nativeOpenDiameterLowerBoundMm']=2*f.pop('modelMinRadius')
contacts=[]
for (part,kind),pp in polys.items():u=unary_union(pp);contacts.append({'part':part,'kind':kind,'areaMm2':u.area,'islands':len(u.geoms)if hasattr(u,'geoms')else 1})
r={'printer':printer,'sourceGcode':str(g),'sourceSha256':sha(g),'archiveSha256':sha(archive),'physicalNozzleOffsetAddedMm':off,'firstLayerMm':first,'firstLayer':contacts,'cameraSupportLayerCount':len(supportlayers),'features':features,'functionalHolesChecked':False,'sourceScriptSha256':sha(Path(__file__)),'boundary':'Actual first-layer bead union only. Model excludes brim/skirt/support; .002mm arc sagitta. Functional holes require separate report.'};(D/(color+'-V1.4-'+printer+'-first-layer.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
