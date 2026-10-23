"""Place the ROBOTIS U20CAM model (OMX-F STEP) in the head: lens along +x on the eye axis, plug edge to +y. Two board positions:
A = lens front flush with the trim front design value (x 89.0), B = board front where V1.30 puts it (x 73.6). Min distance to head parts."""
import json, numpy as np, trimesh, os
B='/private/tmp/claude-501/-Users-xiangzheng-code-robotics/af2b4ebd-4f58-4a8c-aad9-7f6bf8357bec/scratchpad/omxf-step/'
C='/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache'
W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
ck=json.load(open('checks.json')); AY,AZ=ck['axis']['used']
cam=trimesh.load(B+'u20cam-local.stl')
parts={}
for n in ['head_bottom','jaw_frame','amplifier','speaker','face_panel','eye_trim','head_cap']:
    parts[n]=trimesh.load(W+n+'.stl',force='mesh')
for n in ['jaw_support','head_yaw_link','motor15','motor13','motor14','touch_pad_l1','touch_pad_l2','touch_xiao','motor11','motor12']:
    if os.path.exists(f'{C}/solid-{n}.npz'):
        z=np.load(f'{C}/solid-{n}.npz'); parts[n]=trimesh.Trimesh(z['v'],z['f'],process=False)
res={}
for name,x0 in (('A_flush',89.0+(-14.62)), ('B_v130_board',73.6+7.38)):
    T=np.array([[0,0,-1,x0],[0,1,0,AY],[1,0,0,AZ],[0,0,0,1.]]); c=cam.copy(); c.apply_transform(T)
    pts=trimesh.sample.sample_surface_even(c,6000,seed=1)[0]; pts=np.vstack([pts,c.vertices])
    out={}
    for n,m in parts.items():
        near=pts[np.all((pts>m.bounds[0]-8)&(pts<m.bounds[1]+8),axis=1)]
        if not len(near): out[n]='>8'; continue
        d=np.concatenate([trimesh.proximity.closest_point(m,near[i:i+100])[1] for i in range(0,len(near),100)])
        ins=int(m.contains(near).sum()) if m.is_watertight else None
        out[n]=dict(minMm=round(float(d.min()),2), pointsInside=ins)
    res[name]=dict(boardFrontX=round(x0+7.38,2), boardBackX=round(x0-8.98,2), plugBackX=round(x0-13.98,2), lensFrontX=round(x0+14.62,2), bounds=c.bounds.round(2).tolist(), minDist=out)
    c.export(B+f'u20cam-world-{name}.stl')
print(json.dumps(res,indent=1))
json.dump(res,open(B+'real_cam_fit.json','w'),indent=1)
