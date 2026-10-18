from pathlib import Path
import numpy as np,trimesh,manifold3d as mf,json,base64
from scipy.interpolate import CubicSpline
D=Path(__file__).resolve().parent;R=D.parent;H=R.parent;C=H/'curved-head';G=H.parent/'leg-guide-20261006';data=json.loads((G/'full-build-data.json').read_text());P={p['key']:p for p in data['parts']}
def man(m):
 m=m.copy();m.process();return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def tri(s):
 a=s.to_mesh();return trimesh.Trimesh(np.asarray(a.vert_properties)[:,:3],np.asarray(a.tri_verts),process=True)
def dec(k):
 p=P[k];return man(trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True))
files={'cap':C/'curved-cap-with-internal-posts-and-usb-world.stl','camera':R/'camera-shifted-reference-world.stl','retainer':R/'camera-retainer-world.stl','face':R/'face-with-camera-anchors-world.stl','screws':R/'camera-all-six-screw-envelopes-world.stl'}
for n in ['openrb','speaker','amplifier']:files[n]=C/(n+'-curved-layout-world.stl')
for n in ['zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails']:files[n]=C/(n+'-world.stl')
obs={k:man(trimesh.load_mesh(p)) for k,p in files.items()};obs.update({k:dec(k) for k in ['pi','head_bottom','jaw_support','motor14','motor15']})

def curve(waypoints):
 p=np.array(waypoints,float);t=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))];c=CubicSpline(t,p,bc_type=((1,[0,0,1]),(1,[0,-1,0])));ts=np.linspace(0,t[-1],int(t[-1]*4)+1);p=c(ts);v=c(ts,1);v/=np.linalg.norm(v,axis=1)[:,None];acc=c(ts,2);curv=np.linalg.norm(np.cross(c(ts,1),acc),axis=1)/np.linalg.norm(c(ts,1),axis=1)**3
 # Frenet binormal permits bending about ribbon width; near straights parallel-transport old width.
 widths=[];prev=np.array([0.,1.,0.])
 for vv,aa in zip(v,acc):
  w=np.cross(vv,aa)
  if np.linalg.norm(w)<1e-6:w=prev-np.dot(prev,vv)*vv
  w/=np.linalg.norm(w)
  if np.dot(w,prev)<0:w=-w
  widths.append(w);prev=w
 widths=np.array(widths);# endpoint orientation is a constraint checked in report
 ds=np.linalg.norm(np.diff(p,axis=0),axis=1);arclen=np.r_[0,np.cumsum(ds)];L=arclen[-1]
 wide=5+11*np.clip(1-arclen/8,0,1)+6.5*np.clip(1-(L-arclen)/8,0,1)
 normal=np.cross(v,widths);verts=[]
 for pp,w,n,ww in zip(p,widths,normal,wide):verts.extend([pp-w*ww/2-n*.3,pp+w*ww/2-n*.3,pp+w*ww/2+n*.3,pp-w*ww/2+n*.3])
 faces=[[0,2,1],[0,3,2]]
 for i in range(len(p)-1):
  for j in range(4):a=4*i+j;b=4*i+(j+1)%4;c_=b+4;d=a+4;faces.extend([[a,b,c_],[a,c_,d]])
 n=len(verts);faces.extend([[n-4,n-3,n-2],[n-4,n-2,n-1]])
 mesh=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(mesh);s=man(mesh)
 return s,{'length':L,'minRadius':1/max(curv),'firstWidth':widths[0].tolist(),'lastWidth':widths[-1].tolist(),'status':str(s.status())},p
if __name__=='__main__':
 wp=[[74.73,-.091,140.58],[74.73,-.091,146],[70,0,151.8],[62,0,152],[56,6,151],[57,18,146],[53,27,137],[-10,27,137],[-17,21,137],[-10,15,137],[44,15,137],[54,24,135],[59,35,131.05],[65.8,38.5,131.05],[65.8,32.49,131.05]]
 s,r,p=curve(wp);r['hits']={k:max(0,(s^o).volume()) for k,o in obs.items()};print(json.dumps(r,indent=2));tri(s).export(D/'route-probe-world.stl');(D/'route-waypoints.json').write_text(json.dumps(wp))
