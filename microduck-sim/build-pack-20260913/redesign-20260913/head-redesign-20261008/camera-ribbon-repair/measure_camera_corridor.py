from pathlib import Path
import os,json,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh
D=Path(__file__).resolve().parent;O=D/'positive-x225';Q=D/'fixed-pose-local-bend';j={'integrationReady':False,'method':'X ray intersections through exact mesh triangle planes; sections only, not complete route proof','parts':{},'sourceHashes':{}}
for name in ['camera_board_clamped','pi','face_x225_complete','camera_three_screw_clamp']:
 p=O/(name+'-world.stl');j['sourceHashes'][str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();m=trimesh.load(p,force='mesh');tri=m.triangles;v0=tri[:,0,1:];e1=tri[:,1,1:]-v0;e2=tri[:,2,1:]-v0;den=e1[:,0]*e2[:,1]-e1[:,1]*e2[:,0];ok=abs(den)>1e-12;rows=[]
 for y in [0,4,6,9.37,12,14,18,22,26,30]:
  for z in [123.2,127,131.1146,135,139.0]:
   d=np.array([y,z])-v0;a=np.zeros(len(den));b=a.copy();a[ok]=(d[ok,0]*e2[ok,1]-d[ok,1]*e2[ok,0])/den[ok];b[ok]=(e1[ok,0]*d[ok,1]-e1[ok,1]*d[ok,0])/den[ok];hit=ok&(a>=-1e-8)&(b>=-1e-8)&(a+b<=1+1e-8);xs=tri[hit,0,0]+a[hit]*(tri[hit,1,0]-tri[hit,0,0])+b[hit]*(tri[hit,2,0]-tri[hit,0,0]);xs=sorted(set(np.round(xs,7).tolist()));rows.append({'y':y,'z':z,'surfaceXs':xs})
 j['parts'][name]=rows;del m,tri
p=Q/'corridor-sections.json';j['sourceHashes'][str(Path(__file__))]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();p.write_text(json.dumps(j,indent=2)+'\n');print(str(p))
