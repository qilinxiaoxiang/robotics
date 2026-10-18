"""External wire starts at the actual connector exit plane, with analytic tangent.
Circumscribed sections and sag allowance match existing conservative route meshing.
"""
import bounded_amp_check as c
def tube_with_start_tangent(points,r,start_tangent):
 np=c.np; raw=np.array(points);keep=[0]
 for i in range(1,len(raw)-1):
  u=raw[i]-raw[i-1];v=raw[i+1]-raw[i]
  if np.linalg.norm(np.cross(u,v))>1e-9:keep.append(i)
 keep.append(len(raw)-1);pts=raw[keep];ts=np.diff(pts,axis=0);ts/=np.linalg.norm(ts,axis=1)[:,None]
 tangent=np.vstack([ts[0],ts[:-1]+ts[1:],ts[-1]]);tangent/=np.linalg.norm(tangent,axis=1)[:,None]
 tangent[0]=np.asarray(start_tangent,dtype=float);tangent[0]/=np.linalg.norm(tangent[0])
 side=np.cross(tangent[0],[1,0,0] if abs(tangent[0,0])<.9 else [0,1,0]);side/=np.linalg.norm(side)
 verts=[];faces=[];n=16
 # Circumscribed16-gon plus0.005mm covers <=.25mm/R3 arc sag and ring rotation.
 r=(r+.005)/np.cos(np.pi/n)
 for p,t in zip(pts,tangent):
  side-=np.dot(side,t)*t;side/=np.linalg.norm(side);other=np.cross(t,side)
  for j in range(n):
   a=j*2*np.pi/n;verts.append(p+r*(np.cos(a)*side+np.sin(a)*other))
 for i in range(len(pts)-1):
  for j in range(n):
   a=i*n+j;bb=i*n+(j+1)%n;dd=a+n;cc=bb+n;faces.extend([[a,bb,cc],[a,cc,dd]])
 for j in range(1,n-1):faces.append([0,j+1,j]);a=(len(pts)-1)*n;faces.append([a,a+j,a+j+1])
 m=c.tm.Trimesh(verts,faces,process=True)
 if m.volume<0:m.invert()
 assert m.is_watertight
 s=c.mf.Manifold(c.mf.Mesh64(c.np.asarray(m.vertices,c.np.float64),c.np.asarray(m.faces,c.np.uint64)));assert s.status()==c.mf.Error.NoError
 return s
