from pathlib import Path
import json,math,re,hashlib,zipfile
D=Path(__file__).resolve().parent; P=D.parent; R=P.parent.parent
F=R/'workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009'
sources={}
def read(p):
 sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
prep=read(P/'run/preparation.json'); T=read(F/'prototype-adoption/cap-union.json')['printTransform']; pm=read(F/'custom-harness-package.json')['piCurrentWorldDelta']; mounts=read(F/'integrated-rigid-package.json')['mountFeatures']; rays=read(F/'pi-mount-roof-rays.json')['rows']
def transform(p,t,vector=False):return [sum(t[i][j]*p[j] for j in range(3))+(0 if vector else t[i][3]) for i in range(3)]
features=[]
def add(name,part,p,a,lo,hi,r):features.append(dict(name=name,part=part,originWorld=p,axisWorld=a,axialRangeMm=[lo,hi],radiusMm=r))
for m in mounts[:4]:add(m['key'],'head_cap',m['seat'],m['axis'],.15,4.7,.85)
for i,row in enumerate(rays):
 for j,x in enumerate((47.5,70.5)):add(f'pi-pilot-{i}-{j}','head_cap',transform([x,row['sourceY'],125.9],pm),transform([0,0,1],pm,True),.55,4.6,.85)
for i,x in enumerate((5,45)):
 add(f'speaker-pilot-{i}','head_cap',[x,-21.5,136.45],[0,0,1],.15,3.1,1.05)
 add(f'cradle-through-{i}','speaker_cradle',[x,-21.5,131.44],[0,0,1],.01,1.19,1.4)
 add(f'keeper-through-{i}','speaker_keeper',[x,-21.5,135.45],[0,0,1],.01,.99,1.4)
for i,x in enumerate((32.3499993896,19.6499993896)):add(f'amp-pilot-{i}','head_cap',[x,17.287000885,134.0849994],[0,0,1],.15,7.0,1.05)
# Original three shell-closure pilots, beyond the bottom-shell/entry stack.
body=read(R.parents[1]/'hardware-design-20260912/whole-robot-20260912/assembly/body-transforms.json')['zero_joint_body_transforms']['jaw_soft']
fast=next(x for x in read(R/'assembly-fasteners.json')['connections'] if x['id']=='head_cap_closure')
for i,p in enumerate(fast['hole_centers_mm']):add(f'original-cap-closure-{i}','head_cap',transform(p,body),transform(fast['axis'],body,True),3.2,7.6,fast['pilot_diameter_mm']/2)
def cliprad(p,q,f):
 ax=f['axisPlate'];c=f['originPlate'];u=[p[i]-c[i]for i in range(3)];v=[q[i]-p[i]for i in range(3)];along=sum(u[i]*ax[i]for i in range(3));delta=sum(v[i]*ax[i]for i in range(3));lo,hi=f['axialRangeMm']
 if abs(delta)<1e-12:
  if not lo<=along<=hi:return None
  a=0;b=1
 else:
  ts=[(lo-along)/delta,(hi-along)/delta];a=max(0,min(ts));b=min(1,max(ts))
  if a>b:return None
 w=[u[i]-along*ax[i]for i in range(3)];d=[v[i]-delta*ax[i]for i in range(3)];den=sum(t*t for t in d);t=max(a,min(b,-sum(w[i]*d[i]for i in range(3))/den))if den else a
 return math.sqrt(sum((w[i]+t*d[i])**2 for i in range(3))),along+t*delta
reports=[]
for machine in ('Bambu','Elegoo'):
 placement={r['key']:r['translation'] for r in next(r for r in prep['rows'] if r['machine']==machine)['placements']}; fs=json.loads(json.dumps(features))
 for f in fs:
  key=f['part'];t=T if key=='head_cap' else [[1,0,0,-25],[0,1,0,21.5],[0,0,1,-(131.44 if key=='speaker_cradle' else 135.45)],[0,0,0,1]]
  f['originPlate']=[a+b for a,b in zip(transform(f['originWorld'],t),placement[key])];f['axisPlate']=transform(f['axisWorld'],t,True);f['supportCore']=[];f['supportPotential']=[];f['modelCore']=[];f['nearbyModelSegments']=0
  a=[f['originPlate'][k]+f['axisPlate'][k]*f['axialRangeMm'][0] for k in range(3)];b=[f['originPlate'][k]+f['axisPlate'][k]*f['axialRangeMm'][1] for k in range(3)];f['bounds']=[[min(a[k],b[k])-f['radiusMm']-.6 for k in range(3)],[max(a[k],b[k])+f['radiusMm']+.6 for k in range(3)]]
 file=P/f'run/native/Orange_{machine}/plate_1.gcode'; archive=file.parent/'sliced.3mf';off=2 if machine=='Bambu' else 0;x=y=z=e=0.;height=.2;width=.42;kind='Custom';relative=True;segments=0
 for no,l in enumerate(file.open(),1):
  if l.startswith((';TYPE:','; FEATURE:')):kind=l.split(':',1)[1].strip()
  elif l.startswith((';WIDTH:','; LINE_WIDTH:')):width=float(l.split(':',1)[1])
  elif l.startswith((';HEIGHT:','; LAYER_HEIGHT:')):height=float(l.split(':',1)[1])
  elif l.startswith('M83'):relative=True
  elif l.startswith('M82'):relative=False
  elif l.startswith('G92 E'):e=float(l.split('E',1)[1].split()[0])
  if not re.match(r'^G[0123] ',l):continue
  vals={k:float(v)for k,v in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',l.split(';')[0])};xx=vals.get('X',x);yy=vals.get('Y',y);zz=vals.get('Z',z);de=vals.get('E',0) if relative else vals.get('E',e)-e
  if 'E'in vals:e=vals['E'] if not relative else e+vals['E']
  if de>0 and kind!='Custom' and (xx!=x or yy!=y):
   points=[(x,y),(xx,yy)]
   if l.startswith(('G2 ','G3 '))and('I'in vals or'J'in vals):
    cx=x+vals.get('I',0);cy=y+vals.get('J',0);rr=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sg=1 if l.startswith('G3')else-1;span=((b-a)*sg)%(2*math.pi)or 2*math.pi;n=max(1,math.ceil(span/max(.001,2*math.acos(max(-1,min(1,1-.01/max(rr,.01)))))));points=[(cx+rr*math.cos(a+sg*span*i/n),cy+rr*math.sin(a+sg*span*i/n))for i in range(n+1)];points[0]=(x,y);points[-1]=(xx,yy)
   pts=[[p[0],p[1]+off,zz-height/2]for p in points];rad=math.hypot(width/2,height/2)+.012
   for p,q in zip(pts,pts[1:]):
    segments+=1
    for f in fs:
     bb=f['bounds']
     if any(max(p[k],q[k])<bb[0][k] or min(p[k],q[k])>bb[1][k] for k in range(3)):continue
     ans=cliprad(p,q,f)
     if ans is None:continue
     d,t=ans; row=dict(line=no,radialCenterMm=d,axialMm=t,type=kind)
     if 'support'in kind.lower():
      if d<f['radiusMm']+rad:f['supportPotential'].append(row)
      if d<f['radiusMm']-rad:f['supportCore'].append(row)
     else:
      f['nearbyModelSegments']+=1
      if d<f['radiusMm']-rad:f['modelCore'].append(row)
  x,y,z=xx,yy,zz
 for f in fs:
  for k in ('supportCore','supportPotential','modelCore'):
   a=f[k];f[k+'Count']=len(a);f[k+'AxialRangeMm']=[min(r['axialMm']for r in a),max(r['axialMm']for r in a)] if a else None;f[k]=a[:12]
 reports.append(dict(machine=machine,gcode=str(file),gcodeSha256=sha(file),archive=str(archive),archiveSha256=sha(archive),nozzleOffsetAddedMm=[0,off,0],extrudedSegments=segments,features=fs))
 print(machine,[(f['name'],f['supportCoreCount'],f['modelCoreCount'],f['nearbyModelSegments'])for f in fs],flush=True)
report=dict(scope='Native sliced prototype mounting pilots and speaker through-holes only',sourceHashes=sources,method='Stream actual G-code. Arc segments sampled at <=0.01mm sagitta; width/height bead circumradius +0.012mm. Definite core means entire bead radius inside nominal bore, potential only is not a blocked hole. Bambu extruder offset restored. All support segments checked regardless object marker.',results=reports)
(D/'hole-readback.json').write_text(json.dumps(report,indent=2)+'\n')
