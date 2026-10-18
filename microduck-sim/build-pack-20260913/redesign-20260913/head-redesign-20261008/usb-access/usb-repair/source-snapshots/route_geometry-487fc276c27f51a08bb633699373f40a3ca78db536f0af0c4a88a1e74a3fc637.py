"""Exact radius fillets and explicit arclength for the USB repack.
No spline is accepted merely because its sampled points are collision-free.
"""
import numpy as np
import trimesh

def unit(v):
 v=np.array(v,float);n=np.linalg.norm(v)
 if n<1e-9:raise ValueError('zero direction')
 return v/n

def circular_arc(start,incoming,outgoing,radius,step=.25):
 a,b=unit(incoming),unit(outgoing);angle=np.arccos(np.clip(a@b,-1,1))
 if angle<1e-8:return np.array([start],float),0.
 if np.pi-angle<1e-6:raise ValueError('180 degree corner needs an explicit loop plane')
 axis=unit(np.cross(a,b));center=np.asarray(start,float)+np.cross(axis,a)*radius;v=start-center
 theta=np.linspace(0,angle,int(np.ceil(radius*angle/step))+1)
 points=np.array([center+v*np.cos(t)+np.cross(axis,v)*np.sin(t) for t in theta])
 return points,float(radius*angle)

def fillet_polyline(waypoints,radius,step=.25):
 w=np.array(waypoints,float);w=w[np.r_[True,np.linalg.norm(np.diff(w,axis=0),axis=1)>1e-7]]
 if len(w)<2:raise ValueError('route needs two distinct endpoints')
 # Remove only codirectional points; never hide a reversing cusp.
 clean=[w[0]]
 for i in range(1,len(w)-1):
  a,b=unit(w[i]-clean[-1]),unit(w[i+1]-w[i])
  if np.dot(a,b)>1-1e-8:continue
  clean.append(w[i])
 clean.append(w[-1]);w=np.array(clean);cuts=[]
 for i in range(1,len(w)-1):
  a,b=unit(w[i]-w[i-1]),unit(w[i+1]-w[i]);angle=np.arccos(np.clip(a@b,-1,1))
  if np.pi-angle<1e-6:raise ValueError('cusp')
  d=radius*np.tan(angle/2);cuts.append((w[i]-a*d,w[i]+b*d,a,b,d))
 for i in range(len(w)-1):
  need=(cuts[i-1][4] if i else 0)+(cuts[i][4] if i<len(cuts) else 0)
  if np.linalg.norm(w[i+1]-w[i])<need-1e-7:raise ValueError('overlapping bend-radius fillets')
 out=[w[0]];length=0.;prev=w[0]
 for start,end,a,b,_ in cuts:
  n=np.linalg.norm(start-prev)
  if n>1e-7:out.extend(np.linspace(prev,start,int(np.ceil(n/step))+1)[1:])
  arc,le=circular_arc(start,a,b,radius,step);out.extend(arc[1:]);length+=n+le;prev=end
 n=np.linalg.norm(w[-1]-prev)
 if n>1e-7:out.extend(np.linspace(prev,w[-1],int(np.ceil(n/step))+1)[1:])
 return np.array(out),float(length+n)

def tube(points,diameter,facets=24,start_tangent=None,end_tangent=None):
 p=np.array(points,float);p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-7]]
 t=np.gradient(p,axis=0);t/=np.linalg.norm(t,axis=1)[:,None]
 # Endpoint secants tilt a ring into its connector when a bend begins there.
 # Use the analytic route tangent for the mating plane, never trim the cable.
 if start_tangent is not None:t[0]=unit(start_tangent)
 if end_tangent is not None:t[-1]=unit(end_tangent)
 verts=[];prev=None
 for pt,tt in zip(p,t):
  a=np.array([1.,0,0]) if prev is None else prev.copy();a-=tt*(a@tt)
  if np.linalg.norm(a)<1e-6:a=np.cross(tt,[0,1,0])
  a=unit(a);b=np.cross(tt,a);prev=a
  verts.extend([pt+diameter/2*(a*np.cos(q)+b*np.sin(q)) for q in np.linspace(0,2*np.pi,facets,endpoint=False)])
 faces=[]
 for i in range(len(p)-1):
  for j in range(facets):
   a=i*facets+j;b=i*facets+(j+1)%facets;faces.extend([[a,b,b+facets],[a,b+facets,a+facets]])
 verts.extend([p[0],p[-1]]);start,end=len(verts)-2,len(verts)-1
 for j in range(facets):faces.extend([[start,(j+1)%facets,j],[end,(len(p)-1)*facets+j,(len(p)-1)*facets+(j+1)%facets]])
 m=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(m)
 if not m.is_watertight:raise ValueError('open tube')
 return m

if __name__=='__main__':
 # A physical radius10 quarter turn has exact length 5pi+20, not the polyline40.
 p,l=fillet_polyline([[0,0,0],[20,0,0],[20,20,0]],10)
 assert abs(l-(20+5*np.pi))<1e-9 and np.max(np.linalg.norm(np.diff(p,axis=0),axis=1))<=.250001
 assert tube(p,4.5).is_watertight
 try:fillet_polyline([[0,0,0],[5,0,0],[5,5,0]],10)
 except ValueError:pass
 else:raise AssertionError('impossible bend accepted')
 try:fillet_polyline([[0,0,0],[10,0,0],[0,0,0]],10)
 except ValueError:pass
 else:raise AssertionError('cusp accepted')
 print('exact arclength, sampling, tube and two original failure controls passed')
