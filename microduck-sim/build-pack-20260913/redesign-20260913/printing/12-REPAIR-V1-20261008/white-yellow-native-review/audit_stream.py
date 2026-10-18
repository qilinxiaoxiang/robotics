"""Bounded native Bambu review; stream arcs and retain only first two layers."""
from pathlib import Path
import json,re,math,hashlib,zipfile,io,os,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from shapely.geometry import LineString
from shapely.ops import unary_union
D=Path(__file__).resolve().parent;P=D.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
col=sys.argv[1];src=Path(sys.argv[2]) if len(sys.argv)>2 else P/f'native-{col}/{col}_V1.gcode.3mf';rows={};first={};x=y=z=0.;layerz=0.;kind='Custom';width=.4;h=.2;started=False;cur=None;unowned=0;features=set();gsha=hashlib.sha256()
with zipfile.ZipFile(src) as ar:
 cfg=json.loads(ar.read('Metadata/project_settings.config'));initial=float(cfg['initial_layer_print_height']);second=round(initial+float(cfg['layer_height']),5);off=[float(v) for v in cfg['extruder_offset'][0].split('x')];assert len(cfg['extruder_offset'])==1
 members=[n for n in ar.namelist() if n.endswith('.gcode')];assert len(members)==1
 for raw in ar.open(members[0]):
  gsha.update(raw);l=raw.decode();
  if l.startswith('; Z_HEIGHT:'):layerz=float(l.split(':')[1]);started=True
  elif l.startswith('; LAYER_HEIGHT:'):h=float(l.split(':')[1])
  elif l.startswith('; OBJECT_ID:'):cur=l.split(':')[1].strip()
  elif l.startswith('; FEATURE:'):kind=l.split(':')[1].strip()
  elif l.startswith('; LINE_WIDTH:'):width=float(l.split(':')[1])
  if l.startswith('M82'):raise ValueError('absoluteE unsupported')
  if not re.match(r'^G[0123] ',l):continue
  v={k:float(a) for k,a in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',l.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);zz=v.get('Z',z);pts=[(x,y),(xx,yy)]
  if started and v.get('E',0)>0 and kind!='Custom' and (xx!=x or yy!=y or l.startswith(('G2 ','G3 '))):
   if not cur:unowned+=1
   if l.startswith(('G2 ','G3 ')) and ('I'in v or'J'in v):
    cx=x+v.get('I',0);cy=y+v.get('J',0);rr=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sg=1 if l.startswith('G3')else-1;span=((b-a)*sg)%(2*math.pi)or 2*math.pi;n=max(1,math.ceil(span/max(.001,2*math.acos(max(-1,min(1,1-.002/max(rr,.002)))))));pts=[(cx+rr*math.cos(a+sg*span*i/n),cy+rr*math.sin(a+sg*span*i/n)) for i in range(n+1)];pts[0]=(x,y);pts[-1]=(xx,yy)
   pts=[(a+off[0],b+off[1]) for a,b in pts];group='support' if 'support'in kind.lower() else ('brim' if kind.lower()in['brim','skirt'] else 'model');r=rows.setdefault(group,{'segments':0,'bounds':[1e9,1e9,-1e9,-1e9],'layers':set()});r['segments']+=1;r['layers'].add(layerz);bb=r['bounds'];rad=width/2+.002;bb[:]=[min(bb[0],min(a for a,b in pts)-rad),min(bb[1],min(b for a,b in pts)-rad),max(bb[2],max(a for a,b in pts)+rad),max(bb[3],max(b for a,b in pts)+rad)];features.add(kind)
   if layerz<=second+.00001:first.setdefault((layerz,group),[]).append(LineString(pts).buffer(width/2,resolution=8))
  x,y,z=xx,yy,zz
for r in rows.values():r['layers']=sorted(r['layers'])
union={k:unary_union(v) for k,v in first.items()};contacts=[]
for layer in [initial,second]:
 for group in ['model','support','brim']:
  s=union.get((layer,group));contacts.append({'zMm':layer,'kind':group,'areaMm2':0 if s is None else s.area,'islands':0 if s is None else (len(s.geoms) if hasattr(s,'geoms') else 1),'boundsMm':None if s is None else list(s.bounds)})
report={'archive':str(src),'archiveSha256':sha(src),'gcodeMember':members[0],'gcodeSha256':gsha.hexdigest(),'physicalNozzleOffsetAddedMm':off,'objects':1,'groups':rows,'firstTwoLayers':contacts,'unownedExtrusions':unowned,'features':sorted(features),'method':'Stream G1/G2/G3 relativeE; circular arcs chord error<=.002mm; bead areas buffered by actual width/2. First-layer model/support/brim union kept separate. Actual material XY=commandXY+configuredextruder_offset.','sourceHashes':{str(Path(__file__)):sha(Path(__file__))}}
(D/f'{col}-stream.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'color':col,'firstTwoLayers':contacts,'groups':{k:{q:v for q,v in row.items() if q!='layers'} for k,row in rows.items()},'unowned':unowned}))
