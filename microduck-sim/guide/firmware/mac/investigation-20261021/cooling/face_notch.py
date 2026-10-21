"""Eye-hole profile of the V1.8 face, the A7Z face and the community face; eye-trim bore vs the 13M 214 lens holder."""
import numpy as np, trimesh, json, sys
W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
F='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/face-a7z/'
C='/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/assembly/print-parts/'
AX=(-0.09,131.11)  # lens axis y,z (face README)
def profile(mesh, x, n=360, rmax=30):
    """radius of the first material hit from the axis outward at plane x, per angle (ray cast in the plane)."""
    ang=np.linspace(0,2*np.pi,n,endpoint=False)
    o=np.tile([x,AX[0],AX[1]],(n,1)).astype(float)
    d=np.column_stack([np.zeros(n),np.cos(ang),np.sin(ang)])
    loc,ri,_=mesh.ray.intersects_location(o,d,multiple_hits=False)
    r=np.full(n,np.nan)
    for p,i in zip(loc,ri): r[i]=np.hypot(p[1]-AX[0],p[2]-AX[1])
    return ang,r
out={}
for name,path in (('face_v18',W+'face_panel-v18.stl'),('face_a7z',F+'face_panel_a7z.stl'),('community_84',C+'community-84.stl')):
    try: m=trimesh.load(path)
    except Exception as e: print(name,'ERR',e); continue
    print(name,'bounds x',m.bounds[:,0].round(1),'y',m.bounds[:,1].round(1),'z',m.bounds[:,2].round(1))
    xs=np.arange(m.bounds[0,0]+0.2, m.bounds[1,0]-0.1, 0.4)
    rec=[]
    for x in xs:
        ang,r=profile(m,x)
        ok=~np.isnan(r)
        if ok.sum()<10: continue
        rmin,rmax_=np.nanmin(r),np.nanmax(r)
        # notches = angular spans where r exceeds the median by >0.5 mm
        med=np.nanmedian(r); big=(r>med+0.5)&ok
        # count contiguous spans
        spans=[]; 
        b=np.r_[big,big[0]]
        i=0; n=len(big)
        starts=[k for k in range(n) if big[k] and not big[k-1]]
        for s in starts:
            e=s
            while big[(e+1)%n]: e+=1
            spans.append((round(np.degrees(ang[s]),0), round(np.degrees(ang[e%n]),0), round(float(np.nanmax(r[[k%n for k in range(s,e+1)]])),2)))
        rec.append({'x':round(float(x),2),'r_med':round(float(med),2),'r_min':round(float(rmin),2),'r_max':round(float(rmax_),2),'notches':spans})
    out[name]=rec
    for r_ in rec: print(f"  x {r_['x']:5.1f} r_med {r_['r_med']:5.2f} min {r_['r_min']:5.2f} max {r_['r_max']:5.2f} notches {r_['notches']}")
# eye trim bore and the lens holder
trim=trimesh.load(W+'eye_trim.stl'); cam=trimesh.load(F+'camera_13m214.stl')
print('trim bounds',trim.bounds.round(1).tolist())
rec=[]
for x in np.arange(trim.bounds[0,0]+0.2, trim.bounds[1,0]-0.1, 0.5):
    ang,r=profile(trim,x); 
    if np.isnan(r).sum()>300: continue
    rec.append((round(float(x),1), round(float(np.nanmin(r)),2), round(float(np.nanmedian(r)),2), round(float(np.nanmax(r)),2)))
print('trim bore per x (x, rmin, rmed, rmax):', rec)
out['trim_bore']=rec
# lens holder: the camera model's part between x 77.8 and 84.2 near the axis
sl=cam.slice_plane([80.5,0,0],[1,0,0]) if False else None
# use vertices of the camera mesh within x>77.8 and near the axis
v=cam.vertices; sel=v[(v[:,0]>78.0)&(np.hypot(v[:,1]-AX[0],v[:,2]-AX[1])<8)]
print('lens holder vertices near axis: x', sel[:,0].min().round(2), sel[:,0].max().round(2), 'y', sel[:,1].min().round(2), sel[:,1].max().round(2), 'z', sel[:,2].min().round(2), sel[:,2].max().round(2))
half=max(abs(sel[:,1]-AX[0]).max(), abs(sel[:,2]-AX[1]).max()); print('holder half-width', round(float(half),2), 'half-diagonal', round(float(half*2**0.5),2))
d=trimesh.proximity.closest_point(trim, sel)[1]; print('min distance holder vertices -> trim', round(float(d.min()),2))
json.dump(out,open(sys.argv[1],'w'),indent=1)
