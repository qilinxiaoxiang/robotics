from pathlib import Path
import math,json,zipfile,re,hashlib
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
for color in ['yellow','white']:
 a=P/f'{color}-preflight/{color.title()}_preflight.3mf'
 with zipfile.ZipFile(a) as f:raw=f.read('Metadata/plate_1.gcode');cfg=json.loads(f.read('Metadata/project_settings.config'))
 names={'2001':'jaw_frame','2002':'jaw_passive_cheek'} if color=='yellow' else {'2001':'lower_pad'}
 transforms={}
 for name in names.values():
  o=next(q for q in ori['parts'] if q['key']==name);T=[v[:] for v in o['printTransform']];T[0][3]+=o['placementXYMm'][0];T[1][3]+=o['placementXYMm'][1];transforms[name]=T
 offset=list(map(float,cfg['extruder_offset'][0].split('x')));x=y=z=0.;width=.42;height=.2;kind='Custom';cur=None
 for no,l in enumerate(raw.decode().splitlines(),1):
  if l.startswith('; OBJECT_ID:'):cur=names[l.rsplit(':',1)[1].strip()]
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
features=[]
for part,yr in [('jaw_passive_cheek',[-44,-36]),('jaw_frame',[39,44])]:
 features.append({'part':part,'name':'pivot-central-bore','center':[26.1,0,118.6146],'range':yr,'radius':(1 if part=='jaw_passive_cheek' else 3)})
for x in [60,76]:
 features.extend([{'part':'jaw_passive_cheek','name':f'cheek-{x}-clearance','center':[x,0,102.5],'range':[-34,-30.1],'radius':1.4},{'part':'jaw_passive_cheek','name':f'cheek-{x}-head-pocket','center':[x,0,102.5],'range':[-45,-34],'radius':2.2},{'part':'jaw_frame','name':f'main-{x}-pilot','center':[x,0,102.5],'range':[-29.9,-25.5],'radius':1.05}])
for label,cx,cz,sy in [('045',26.1,112.6146,43.75428549),('046',32.1,118.6146,44.31875769),('047',26.1,124.6146,44.38271307),('048',20.1,118.6146,43.81933182)]:
 features.append({'part':'jaw_frame','name':'S15-horn-'+label,'center':[cx,0,cz],'range':[39.7,sy-.2],'radius':1.1})
for f in features:
 vals={};hits=[]
 for p,q,r,k,no in allsegs[f['part']]:
  pq=clip(p,q,1,f['range'][0]-r,f['range'][1]+r)
  if not pq:continue
  v=rad(*pq,f['center'])-r;group='support' if 'Support'in k else 'model'
  if group not in vals or v<vals[group]['radialInnerBoundMm']:vals[group]={'radialInnerBoundMm':v,'line':no,'type':k}
  if group=='support' and v<f['radius']:hits.append(no)
 f.update(vals);f['supportPotentialIntersectLines']=sorted(set(hits))
reliefs=[]
for x in [60,76]:
 lines=[];pts=[]
 for p,q,r,k,no in allsegs['lower_pad']:
  if 'Support' not in k:continue
  if all(max(p[i],q[i])+r>=lo and min(p[i],q[i])-r<=hi for i,lo,hi in [(0,x-3.2,x+3.2),(1,-55,-22.85),(2,98.55,105.15)]):lines.append(no);pts.extend([p,q])
 reliefs.append({'centerX':x,'supportLines':len(set(lines)),'supportWorldCenterlineBounds':[[min(p[i] for p in pts) for i in range(3)],[max(p[i] for p in pts) for i in range(3)]] if pts else None,'cutWorldBounds':[[x-3.2,-55,98.55],[x+3.2,-22.85,105.15]],'openDirectionWorld':[0,0,-1]})
out={'archives':rows,'features':features,'lowerPadReliefs':reliefs,'segmentCounts':{k:len(v) for k,v in allsegs.items()},'scope':'Conservative native bead bounds using actual physical nozzle offset and inverse part transforms; potential overlap is not actual fused plastic.'}
(D/'jaw-native-toolpaths.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
core=[]
for x in [60,76]:
 samples=[]
 for p,q,r,k,no in allsegs['jaw_frame']:
  if 'Support' not in k:continue
  pq=clip(p,q,1,-29.65,-25.75)
  if pq and rad(*pq,[x,0,102.5])<.7:samples.append({'line':no,'type':k,'p':pq[0],'q':pq[1],'radialCenterMm':rad(*pq,[x,0,102.5])})
 core.append({'x':x,'segmentsWhoseCenterIsInsidePilotCore':samples})
(D/'jaw-pilot-support-core.json').write_text(json.dumps(core,indent=2)+'\n')
