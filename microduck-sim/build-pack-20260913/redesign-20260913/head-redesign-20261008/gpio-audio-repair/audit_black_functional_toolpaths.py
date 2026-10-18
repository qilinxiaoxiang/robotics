from pathlib import Path
import zipfile,json,re,math,hashlib
D=Path(__file__).resolve().parent
R=D.parent.parent
P=R/'printing/11-ASSEMBLY-REPAIR-20261008'
a=P/'black-preflight/Black_preflight.3mf'
with zipfile.ZipFile(a) as z:
 raw=z.read('Metadata/plate_1.gcode'); cfg=json.loads(z.read('Metadata/project_settings.config'))
s=raw.decode();num=re.compile(r'([XYZEIJ])([-+]?\d*\.?\d+)');x=y=z=0.;width=.42;height=.2;kind='Custom';active=False; segs=[]
err=.005
for no,l in enumerate(s.splitlines(),1):
 if l.startswith('M82'):raise ValueError('absolute E')
 if l.startswith('EXCLUDE_OBJECT_START'):active=True
 if l.startswith('EXCLUDE_OBJECT_END'):active=False
 if l.startswith(';TYPE:'):kind=l[6:].strip()
 if l.startswith(';WIDTH:'):width=float(l[7:])
 if l.startswith(';HEIGHT:'):height=float(l[8:])
 if not re.match(r'^G[0123] ',l):continue
 cmd=l.split()[0];v={k:float(q) for k,q in num.findall(l.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);zz=v.get('Z',z)
 pts=[(x,y),(xx,yy)]
 if cmd in ('G2','G3') and ('I'in v or 'J'in v):
  cx=x+v.get('I',0);cy=y+v.get('J',0);r=math.hypot(x-cx,y-cy);aa=math.atan2(y-cy,x-cx);bb=math.atan2(yy-cy,xx-cx);sign=1 if cmd=='G3' else -1
  span=((bb-aa)*sign)%(2*math.pi) or 2*math.pi;n=max(1,math.ceil(span/max(.001,2*math.acos(max(-1,min(1,1-err/max(r,err)))))))
  pts=[(cx+r*math.cos(aa+sign*span*i/n),cy+r*math.sin(aa+sign*span*i/n)) for i in range(n+1)];pts[0]=(x,y);pts[-1]=(xx,yy)
 if active and kind!='Custom' and v.get('E',0)>0 and (xx!=x or yy!=y or cmd in ('G2','G3')):
  assert abs(zz-z)<1e-7,'extruding helical arc needs explicit handling'
  for p,q in zip(pts,pts[1:]):segs.append(([*p,zz-height/2],[*q,zz-height/2],width,height,kind,no))
 x,y,z=xx,yy,zz

def clipped(p,q,axis,lo,hi):
 d=q[axis]-p[axis]
 if abs(d)<1e-12:return (p,q) if lo<=p[axis]<=hi else None
 aa=(lo-p[axis])/d;bb=(hi-p[axis])/d;t0=max(0,min(aa,bb));t1=min(1,max(aa,bb))
 return ([p[k]+t0*(q[k]-p[k]) for k in range(3)],[p[k]+t1*(q[k]-p[k]) for k in range(3)]) if t0<=t1 else None

def radial(p,q,c,axes):
 v=[q[k]-p[k] for k in axes];d=[p[k]-c[k] for k in axes];den=sum(t*t for t in v);t=max(0,min(1,-sum(d0*v0 for d0,v0 in zip(d,v))/den)) if den else 0
 return math.sqrt(sum((d0+t*v0)**2 for d0,v0 in zip(d,v)))
features=[]
for i,(cx,cy) in enumerate([(128,134),(134,128),(122,128),(128,122)]):features.append(dict(name=f'M2x6-{i+1}',axis=2,range=[0,3.900004],center=[cx,cy,0],radius=1.2))
for side,ran in [('left',[110.5,113.5]),('right',[142.5,145.5])]:
 for cy,cz in [(134,18.69354364),(128,12.69354364),(128,24.69354364),(122,18.69354364)]:features.append(dict(name=f'horizontal-horn-{side}-{cy}-{cz:.3f}',axis=0,range=ran,center=[0,cy,cz],radius=1.1))
rows=[]
for f in features:
 vals={};axis=f['axis'];axes=[k for k in range(3) if k!=axis]
 for p,q,w,h,k,no in segs:
  # Rectangular bead bound: use width/2 on XY, height/2 along Z. Radial support conservative max for horizontal holes.
  rad=(w/2 if axis==2 else max(w,h)/2)+err; axrad=h/2 if axis==2 else w/2
  pq=clipped(p,q,axis,f['range'][0]-axrad,f['range'][1]+axrad)
  if pq is None:continue
  r=radial(*pq,f['center'],axes)-rad
  if axis==0:
   ymin=min(pq[0][1],pq[1][1])-w/2-err;ymax=max(pq[0][1],pq[1][1])+w/2+err
   zmin=p[2]-h/2;zmax=p[2]+h/2
   r=math.hypot(max(ymin-f['center'][1],f['center'][1]-ymax,0),max(zmin-f['center'][2],f['center'][2]-zmax,0))
  group='support' if k.startswith('Support') else 'model'
  if group not in vals or r<vals[group]['innerMaterialRadiusLowerBoundMm']:vals[group]={'innerMaterialRadiusLowerBoundMm':r,'line':no,'type':k,'z':p[2],'width':w,'height':h}
 rows.append({**f,**vals})
# Side-wall bearing pilot R8 is near the bed. Check support on its mating cylindrical surface.
near=[]
for p,q,w,h,k,no in segs:
 if not k.startswith('Support'):continue
 pq=clipped(p,q,2,-h/2,1.65+h/2)
 if pq:
  r=radial(*pq,[128,128,0],[0,1])-w/2-err
  near.append((r,no,k))
seat_support=[]
for f in features[:4]:
 hits=[]
 for p,q,w,h,k,no in segs:
  if not k.startswith('Support') or not p[2]-h/2-.001<=3.900004<=p[2]+h/2+.001:continue
  rr=radial(p,q,f['center'],[0,1])-w/2-err
  if rr<=2.5:hits.append(no)
 seat_support.append({'name':f['name'],'supportLinesAtSeatPlaneWithinOuterRadius2p5':hits})
result={'seatSupport':seat_support,'archive':str(a),'archiveSha256':hashlib.sha256(a.read_bytes()).hexdigest(),'gcodeSha256':hashlib.sha256(raw).hexdigest(),'flattenedExtrusionSegments':len(segs),'arcChordErrorMm':err,'features':rows,'bearingPilotSupportMinimumRadiusLowerBoundMm':min(near),'settings':{k:cfg.get(k) for k in ['enable_support','support_type','support_style','support_object_xy_distance','support_top_z_distance','support_on_build_plate_only','elefant_foot_compensation','elephant_foot_compensation','hole_to_polyhole','xy_hole_compensation']},'scope':'Native bead geometric upper bounds, no material shrinkage or physical tolerance certification.'}
(D/'black-functional-toolpaths.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
shoulder=[]
for p,q,w,h,k,no in segs:
 if not k.startswith('Support') or p[2]+h/2>1.9+.001:continue
 inner=radial(p,q,[128,128,0],[0,1])-w/2-err
 outer=max(math.hypot(v[0]-128,v[1]-128) for v in [p,q])+w/2+err
 if inner<=9.003 and outer>=8.0:shoulder.append((p[2]+h/2,no,k,inner,outer))
result['bearingShoulderSupportHighestTop']=max(shoulder) if shoulder else None
(D/'black-functional-toolpaths.json').write_text(json.dumps(result,indent=2)+'\n')
print('bearing shoulder',result['bearingShoulderSupportHighestTop'])
