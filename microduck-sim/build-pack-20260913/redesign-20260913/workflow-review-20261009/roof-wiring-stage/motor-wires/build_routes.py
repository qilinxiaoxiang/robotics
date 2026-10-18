from pathlib import Path
import json,hashlib,math
import numpy as np,trimesh
from scipy.interpolate import CubicSpline
D=Path(__file__).resolve().parent
src=json.loads((D/'route-input.json').read_text()); meshes=[];reports=[]
def emit(mesh,key,color,group,kind):
 assert mesh.is_watertight and mesh.is_winding_consistent and mesh.volume>0,key
 f=D/(key+'.stl');mesh.export(f)
 reread=trimesh.load_mesh(f,process=True);assert reread.is_watertight and reread.volume>0,key
 row={'key':key,'name':key.replace('-',' '),'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'color':color,'group':group,'units':'mm','coordinates':'world; identity transform','kind':kind,'expectedFinalBoundsMm':mesh.bounds.tolist(),'representation':'mesh','validationStatus':'candidate; collision readback follows'};meshes.append(row)
def route_controls(r):
 A=np.array(r['from']['shoulder']);B=np.array(r['to']['shoulder']);oa=np.array(r['from']['outward']);ob=np.array(r['to']['outward']);a=r['from']['motor'];b=r['to']['motor']
 if max(a,b)<=10:
  if (a<=5)==(b<=5):
   side=-1 if a<=5 else 1; y=side*77
   interior=[[A[0],y,A[2]],[-53,y,(A[2]+B[2])/2],[B[0],y,B[2]]]
  else:interior=[[-53,A[1],A[2]],[-57,0,-100],[-53,B[1],B[2]]]
 else:
  y=-34
  interior=[[A[0],y,A[2]],[max(A[0],B[0])+7,y,(A[2]+B[2])/2],[B[0],y,B[2]]]
 pts=[A,A+oa*6,*map(np.array,interior),B+ob*6,B]
 out=[pts[0]]
 for p in pts[1:]:
  if np.linalg.norm(p-out[-1])>.1:out.append(p)
 if {a,b} in [{6,7},{1,2}]:
  side=1 if max(a,b)>5 else -1;ank=r['from'] if a in [1,6] else r['to'];kne=r['to'] if a in [1,6] else r['from'];AA=np.array(ank['shoulder']);BB=np.array(kne['shoulder']);q=[AA,AA+np.array(ank['outward'])*5,[-49,side*34,-72.5],[-49,side*68.3,-54],[-49,side*68.3,BB[2]],BB+np.array(kne['outward'])*2.8,BB];return np.array(q if a in [1,6]else q[::-1])
 if {a,b}=={1,6}:return np.array([A,A+oa*5,[-49,-34,-73],[-49,0,-76],[-49,34,-73],B+ob*5,B])
 if a==14 and b==13:return np.array([A,A+oa*3,[-19,-14,130],[B[0],-14,131],[B[0],-13,129.5],B+ob*2,B])
 if a==12 and b==5:return np.array([A,A+oa*3,[-3,-14,35],B+ob*6,B])
 if a==0:return np.array([A,A+oa*5,[A[0],25,A[2]],[55,25,134],[55,7,B[2]],B+ob*6,B])
 if a==15 and b==14:return np.array([A,A+oa*3,[A[0],12,132],[-24,12,132],[-24,-9,B[2]],B+ob*5,B])
 return np.array(out)
def tube(points,r=.75,n=16):
 # Circumscribed polygon receives the declared round diameter, not an inscribed under-bound.
 tg=np.gradient(points,axis=0);tg/=np.linalg.norm(tg,axis=1)[:,None]
 ns=[];old=np.array([0.,0.,1.])
 for t in tg:
  a=old-t*np.dot(old,t)
  if np.linalg.norm(a)<.1:a=np.cross(t,[0,1,0])
  a/=np.linalg.norm(a);ns.append(a);old=a
 ns=np.array(ns);bs=np.cross(tg,ns);rr=r/np.cos(np.pi/n)+.004
 vs=np.array([p+rr*(np.cos(q)*a+np.sin(q)*b)for p,a,b in zip(points,ns,bs)for q in np.arange(n)*2*np.pi/n]);fs=[]
 for i in range(len(points)-1):
  for j in range(n):
   k=i*n+j;l=i*n+(j+1)%n;fs.extend([[k,l,l+n],[k,l+n,k+n]])
 vs=np.vstack([vs,points[0],points[-1]]);st=len(vs)-2;en=st+1
 for j in range(n):fs.extend([[st,(j+1)%n,j],[en,(len(points)-1)*n+j,(len(points)-1)*n+(j+1)%n]])
 m=trimesh.Trimesh(vs,fs,process=True);m.fix_normals();return m
for r in src['routes']:
 pts=route_controls(r);oa=np.array(r['from']['outward']);ob=np.array(r['to']['outward'])
 if set([r['from']['motor'],r['to']['motor']]) in [{7,8},{2,3}]:
  A=np.array(r['from']['shoulder']);B=np.array(r['to']['shoulder']);side=1 if A[1]>0 else -1
  pts=np.array([A,A+oa*3.1,[A[0],side*68.6,-31.3],[B[0],side*68.6,-31.3],B+ob*3.1,B])
 elif set([r['from']['motor'],r['to']['motor']]) in [{5,4},{9,10}]:
  A=np.array(r['from']['shoulder']);B=np.array(r['to']['shoulder']);side=1 if A[1]>0 else -1
  P=r['from'] if r['from']['motor'] in [5,10] else r['to'];Q=r['to'] if r['from']['motor'] in [5,10] else r['from'];AA=np.array(P['shoulder']);BB=np.array(Q['shoulder']);q=[AA,AA+np.array(P['outward'])*5,[-10,side*12,27],[-30,side*12,27],[-30,side*12,-4],[-30,BB[1],BB[2]],BB+np.array(Q['outward'])*5,BB];pts=np.array(q if r['from']['motor'] in [5,10]else q[::-1])
 if True:
  # Rounded polyline remains inside the local control hull; prevents cubic overshoot into motors.
  path=[pts[0]]
  for i in range(1,len(pts)-1):
   a,b,c=pts[i-1:i+2];v=b-a;w=c-b;nv=np.linalg.norm(v);nw=np.linalg.norm(w)
   if min(nv,nw)<1e-5:continue
   trim=min(2.5,nv*.3,nw*.3);e=b-v/nv*trim;f=b+w/nw*trim
   last=path[-1]
   path.extend([last+(e-last)*t for t in np.linspace(0,1,max(2,math.ceil(np.linalg.norm(e-last)/.35)))[1:]])
   path.extend([(1-t)**2*e+2*(1-t)*t*b+t*t*f for t in np.linspace(0,1,17)[1:]])
  last=path[-1];path.extend([last+(pts[-1]-last)*t for t in np.linspace(0,1,max(2,math.ceil(np.linalg.norm(pts[-1]-last)/.35)))[1:]])
  center=np.array(path);seg=np.linalg.norm(np.diff(center,axis=0),axis=1);center=center[np.r_[True,seg>1e-8]];u=np.r_[0,np.cumsum(np.linalg.norm(np.diff(center,axis=0),axis=1))];ratio=u/u[-1];cs=CubicSpline(u,center)
 else:
  ss=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))];cs=CubicSpline(ss,pts,bc_type=((1,oa),(1,-ob)));u=np.linspace(0,ss[-1],max(40,math.ceil(ss[-1]/.5)));center=cs(u);ratio=u/u[-1]

 wa=np.array(r['from']['width']);wb=np.array(r['to']['width']);
 if np.dot(wa,wb)<0:wb=-wb
 offset=(1-ratio[:,None])*wa+ratio[:,None]*wb; offset/=np.linalg.norm(offset,axis=1)[:,None]
 strands=[]
 for k,(col,slot) in enumerate([('#303030',-1),('#d33b31',0),('#f1c932',1)]):
  spread=1.6+.9*np.maximum(np.exp(-u/5),np.exp(-(u[-1]-u)/5));points=center+slot*spread[:,None]*offset;emit(tube(points),r['id']+f'-conductor-{k+1}',col,'Motor harness candidates','wire');strands.append(points.tolist())
 for end in ['from','to']:
  p=r[end];key=f"motor-{p['motor']:02}-socket-{p['sourceSocket']}-housing"
  if not any(x['key']==key for x in meshes):
   lo,hi=np.array(p['housingLocalBounds']);box=trimesh.creation.box(hi-lo);box.apply_translation((lo+hi)/2);box.apply_transform(np.array(p['transform']));emit(box,key,'#eee7dc','Registered connector housings','receiving-envelope')
 d1=cs(u,1);d2=cs(u,2);kap=np.linalg.norm(np.cross(d1,d2),axis=1)/np.linalg.norm(d1,axis=1)**3
 reports.append({**r,'controlPointsMm':pts.tolist(),'centerlineMm':center.tolist(),'conductorCenterlinesMm':strands,'centerlineLengthMm':float(np.linalg.norm(np.diff(center,axis=0),axis=1).sum()),'minimumSampledCenterlineBendRadiusMm':float(1/max(kap)),'curve':'Locally rounded polyline; source-port outward lead. Neutral pose receiving candidate, not measured stock bend specification.','spareLengthModeled':False,'assembly':'Pre-seat knee plugs before thigh enclosure closure. Actual prior knee test identifies orange thigh lip, not opposite black plate. Other joints require local insertion review; do not infer all connector paths accepted.'})
(D/'routes.json').write_text(json.dumps({'source':src,'routes':reports},indent=2))
(D/'manifest.json').write_text(json.dumps({'status':'STAGED_CANDIDATE_NOT_WIRING_ACCEPTANCE','units':'mm','parts':meshes,'sourceManifest':src['sourceManifest'],'sourceManifestSha256':src['sourceManifestSha256'],'routeReport':str(D/'routes.json'),'wholeHarnessAccepted':False,'openrbPortPending':False,'spareStockLengthNotYetAllocated':True,'pinOrderUnknown':True},indent=2));print(len(meshes),'closed importable parts')
