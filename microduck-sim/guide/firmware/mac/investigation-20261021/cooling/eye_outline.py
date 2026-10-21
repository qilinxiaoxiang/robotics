import numpy as np, trimesh
F='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/face-a7z/face_panel_a7z.stl'
W='/Users/xiangzheng/code/robotics/microduck-sim/guide/print/world/'
AX=np.array([-0.09,131.11])
for name,path,xs in (('face_a7z',F,(80.6,81.2)),('face_v18',W+'face_panel-v18.stl',(80.6,)),('eye_trim',W+'eye_trim.stl',(82.5,85.0,88.5))):
    m=trimesh.load(path)
    for x in xs:
        sec=m.section(plane_origin=[x,0,0],plane_normal=[1,0,0])
        best=None
        for loop in sec.discrete:
            yz=loop[:,1:3]-AX; r=np.hypot(yz[:,0],yz[:,1])
            if r.max()<12 and r.min()<9.5:   # the eye hole loop
                best=(loop,r)
        if best is None: print(name,x,'no hole loop'); continue
        loop,r=best; ang=(np.degrees(np.arctan2(loop[:,2]-AX[1],loop[:,1]-AX[0]))+360)%360
        order=np.argsort(ang); ang,r=ang[order],r[order]
        # notch spans where r>7.6
        big=r>7.6
        spans=[]; i=0
        while i<len(r):
            if big[i]:
                j=i
                while j+1<len(r) and big[j+1]: j+=1
                # chord width of the notch at r 7.3 from the angular span
                w=np.radians(ang[j]-ang[i])*7.3
                spans.append((round(ang[i],1),round(ang[j],1),round(r[i:j+1].max(),2),round(float(w),2)))
                i=j+1
            else: i+=1
        print(f'{name} x={x}: hole loop {len(loop)} pts, r min {r.min():.2f} med {np.median(r):.2f} max {r.max():.2f}; notch spans (deg start,end,r_max,width_mm) {spans}')
