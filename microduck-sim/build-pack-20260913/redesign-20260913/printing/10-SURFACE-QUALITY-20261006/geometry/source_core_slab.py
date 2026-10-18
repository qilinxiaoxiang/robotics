"""Exact source-triangle distance from a finite axial bore slab.

Every intersecting triangle is clipped to both axial planes, then its projected
convex polygon is tested against the core centre. Source-boundary distance is a
certificate for an already measured void at the centre; no axial interpolation.
"""
import numpy as np

def source_slab_boundary_radius(mesh,center,axis,halfwindow):
    axis=np.array(axis,float);axis/=np.linalg.norm(axis)
    x=np.cross(axis,[1,0,0] if abs(axis[0])<.8 else [0,1,0]);x/=np.linalg.norm(x);y=np.cross(axis,x)
    coordinates=(mesh.vertices-center)@np.array([x,y,axis]).T
    triangles=coordinates[mesh.faces]
    possible=(triangles[:,:,2].min(axis=1)<=halfwindow+1e-9)&(triangles[:,:,2].max(axis=1)>=-halfwindow-1e-9)
    closest=float('inf');closest_face=None
    for face,triangle in zip(np.flatnonzero(possible),triangles[possible]):
        polygon=[v for v in triangle]
        for sign in [1,-1]:
            clipped=[]
            if not polygon:break
            for first,last in zip(polygon,polygon[1:]+polygon[:1]):
                f=sign*first[2]-halfwindow;l=sign*last[2]-halfwindow
                if f<=1e-10:clipped.append(first)
                if (f<0<l) or (l<0<f):clipped.append(first+(last-first)*f/(f-l))
            polygon=clipped
        if len(polygon)<2:continue
        xy=np.array(polygon)[:,:2];last=np.roll(xy,-1,axis=0);step=last-xy
        signed=xy[:,0]*last[:,1]-xy[:,1]*last[:,0]
        area=sum(signed)
        contains=(len(xy)>=3 and abs(area)>1e-12 and (np.all(signed>=-1e-10) or np.all(signed<=1e-10)))
        if contains:distance=0.0
        else:
            den=np.sum(step*step,axis=1);t=np.divide(-np.sum(xy*step,axis=1),den,out=np.zeros(len(den)),where=den>1e-15);t=np.clip(t,0,1)
            distance=float(np.linalg.norm(xy+t[:,None]*step,axis=1).min())
        if distance<closest:closest=distance;closest_face=int(face)
    return dict(minimum_source_boundary_radius_mm=closest,nearest_source_triangle_index=closest_face,
                axial_half_window_mm=halfwindow,method='All source triangles clipped to axial slab; exact closest distance of each projected convex polygon to core axis. Centre section independently verified as an interior cavity.')
