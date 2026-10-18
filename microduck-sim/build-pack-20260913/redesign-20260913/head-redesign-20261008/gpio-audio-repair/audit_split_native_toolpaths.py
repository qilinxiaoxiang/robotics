from pathlib import Path
import math,json,zipfile,re,hashlib,xml.etree.ElementTree as E
D=Path(__file__).resolve().parent;R=D.parent.parent;P=R/'printing/11-ASSEMBLY-REPAIR-20261008';ori=json.loads((P/'orientation-preparation.json').read_text());num=re.compile(r'([XYZEIJ])([-+]?\d*\.?\d+)');rows=[];allsegs={}
def inv(p,T):return [sum(T[j][i]*(p[j]-T[j][3]) for j in range(3)) for i in range(3)]
def clip(p,q,axis,lo,hi):
 d=q[axis]-p[axis]
 if abs(d)<1e-12:return (p,q) if lo<=p[axis]<=hi else None
 aa=(lo-p[axis])/d;bb=(hi-p[axis])/d;u=max(0,min(aa,bb));v=min(1,max(aa,bb))
 return ([p[k]+u*(q[k]-p[k]) for k in range(3)],[p[k]+v*(q[k]-p[k]) for k in range(3)]) if u<=v else None
def rad(p,q,c):
 d=[p[k]-c[k] for k in [0,2]];v=[q[k]-p[k] for k in [0,2]];den=sum(x*x for x in v);t=max(0,min(1,-sum(x*y for x,y in zip(d,v))/den)) if den else 0
 return math.hypot(*(x+t*y for x,y in zip(d,v)))
for color in ['yellow','black']:
 a=P/f'{color}-neck-preflight/{color.title()}_neck.3mf'
 with zipfile.ZipFile(a) as f:
  raw=f.read('Metadata/plate_1.gcode');cfg=json.loads(f.read('Metadata/project_settings.config'));meta=E.fromstring(f.read('Metadata/model_settings.config'))
 objnames={o.get('id'):o.find("metadata[@key='name']").get('value') for o in meta.findall('object')}
 names={i.find("metadata[@key='identify_id']").get('value'):objnames[i.find("metadata[@key='object_id']").get('value')] for i in meta.findall('plate/model_instance')}
 transforms={}
 for name in names.values():
  o=next(q for q in ori['parts'] if q['key']==name);T=[v[:] for v in o['printTransform']];T[0][3]+=o['placementXYMm'][0];T[1][3]+=o['placementXYMm'][1];transforms[name]=T
 offset=list(map(float,cfg['extruder_offset'][0].split('x')));x=y=z=0.;width=.42;height=.2;kind='Custom';cur=None
 for no,l in enumerate(raw.decode().splitlines(),1):
  if l.startswith('; OBJECT_ID:'):cur=names[l.rsplit(':',1)[1].strip()]
  if l.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(.+)_id_',l)[1]
  if l.startswith('EXCLUDE_OBJECT_END'):cur=None
  if l.startswith(';TYPE:'):kind=l.split(':',1)[1].strip()
  if l.startswith(';WIDTH:'):width=float(l.split(':',1)[1])
  if l.startswith(';HEIGHT:'):height=float(l.split(':',1)[1])
  if l.startswith('; FEATURE:'):kind=l.split(':',1)[1].strip()
  if l.startswith('; LINE_WIDTH:'):width=float(l.split(':',1)[1])
  if l.startswith('; LAYER_HEIGHT:'):height=float(l.split(':',1)[1])
  if l.startswith('M82'):raise ValueError('Absolute E')
  if not re.match(r'^G[0123] ',l):continue
  cmd=l.split()[0];v={k:float(q) for k,q in num.findall(l.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);zz=v.get('Z',z);pts=[(x,y),(xx,yy)]
  if cmd in ('G2','G3') and ('I'in v or 'J'in v):
   cx=x+v.get('I',0);cy=y+v.get('J',0);rr=math.hypot(x-cx,y-cy);aa=math.atan2(y-cy,x-cx);bb=math.atan2(yy-cy,xx-cx);sgn=1 if cmd=='G3' else -1;span=((bb-aa)*sgn)%(2*math.pi) or 2*math.pi;n=max(1,math.ceil(span/max(.001,2*math.acos(max(-1,min(1,1-.005/max(rr,.005)))))))
   pts=[(cx+rr*math.cos(aa+sgn*span*i/n),cy+rr*math.sin(aa+sgn*span*i/n)) for i in range(n+1)];pts[0]=(x,y);pts[-1]=(xx,yy)
  if cur and kind!='Custom' and v.get('E',0)>0 and (xx!=x or yy!=y or cmd in ('G2','G3')):
   assert abs(zz-z)<1e-6
   points=[inv([p[0]+offset[0],p[1]+offset[1],zz-height/2],transforms[cur]) for p in pts]
   for p,q in zip(points,points[1:]):allsegs.setdefault(cur,[]).append([p,q,math.hypot(width/2,height/2)+.005,kind,no])
  x,y,z=xx,yy,zz
 rows.append({'archive':str(a),'archiveSha256':hashlib.sha256(a.read_bytes()).hexdigest(),'gcodeSha256':hashlib.sha256(raw).hexdigest(),'offsetMm':offset,'config':{k:cfg.get(k) for k in ['support_type','support_on_build_plate_only','support_object_xy_distance','support_top_z_distance']}})
# New part functional regions in unchanged source world coordinates.
features=[]
for id,cx,cy,owner in [('01',6.6,19,'head_bottom'),('02',49.1,9.35,'head_roll_bearing_carrier'),('03',42.1,-30,'head_bottom'),('04',3.1,-30,'head_bottom')]:
 features.append({'part':owner,'name':'thread-pilot-'+id,'axis':2,'center':[cx,cy,0],'range':[107.5,111.15],'radius':1.1})
 features.append({'part':'jaw_support','name':'support-clearance-'+id,'axis':2,'center':[cx,cy,0],'range':[111.65,113.05],'radius':1.4})
for part,ran in [('head_bottom',[5.5,10.5]),('head_roll_bearing_carrier',[39.5,44.5])]:features.append({'part':part,'name':'roll-ring-seat','axis':0,'center':[0,0,115.6146],'range':ran,'radius':11.0})
# Original jaw motor bearing bore, retained in the black frame.
features.append({'part':'jaw_support','name':'jaw-bearing-bore','axis':1,'center':[26.1,0,118.6146],'range':[-34,34],'radius':5.2})
def radius(p,q,c,axis):
 axes=[j for j in range(3) if j!=axis];v=[q[j]-p[j] for j in axes];d=[p[j]-c[j] for j in axes];den=sum(x*x for x in v);t=max(0,min(1,-sum(x*y for x,y in zip(d,v))/den)) if den else 0
 return math.sqrt(sum((x+t*y)**2 for x,y in zip(d,v)))
for f in features:
 best={};hits=[];core=[]
 for p,q,r,k,no in allsegs[f['part']]:
  pq=clip(p,q,f['axis'],f['range'][0]-r,f['range'][1]+r)
  if not pq:continue
  dist=radius(*pq,f['center'],f['axis']);group='support' if 'Support'in k else 'model';inner=dist-r
  if group not in best or inner<best[group]['innerRadiusLowerBoundMm']:best[group]={'innerRadiusLowerBoundMm':inner,'line':no,'type':k}
  if group=='support' and inner<f['radius']:hits.append(no)
  pq=clip(p,q,f['axis'],f['range'][0],f['range'][1])
  if group=='support' and pq and radius(*pq,f['center'],f['axis'])<max(0,f['radius']-.35):core.append(no)
 f.update(best);f['supportPotentialIntersectLineCount']=len(set(hits));f['supportCenterInsideCoreLineCount']=len(set(core));f['coreExampleLines']=sorted(set(core))[:8]
regions=[{'part':'jaw_support','name':'key-pocket','lo':[45,3.8,111.49],'hi':[47.4,6.2,112.4]},{'part':'head_roll_bearing_carrier','name':'key-top-face','lo':[45.2,4,112.19],'hi':[47.2,6,112.22]}]
for reg in regions:
 support=[];model=[];model_layers={}
 for p,q,r,k,no in allsegs[reg['part']]:
  pq=(p,q)
  for ax in range(3):
   if pq:pq=clip(*pq,ax,reg['lo'][ax]-r,reg['hi'][ax]+r)
  if pq:
   (support if 'Support'in k else model).append(no)
 reg['supportNearRegionLines']=len(set(support));reg['supportExampleLines']=sorted(set(support))[:12];reg['modelNearRegionLines']=len(set(model))
# At center of roof under pocket, count actual model extrusions crossing a0.8x0.8 core; no skin inferred from outer dimensions.
roof_layers={}
for p,q,r,k,no in allsegs['jaw_support']:
 if 'Support'in k:continue
 pq=(p,q)
 for ax,lo,hi in [(0,45.8,46.6),(1,4.6,5.4),(2,112.4,113.2146)]:
  if pq:pq=clip(*pq,ax,lo,hi)
 if pq:
  worldZ=(p[2]+q[2])/2;printZ=130.31461-worldZ
  roof_layers.setdefault(round(printZ,5),{'lines':0,'types':set()});roof_layers[round(printZ,5)]['lines']+=1;roof_layers[round(printZ,5)]['types'].add(k)
roof_layers={str(k):{'lines':v['lines'],'types':sorted(v['types'])} for k,v in sorted(roof_layers.items())}
out={'archives':rows,'features':features,'keyRegions':regions,'pocketRoofModelBeadCenterLayersPrintZMm':roof_layers,'segmentCounts':{k:len(v) for k,v in allsegs.items()},'scope':'Actual native supports and conservative extrusion envelopes, current orientation/placement transforms, existing geometry retained.'}
(D/'split-native-toolpaths.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
