"""Read-only local native extrusion review; no CAD or slicing."""
from pathlib import Path
import json,hashlib,zipfile,xml.etree.ElementTree as ET,math,re,sys
D=Path(__file__).resolve().parent;machine=sys.argv[1];color=sys.argv[2];prep=D/'run/preparation.json';receipt=json.loads(prep.read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();row=next(r for r in receipt['rows']if r['color']==color and r['machine']==machine);project=Path(row['project']['path']);archive=D/'run/native'/f'{color}_{machine}'/'sliced.3mf';probes=json.loads((D/'black-imu-functional-probes.json').read_text());features=[dict(f,modelSegments=[],supportSegments=[])for f in probes['features']if f['partKey']==('imu_cover'if color=='Black'else'imu_clamp')];part=next(p for p in receipt['parts']if p['key']==features[0]['partKey']);place=next(p for p in row['placements']if p['key']==part['key']);T=part['sourceToPrint'];shift=[T[i][3]+place['translation'][i]+(part['dropToBedMm']if i==2 else 0)for i in range(3)]
def world(p):return [sum(T[j][i]*(p[j]-shift[j])for j in range(3))for i in range(3)]
with zipfile.ZipFile(project)as z:
 cfg=json.loads(z.read('Metadata/project_settings.config'));settings=ET.fromstring(z.read('Metadata/model_settings.config'))
names={o.get('id'):o.find("metadata[@key='name']").get('value')for o in settings.findall('object')};labels={x.find("metadata[@key='identify_id']").get('value'):names[x.find("metadata[@key='object_id']").get('value')]for x in settings.findall('plate/model_instance')};off=list(map(float,cfg.get('extruder_offset',['0x0'])[0].split('x')))if machine=='Bambu'else[0,0]
def hit(a,b,f,pad):
 if 'boundsWorldMm'in f:
  lo,hi=f['boundsWorldMm'];lo=[v+.15 for v in lo];hi=[v-.15 for v in hi];t0=0;t1=1
  for i in range(3):
   delta=b[i]-a[i]
   if abs(delta)<1e-10:
    if a[i]<lo[i]-pad or a[i]>hi[i]+pad:return False
   else:
    ss=sorted([(lo[i]-pad-a[i])/delta,(hi[i]+pad-a[i])/delta]);t0=max(t0,ss[0]);t1=min(t1,ss[1])
  return t0<=t1
 p,q=f['startWorldMm'],f['endWorldMm'];xmin,xmax=sorted([p[0],q[0]])
 if max(a[0],b[0])<xmin or min(a[0],b[0])>xmax:return False
 rad=f.get('radiusMm',f.get('screenRadiusMm',f.get('innerRadiusMm',f.get('pinRadiusMm',0))));rad=max(.15,rad-.2)
 dy=b[1]-a[1];dz=b[2]-a[2];t=max(0,min(1,((p[1]-a[1])*dy+(p[2]-a[2])*dz)/(dy*dy+dz*dz or 1)))
 return math.hypot(a[1]+t*dy-p[1],a[2]+t*dz-p[2])<rad+pad
xyz=[0.,0.,0.];kind='Custom';width=.4;cur=None;relative=True;e=0.;height=float(cfg['initial_layer_print_height']);seen=0
with zipfile.ZipFile(archive)as z:
 member=next(n for n in z.namelist()if n.endswith('.gcode'));gsha=hashlib.sha256(z.read(member)).hexdigest()
 with z.open(member)as stream:
  for no,raw in enumerate(stream,1):
   l=raw.decode().strip()
   if l.startswith('; start printing object, unique label id:'):cur=labels.get(l.rsplit(':',1)[1].strip())
   elif l.startswith('; stop printing object, unique label id:'):cur=None
   elif l.startswith('; OBJECT_ID:'):cur=labels.get(l.split(':',1)[1].strip())
   elif l.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(\S+)',l)[1].split('_id_')[0]
   elif l.startswith('EXCLUDE_OBJECT_END'):cur=None
   elif l.startswith(('; FEATURE:',';TYPE:')):kind=l.split(':',1)[1].strip()
   elif l.startswith(('; LINE_WIDTH:',';WIDTH:')):width=float(l.split(':',1)[1])
   elif l.startswith(('; LAYER_HEIGHT:',';HEIGHT:')):height=float(l.split(':',1)[1])
   if l.startswith('M82'):relative=False
   if l.startswith('M83'):relative=True
   if l.startswith('G92 '):
    mm=re.search(r'E([-+\d.]+)',l)
    if mm:e=float(mm[1])
   if not re.match(r'^G[0123] ',l):continue
   v={k:float(t)for k,t in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',l.split(';')[0])};end=[v.get(k,xyz[i])for i,k in enumerate('XYZ')];de=v.get('E',0)if relative else v.get('E',e)-e
   if 'E'in v:e=e+v['E']if relative else v['E']
   if ((cur and cur.startswith(part['key']))or 'support'in kind.lower())and de>0 and kind!='Custom'and end[:2]!=xyz[:2]:
    seen+=1;pts=[xyz[:2],end[:2]]
    if l.startswith(('G2 ','G3 ')):
     cx=xyz[0]+v.get('I',0);cy=xyz[1]+v.get('J',0);rr=math.hypot(xyz[0]-cx,xyz[1]-cy);aa=math.atan2(xyz[1]-cy,xyz[0]-cx);bb=math.atan2(end[1]-cy,end[0]-cx);sg=1 if l.startswith('G3')else-1;span=((bb-aa)*sg)%(2*math.pi)or 2*math.pi;n=max(2,math.ceil(span*rr/.08));pts=[(cx+rr*math.cos(aa+sg*span*i/n),cy+rr*math.sin(aa+sg*span*i/n))for i in range(n+1)]
    ws=[world([p[0]+off[0],p[1]+off[1],end[2]-height/2])for p in pts];supp='support'in kind.lower()
    for f in features:
     if any(hit(a,b,f,width/2+.002)for a,b in zip(ws,ws[1:])):
      arr=f['supportSegments'if supp else'modelSegments']
      if len(arr)<30:arr.append({'line':no,'layerZMm':end[2],'feature':kind,'worldStart':ws[0],'worldEnd':ws[-1]})
   xyz=end
assert seen>0,'No target extrusions; model label mapping failed'
out={'status':'NATIVE_FEATURE_SCREEN_REQUIRES_PRACTICAL_REVIEW','machine':machine,'color':color,'partKey':part['key'],'archive':str(archive),'archiveSha256':sha(archive),'gcodeSha256':gsha,'preparationSha256':sha(prep),'projectSha256':sha(project),'scannedTargetOrAllSupportExtrusions':seen,'sourceScriptSha256':sha(Path(__file__)),'features':features,'scope':'Conservative toolpath overlap screen; inspect recorded feature access before declaring trapped support. No automatic rejection merely because accessible support exists.'};p=D/f'imu-functional-{color}-{machine}.json';p.write_text(json.dumps(out,indent=2)+'\n');print([(f['key'],len(f['modelSegments']),len(f['supportSegments']))for f in features])
