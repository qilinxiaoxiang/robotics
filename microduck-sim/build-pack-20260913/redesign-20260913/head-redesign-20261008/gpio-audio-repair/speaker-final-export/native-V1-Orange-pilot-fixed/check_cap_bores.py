from pathlib import Path
import math,re,json,hashlib,os,io,base64
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
from PIL import Image,ImageStat
D=Path(__file__).resolve().parent;R=D.parents[3];H=R/'head-redesign-20261008';P=R/'printing/12-REPAIR-V1-20261008';ori={r['key']:r for r in json.loads((P/'orientation-preparation.json').read_text())['parts']if r['color']=='Orange'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();f=D/'Orange_V1_fixed_GUI.gcode';features=[];sources=[]
def read(p):sources.append(p);return json.loads(p.read_text())
def feature(name,part,origin,axis,lo,hi,r):features.append(dict(name=name,part=part,origin=origin,axis=axis,range=[lo,hi],radius=r,coreSupportLines=set(),potentialSupportLines=set(),minModelInnerRadiusMm=999,coreHitPoints=[]))
for i in (0,1):
 a=read(H/f'gpio-audio-repair/cap-amp16z2/amp-new-post-{i}.json');feature(f'amp-pilot-{i}','head_cap',a['holeBottomMm'],[0,0,1],.15,6.7,1.05)
for i,y in enumerate((7,17)):
 feature(f'speaker-pilot-{i}','head_cap',[-16,y,133.45],[0,0,1],.15,2.99,1.05)
 feature(f'speaker-cradle-{i}','speaker_cradle',[-16,y,128.44],[0,0,1],.01,1.19,1.4)
 feature(f'speaker-keeper-{i}','speaker_keeper',[-16,y,132.45],[0,0,1],.01,.99,1.4)
for p in read(H/'curved-head/mounts-and-paths.json')['posts']:
 # Screw corridor above PCB through post, including nut chamber; exclude roof skin end.
 feature(p['screw'],'head_cap',p['pcbHoleCenterWorldMm'],p['axisWorld'],1.7,1.6+p['postLengthMm']-.3,1.2)
def inv(p,key):
 o=ori[key];T=o['printTransform'];p=[p[0]-o['placementXYMm'][0],p[1]-o['placementXYMm'][1],p[2]];return [sum(T[j][i]*(p[j]-T[j][3])for j in range(3))for i in range(3)]
def cliprad(p,q,f):
 ax=f['axis'];c=f['origin'];u=[p[i]-c[i]for i in range(3)];v=[q[i]-p[i]for i in range(3)];along=sum(u[i]*ax[i]for i in range(3));delta=sum(v[i]*ax[i]for i in range(3));lo,hi=f['range']
 if abs(delta)<1e-12:
  if not lo<=along<=hi:return None
  a=0;b=1
 else:
  ts=[(lo-along)/delta,(hi-along)/delta];a=max(0,min(ts));b=min(1,max(ts))
  if a>b:return None
 w=[u[i]-along*ax[i]for i in range(3)];d=[v[i]-delta*ax[i]for i in range(3)];den=sum(t*t for t in d);t=max(a,min(b,-sum(w[i]*d[i]for i in range(3))/den))if den else a
 return math.sqrt(sum((w[i]+t*d[i])**2 for i in range(3)))
x=y=z=0.;height=.2;width=.42;cur=None;kind='Custom'
for no,l in enumerate(f.open(),1):
 if l.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(.+)_id_',l)[1]
 elif l.startswith('EXCLUDE_OBJECT_END'):cur=None
 elif l.startswith(';TYPE:'):kind=l[6:].strip()
 elif l.startswith(';WIDTH:'):width=float(l[7:])
 elif l.startswith(';HEIGHT:'):height=float(l[8:])
 if not re.match(r'^G[0123] ',l):continue
 vals={k:float(v)for k,v in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',l.split(';')[0])};xx=vals.get('X',x);yy=vals.get('Y',y);zz=vals.get('Z',z);points=[(x,y),(xx,yy)]
 if cur and vals.get('E',0)>0 and kind!='Custom'and(xx!=x or yy!=y):
  if l.startswith(('G2 ','G3 '))and('I'in vals or'J'in vals):
   cx=x+vals.get('I',0);cy=y+vals.get('J',0);rr=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sg=1 if l.startswith('G3')else-1;span=((b-a)*sg)%(2*math.pi)or 2*math.pi;n=max(1,math.ceil(span/max(.001,2*math.acos(max(-1,min(1,1-.01/max(rr,.01)))))));points=[(cx+rr*math.cos(a+sg*span*i/n),cy+rr*math.sin(a+sg*span*i/n))for i in range(n+1)];points[0]=(x,y);points[-1]=(xx,yy)
  w=[inv([p[0],p[1],zz-height/2],cur)for p in points];rad=math.hypot(width/2,height/2)+.012
  for feat in features:
   if feat['part']!=cur:continue
   for p,q in zip(w,w[1:]):
    # Cheap source-world coordinate bounds for far-away segments.
    c=feat['origin'];ax=feat['axis'];lo,hi=feat['range'];a=[c[k]+ax[k]*lo for k in range(3)];b=[c[k]+ax[k]*hi for k in range(3)];bound=feat['radius']+rad
    if any(max(p[k],q[k])<min(a[k],b[k])-bound or min(p[k],q[k])>max(a[k],b[k])+bound for k in range(3)):continue
    d=cliprad(p,q,feat)
    if d is None:continue
    if'support'in kind.lower():
     if d<feat['radius']+rad:feat['potentialSupportLines'].add(no)
     if d<feat['radius']-.3:
      feat['coreSupportLines'].add(no);feat['coreHitPoints'].extend([p,q])
    else:feat['minModelInnerRadiusMm']=min(feat['minModelInnerRadiusMm'],d-rad)
 x,y,z=xx,yy,zz
for r in features:
 pts=r.pop('coreHitPoints');along=[sum((p[i]-r['origin'][i])*r['axis'][i]for i in range(3))for p in pts];r['coreHitAlongAxisMm']=[min(along),max(along)]if along else None;r['coreHitWorldBounds']=[[min(p[i]for p in pts)for i in range(3)],[max(p[i]for p in pts)for i in range(3)]]if pts else None
 for key in ('coreSupportLines','potentialSupportLines'):r[key+'Count']=len(r[key]);r[key]=sorted(r[key])[:12]
code=f.read_text();h=re.search(r'; thumbnail begin (\d+)x(\d+) (\d+)\s*\n(.*?); thumbnail end',code,re.S);assert h;encoded=''.join(l[2:].strip()for l in h[4].splitlines());assert len(encoded)==int(h[3]);png=base64.b64decode(encoded,validate=True);im=Image.open(io.BytesIO(png));im.load();assert im.size==(144,144)and max(ImageStat.Stat(im.convert('RGB')).var)>1
(D/'native-thumbnail.png').write_bytes(png);issues=[r['name']for r in features if r['coreSupportLinesCount']]
report={'gcodeSha256':sha(f),'projectSha256':sha(P/'staging-projects/MicroDuck_Elegoo_Orange_ASSEMBLY_editable.3mf'),'nativeThumbnail':{'size':[144,144],'nonblank':True,'sha256':hashlib.sha256(png).hexdigest()},'features':features,'supportCoreClear':not issues,'modelCoreIssues':[r['name']for r in features if r['minModelInnerRadiusMm']<r['radius']-.3],'supportCoreIssues':issues,'sourceHashes':{str(p):sha(p)for p in sources},'method':'Actual native bead center segments transformed to exact source world; spherical bead-bound radius hypot(width/2,height/2)+.012 for .01 arc sagitta. Definite core hits separated from potential edge contact.','boundary':'No full head assembly/FFC acceptance or physical support removability claim. OpenRB nut chamber is included in bolt corridor but separate side-slot access needs its own proof.'}
(D/'functional-bore-readback.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
