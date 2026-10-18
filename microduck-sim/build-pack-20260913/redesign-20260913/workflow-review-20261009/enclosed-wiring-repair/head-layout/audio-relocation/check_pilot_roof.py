import os,json,hashlib
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import trimesh as tm,numpy as np
O=Path(__file__).resolve().parent;D=O.parent;p=D/'native-cap-registered-world.stl';m=tm.load(p,force='mesh');assert m.is_watertight
rows=[]
def disk_min(t,c,r):
 a,b,d=t;M=np.column_stack((b[:2]-a[:2],d[:2]-a[:2]));det=np.linalg.det(M)
 if abs(det)<1e-10:return []
 inv=np.linalg.inv(M)
 def inside(v):
  u=inv@(v-a[:2]);return min(u)>=-1e-8 and sum(u)<=1+1e-8
 grad=np.linalg.solve(M.T,np.array([b[2]-a[2],d[2]-a[2]]));pts=[q[:2] for q in t if np.linalg.norm(q[:2]-c)<=r+1e-8]
 if np.linalg.norm(grad)>1e-12:
  q=c-r*grad/np.linalg.norm(grad)
  if inside(q):pts.append(q)
 for v,w in zip(t,np.roll(t,-1,axis=0)):
  e=w[:2]-v[:2];u=v[:2]-c;aa=e@e;bb=2*(u@e);cc=u@u-r*r;disc=bb*bb-4*aa*cc
  if aa<1e-14 or disc<0:continue
  for frac in [(-bb-disc**.5)/(2*aa),(-bb+disc**.5)/(2*aa)]:
   if -1e-9<=frac<=1+1e-9:pts.append(v[:2]+frac*e)
 return [float(a[2]+grad@(q-a[:2]))for q in pts]

def clip(poly,axis,limit,keepabove):
 out=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ia=a[axis]>=limit if keepabove else a[axis]<=limit;ib=b[axis]>=limit if keepabove else b[axis]<=limit
  if ia:out.append(a)
  if ia!=ib:out.append(a+(b-a)*(limit-a[axis])/(b[axis]-a[axis]))
 return out
for name,x,y,z,depth,eng in [('amp0',13.287000885,-12.3499993896,135.5849994,7.2,6.43),('amp1',13.287000885,.3500006104,135.5849994,7.2,6.43),('speaker0',-16,7,133.45,3.6,2.99),('speaker1',-16,17,133.45,3.6,2.99)]:
 zs=[];ds=[]
 for t,n in zip(m.triangles,m.face_normals):
  if n[2]<=.1 or t[:,2].max()<z:continue
  poly=list(t)
  for a,l,k in [(0,x-1.05,True),(0,x+1.05,False),(1,y-1.05,True),(1,y+1.05,False)]:
   poly=clip(poly,a,l,k)
   if not poly:break
  if poly:
   zs.extend(float(v[2]) for v in poly);ds.extend(disk_min(t,np.array([x,y]),1.05))
 assert zs
 row={'id':name,'xyMm':[x,y],'seatZMm':z,'pilotDiameterMm':2.1,'pilotDepthMm':depth,'engagementMm':eng,'tipGapMm':depth-eng,'conservativeOuterRoofMinZMm':min(zs),'remainingClosedRoofAxialMaterialLowerBoundMm':min(zs)-z-depth,'exactBoreDiskOuterRoofMinZMm':min(ds),'exactBoreDiskRemainingRoofMm':min(ds)-z-depth,'method':'Minimum of exact upward native-cap triangle planes clipped to pilot bounding square; conservative over bore disk.'};rows.append(row)
out={'source':str(p),'sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':rows};(O/'pilot-roof-precheck.json').write_text(json.dumps(out,indent=2));print(json.dumps(rows,indent=2))
