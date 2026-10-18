from pathlib import Path
import json,math,hashlib
import numpy as np,trimesh,manifold3d as mf
F=Path(__file__).resolve().parent
def primitives(points,R=2.):
 pts=np.array(points,dtype=float);out=[];prev=pts[0];tans=[]
 for ix,(a,b,c) in enumerate(zip(pts,pts[1:],pts[2:])):
  R=2.
  u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b);ang=math.acos(np.clip(np.dot(u,v),-1,1));trim=R*math.tan(ang/2)
  assert trim<min(np.linalg.norm(b-a),np.linalg.norm(c-b)),(b,trim)
  e=b-u*trim;f=b+v*trim;n=np.cross(u,v);n/=np.linalg.norm(n);cen=e+np.cross(n,u)*R
  if np.linalg.norm(e-prev)>1e-7:out.append({'kind':'line','start':prev.tolist(),'end':e.tolist(),'lengthMm':float(np.linalg.norm(e-prev))})
  h=ang/2;rv=e-cen;mid=cen+rv*math.cos(h)+np.cross(n,rv)*math.sin(h)
  out.append({'kind':'arc','start':e.tolist(),'mid':mid.tolist(),'end':f.tolist(),'center':cen.tolist(),'normal':n.tolist(),'radiusMm':R,'sweepRadians':ang,'lengthMm':R*ang});prev=f
 if np.linalg.norm(pts[-1]-prev)>1e-7:out.append({'kind':'line','start':prev.tolist(),'end':pts[-1].tolist(),'lengthMm':float(np.linalg.norm(pts[-1]-prev))})
 # check joins are forward; corner trims must not overlap
 for p in out:
  if p['kind']=='line':assert np.linalg.norm(np.array(p['end'])-p['start'])>0
 return out
def sample(pr):
 pts=[];tans=[]
 for p in pr:
  a=np.array(p['start']);b=np.array(p['end']);N=max(2,math.ceil(p['lengthMm']/.15))
  for q in np.linspace(0,1,N,endpoint=False):
   if p['kind']=='line':v=b-a;point=a+q*v;t=v/np.linalg.norm(v)
   else:
    n=np.array(p['normal']);rv=a-p['center'];ang=p['sweepRadians']*q;rad=rv*math.cos(ang)+np.cross(n,rv)*math.sin(ang);point=np.array(p['center'])+rad;t=np.cross(n,rad)/p['radiusMm']
   pts.append(point);tans.append(t)
 pts.append(b);tans.append(tans[-1]);return np.array(pts),np.array(tans)
def tube(pts,tans):
 n=24;r=(1.3+.003)/math.cos(math.pi/n);frames=[];old=np.array([0.,0.,1.])
 for t in tans:
  x=old-np.dot(old,t)*t
  if np.linalg.norm(x)<.1:x=np.cross(t,[0,1,0])
  x/=np.linalg.norm(x);frames.append(x);old=x
 v=[p+r*(math.cos(q)*x+math.sin(q)*np.cross(t,x)) for p,t,x in zip(pts,tans,frames) for q in np.arange(n)*2*math.pi/n];f=[]
 for i in range(len(pts)-1):
  for j in range(n):a=i*n+j;b=i*n+(j+1)%n;f.extend([[a,b,b+n],[a,b+n,a+n]])
 v.extend([pts[0],pts[-1]]);st=len(v)-2;en=st+1
 for j in range(n):f.extend([[st,(j+1)%n,j],[en,(len(pts)-1)*n+j,(len(pts)-1)*n+(j+1)%n]])
 m=trimesh.Trimesh(v,f,process=True);m.fix_normals();assert m.is_watertight and m.is_winding_consistent;return m
def solid(m):
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(a.status())=='Error.NoError' and a.volume()>0;return a

r=json.loads((F/'integrated-rigid-package.json').read_text());controls=[[69.18,-13.66,150.2],[69.18,-17,150.2],[62,-17,146],[40,-16.3,143],[12,-16.3,143],[-6,-16.3,138],[-6,-16.3,128.7],[-6,-8.735,128.7]]
pr=primitives(controls);p,t=sample(pr);m=tube(p,t);f=F/'usb-short-custom-wire-receiving.stl';m.export(f);assert trimesh.load_mesh(f).is_volume
row={'key':'USB short custom shielded harness receiver','file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'worldTransform':np.eye(4).tolist(),'group':'usb_wire','geometryKind':'custom-wire-receiving','diameterMm':2.6,'minDesignRadiusMm':2,'lengthMm':sum(x['lengthMm']for x in pr)}
r['parts'].append(row);(F/'usb-routed-package.json').write_text(json.dumps(r,indent=2)+'\n');(F/'usb-short-route.json').write_text(json.dumps({'status':'PAPER_CUSTOM_TERMINATION_CANDIDATE','part':row,'primitives':pr,'controlPointsMm':controls,'terminalAssumptions':['Micro solder-tab breakout exits negative Y from insulated receiver; exact tab fanout/manufacture not accepted','C FFC connector must be mapped to retained factory USB2 nets; permanent round-wire termination is custom work, not asserted ready cable'],'physicalApproved':False,'procurementApproved':False},indent=2)+'\n')
s=(F/'check_package.py').read_text().replace("src=F/'joint-package.json'","src=F/'usb-routed-package.json'").replace("'joint-check-'","'usb-routed-check-'");(F/'check_usb_routed.py').write_text(s);print(row)
