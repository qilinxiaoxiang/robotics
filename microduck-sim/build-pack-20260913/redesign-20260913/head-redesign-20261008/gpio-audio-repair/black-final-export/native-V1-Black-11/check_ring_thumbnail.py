from pathlib import Path
import math,json,re,base64,io,hashlib,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from PIL import Image,ImageStat
from shapely.geometry import LineString,Point
D=Path(__file__).resolve().parent;f=D/'Black_V1_11_GUI.gcode';code=f.read_text();x=y=z=0.;width=.42;h=.2;cur=None;kind='Custom';rows={};center=Point(92,188.65)
for l in code.splitlines():
 if l.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(.+)_id_',l)[1]
 elif l.startswith('EXCLUDE_OBJECT_END'):cur=None
 elif l.startswith(';TYPE:'):kind=l[6:]
 elif l.startswith(';WIDTH:'):width=float(l[7:])
 elif l.startswith(';HEIGHT:'):h=float(l[8:])
 if not re.match(r'^G[0123] ',l):continue
 v={k:float(a)for k,a in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',l.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);zz=v.get('Z',z)
 if cur=='mouth_sliding_ring' and v.get('E',0)>0 and (xx!=x or yy!=y):
  pts=[(x,y),(xx,yy)]
  if l.startswith(('G2 ','G3 '))and('I'in v or'J'in v):
   cx=x+v.get('I',0);cy=y+v.get('J',0);rr=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sg=1 if l.startswith('G3')else-1;span=((b-a)*sg)%(2*math.pi)or 2*math.pi;n=max(1,math.ceil(span/max(.001,2*math.acos(max(-1,min(1,1-.001/max(rr,.001)))))));pts=[(cx+rr*math.cos(a+sg*span*i/n),cy+rr*math.sin(a+sg*span*i/n))for i in range(n+1)]
  row=rows.setdefault(round(zz,5),{'minOpenRadius':999.,'maxOuterRadius':0.,'heightMm':h,'supportSegments':0})
  row['minOpenRadius']=min(row['minOpenRadius'],LineString(pts).distance(center)-width/2-.002);row['maxOuterRadius']=max(row['maxOuterRadius'],max(math.hypot(p[0]-92,p[1]-188.65)for p in pts)+width/2+.002)
  row['supportSegments']+='support'in kind.lower()
 x,y,z=xx,yy,zz
assert len(rows)==23 and all(r['supportSegments']==0 for r in rows.values())
flange=[z for z,r in rows.items()if r['maxOuterRadius']>7.8];assert flange==[.2,.3],flange
assert all(r['maxOuterRadius']<7.4 for z,r in rows.items()if z>.3)
hh=re.search(r'; thumbnail begin (\d+)x(\d+) (\d+)\s*\n(.*?); thumbnail end',code,re.S);encoded=''.join(l[2:].strip()for l in hh[4].splitlines());assert len(encoded)==int(hh[3]);png=base64.b64decode(encoded,validate=True);im=Image.open(io.BytesIO(png));im.load();assert im.size==(144,144)and max(ImageStat.Stat(im.convert('RGB')).var)>1;(D/'native-thumbnail.png').write_bytes(png)
r={'passed':True,'gcodeSha256':hashlib.sha256(f.read_bytes()).hexdigest(),'thumbnailSha256':hashlib.sha256(png).hexdigest(),'thumbnailSize':[144,144],'ringModelLayerCount':len(rows),'flangeExtrusionTopZMm':flange,'flangeEffectiveThicknessMm':.3,'ringTopZMm':max(rows),'minimumOpenDiameterBoundMm':2*min(r['minOpenRadius']for r in rows.values()),'layers':rows,'method':'Native exact arc subdivision with .001 sagitta + .002mm allowance; bead width used for actual radial clearance. Wide rear flange only two layers .2+.1; following .1mm layers narrower.'};(D/'ring-thumbnail-readback.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
