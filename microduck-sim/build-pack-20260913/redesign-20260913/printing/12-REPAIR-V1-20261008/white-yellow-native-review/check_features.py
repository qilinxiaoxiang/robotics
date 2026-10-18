from pathlib import Path
import json,math,re,zipfile,os,hashlib,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;P=D.parent;R=P.parent.parent;H=R/'head-redesign-20261008';col=sys.argv[1];label=sys.argv[2] if len(sys.argv)>2 else col;archive=Path(sys.argv[3]) if len(sys.argv)>3 else P/f'native-{col}/{col}_V1.gcode.3mf';inputs=[Path(__file__),P/'orientation-preparation.json'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();ori=next(q for q in json.loads(inputs[-1].read_text())['parts'] if q['color']==col);T=ori['printTransform'];features=[]
def read(p):inputs.append(p);return json.loads(p.read_text())
def feat(name,origin,axis,lo,hi,r):
 a=[sum(T[i][j]*origin[j] for j in range(3))+T[i][3]+(ori['placementXYMm'][i] if i<2 else 0) for i in range(3)];v=[sum(T[i][j]*axis[j] for j in range(3)) for i in range(3)];features.append(dict(name=name,originWorld=origin,axisWorld=axis,origin=a,axis=v,range=[lo,hi],radius=r,coreSupport=[],potentialSupport=[],modelCore=[],minModelInnerRadiusMm=999.))
if col=='White':
 for q in read(H/'camera-ribbon-repair/positive-x225/candidate-manifest.json')['cameraFasteners']:feat(q['id'],q['headSeatMm'],[-v for v in q['outwardAxis']],1.65,4.15,.8)
 for q in read(H/'camera-ribbon-repair/positive-x225/pi-support-report.json')['screws']:feat(q['id'],q['headSeatMm'],[-v for v in q['outwardAxis']],1.75,6.1,1.05)
else:
 for i,(x,y) in enumerate([(6.6,19),(49.1,9.35),(42.1,-30),(3.1,-30)]):feat('support-pilot-'+str(i+1),[x,y,111.5146],[0,0,-1],.2,3.2,1.05)
 for i,(x,y) in enumerate([(75.6,39),(75.6,-39),(-23.4,0)]):feat('cap-through-'+str(i+1),[x,y,112.311],[0,0,1],.05,1.5,1.2)
 # Actual22mm head-roll seats; only lower open-seat half is relevant to printed shell.
 for i,x in enumerate([6,40]):feat('head-roll-seat-'+str(i+1),[x,0,115.6146],[1,0,0],.1,3.8,10.5)
exec((H/'gpio-audio-repair/speaker-final-export/native-V1-Orange-original-orientation-exclusive/check_cap_bores.py').read_text().split('def cliprad')[1].split('x=y=z=')[0].join(['def cliprad','']))
x=y=z=0.;kind='Custom';width=.4;height=.2;started=False
with zipfile.ZipFile(archive) as ar:
 cfg=json.loads(ar.read('Metadata/project_settings.config'));off=[float(v) for v in cfg['extruder_offset'][0].split('x')];names=[n for n in ar.namelist() if n.endswith('.gcode')];assert len(names)==1
 for no,raw in enumerate(ar.open(names[0]),1):
  l=raw.decode()
  if l.startswith('; Z_HEIGHT:'):started=True
  elif l.startswith('; LAYER_HEIGHT:'):height=float(l.split(':')[1])
  elif l.startswith('; FEATURE:'):kind=l.split(':')[1].strip()
  elif l.startswith('; LINE_WIDTH:'):width=float(l.split(':')[1])
  if not re.match(r'^G[0123] ',l):continue
  vals={k:float(v) for k,v in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',l.split(';')[0])};xx=vals.get('X',x);yy=vals.get('Y',y);zz=vals.get('Z',z)
  if started and vals.get('E',0)>0 and kind!='Custom'and(xx!=x or yy!=y):
   points=[(x,y),(xx,yy)]
   if l.startswith(('G2 ','G3 '))and('I'in vals or'J'in vals):
    cx=x+vals.get('I',0);cy=y+vals.get('J',0);rr=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sg=1 if l.startswith('G3')else-1;span=((b-a)*sg)%(2*math.pi)or 2*math.pi;n=max(1,math.ceil(span/max(.001,2*math.acos(max(-1,min(1,1-.01/max(rr,.01)))))));points=[(cx+rr*math.cos(a+sg*span*i/n),cy+rr*math.sin(a+sg*span*i/n)) for i in range(n+1)];points[0]=(x,y);points[-1]=(xx,yy)
   points=[(a+off[0],b+off[1],zz-height/2) for a,b in points];rad=math.hypot(width/2,height/2)+.012
   for f in features:
    c=f['origin'];ax=f['axis'];lo,hi=f['range'];a=[c[k]+ax[k]*lo for k in range(3)];b=[c[k]+ax[k]*hi for k in range(3)];bound=f['radius']+rad
    for p,q in zip(points,points[1:]):
     if any(max(p[k],q[k])<min(a[k],b[k])-bound or min(p[k],q[k])>max(a[k],b[k])+bound for k in range(3)):continue
     d=cliprad(p,q,f)
     if d is None:continue
     if'support'in kind.lower():
      if d<f['radius']+rad:f['potentialSupport'].append(no)
      if d<f['radius']-.3:f['coreSupport'].append(no)
     else:
      f['minModelInnerRadiusMm']=min(f['minModelInnerRadiusMm'],d-rad)
      if d<f['radius']-.4:f['modelCore'].append(no)
  x,y,z=xx,yy,zz
for f in features:
 for k in ['coreSupport','potentialSupport','modelCore']:v=sorted(set(f[k]));f[k+'Count']=len(v);f[k]=v[:10]
report={'archive':str(archive),'archiveSha256':sha(archive),'physicalNozzleOffsetAddedMm':off,'features':features,'sourceHashes':{str(p):sha(p) for p in inputs},'scope':'Native toolpath in declared screw bores and head-roll seats only; support core contacts separate from conservative edge bead bounds. No physical removal/adhesion claim.'};(D/f'{label}-features.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps([{'name':f['name'],'coreSupport':f['coreSupportCount'],'potential':f['potentialSupportCount'],'modelCore':f['modelCoreCount'],'minRadius':f['minModelInnerRadiusMm']} for f in features]))
