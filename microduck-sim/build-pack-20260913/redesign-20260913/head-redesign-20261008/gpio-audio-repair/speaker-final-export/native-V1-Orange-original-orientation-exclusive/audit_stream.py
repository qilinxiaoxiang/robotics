from pathlib import Path
import json,re,math,hashlib,zipfile,itertools,os,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from shapely.geometry import box
D=Path(__file__).resolve().parent;R=D.parents[3];src=D/'Orange_V1p1_native.3mf'
with zipfile.ZipFile(src)as z:cfg=json.loads(z.read('Metadata/project_settings.config'))
rows={};x=y=z=0.;kind='Custom';cur=None;width=.4;unowned=0;orphanBrim=0;firstlines=[];firstDone=False
p=D/(sys.argv[1] if len(sys.argv)>1 else 'plate_1.gcode')
for l in p.open():
 if not firstDone:firstlines.append(l)
 if l.startswith(';Z:')and float(l[3:])>.2:firstDone=True
 if l.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(.+)_id_',l)[1]
 elif l.startswith('EXCLUDE_OBJECT_END'):cur=None
 elif l.startswith(';TYPE:'):kind=l[6:].strip()
 elif l.startswith(';WIDTH:'):width=float(l[7:])
 if not re.match(r'^G[0123] ',l):continue
 v={k:float(a)for k,a in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',l.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);zz=v.get('Z',z);points=[(x,y),(xx,yy)]
 if l.startswith(('G2 ','G3 '))and('I'in v or'J'in v):
  cx=x+v.get('I',0);cy=y+v.get('J',0);rr=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sg=1 if l.startswith('G3')else-1;span=((b-a)*sg)%(2*math.pi)or 2*math.pi
  for c in [0,math.pi/2,math.pi,3*math.pi/2]:
   if((c-a)*sg)%(2*math.pi)<=span+1e-8:points.append((cx+rr*math.cos(c),cy+rr*math.sin(c)))
 if v.get('E',0)>0 and kind!='Custom'and(xx!=x or yy!=y):
  owner=cur
  if not owner and kind=='Brim':
   assert abs(zz-.2)<1e-6;owner='head_cap';orphanBrim+=1
  if owner:
   r=rows.setdefault(owner,{'bounds':[1e9,1e9,-1e9,-1e9],'segments':0,'modelZ':set(),'supportZ':set()});rad=width/2+.002;b=r['bounds'];b[0]=min(b[0],min(a[0]for a in points)-rad);b[1]=min(b[1],min(a[1]for a in points)-rad);b[2]=max(b[2],max(a[0]for a in points)+rad);b[3]=max(b[3],max(a[1]for a in points)+rad);r['segments']+=1;r['supportZ'if'support'in kind.lower()else'modelZ'].add(round(zz,5))
  else:unowned+=1
 x,y,z=xx,yy,zz
pairs=[{'a':a,'b':b,'boundingBoxGapLowerBoundMm':box(*rows[a]['bounds']).distance(box(*rows[b]['bounds']))}for a,b in itertools.combinations(rows,2)]
sys.path.insert(0,str(R/'printing/09-REPRINT-READY-20260930'));from native_tools import first_layer_summary
first=first_layer_summary(''.join(firstlines));print('AUDIT',len(rows),len(first),unowned,'firstkeys',[v['name']for v in first],flush=True);assert len(rows)==3 and len(first)==3 and unowned==0
margin=min(min(r['bounds'][0],r['bounds'][1],256-r['bounds'][2],256-r['bounds'][3])for r in rows.values());assert margin>0 and all(p['boundingBoxGapLowerBoundMm']>4 for p in pairs)
for r in rows.values():r['modelLayers']=len(r.pop('modelZ'));r['supportPlanes']=len(r.pop('supportZ'))
report={'passed':True,'archiveSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'gcodeSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'objectCount':3,'objects':rows,'pairs':pairs,'bedMarginMm':margin,'firstLayer':first,'unownedExtrusions':unowned,'orphanBrimSegmentsAssignedToHeadCap':orphanBrim,'brimAssignment':'Native unowned TYPE Brim on Z0.2 only, included in head_cap full bounds and gap checks against both speaker parts, never discarded.','method':'Streaming actual arc extrema plus native width/2 and .002mm allowance; conservative per-object XY boxes contain all model/support/brim paths. Retain only initial-layer paths for area union.','scope':'Full extrusion extent/count/spacing and first layer; head-cap functional bores require separate check.'}
(D/('native-audit-GUI-stream.json' if len(sys.argv)>1 else 'native-audit-stream.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
