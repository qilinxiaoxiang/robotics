from pathlib import Path
import json,numpy as np,trimesh,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
out=Path(__file__).resolve().parent
d=np.load('/tmp/microduck-hardware-inspection/mesh-12.npz');m=trimesh.Trimesh(d['vertices'],d['faces'],process=True)
centers=[(-28.499,18.365),(-28.499,-18.365),(8.2,18.365),(8.2,-18.365)]
# All projected triangles are tested for overlap with X-directed rays.
t=m.triangles;tri2=t[:,:,1:];a=tri2[:,0];b=tri2[:,1];c=tri2[:,2];den=(b[:,1]-c[:,1])*(a[:,0]-c[:,0])+(c[:,0]-b[:,0])*(a[:,1]-c[:,1]);valid=np.abs(den)>1e-12

def blocked(y,z):
 aa=a[valid];bb=b[valid];cc=c[valid];dd=den[valid]
 u=((bb[:,1]-cc[:,1])*(y-cc[:,0])+(cc[:,0]-bb[:,0])*(z-cc[:,1]))/dd
 v=((cc[:,1]-aa[:,1])*(y-cc[:,0])+(aa[:,0]-cc[:,0])*(z-cc[:,1]))/dd
 w=1-u-v
 return int(np.sum((u>=-1e-9)&(v>=-1e-9)&(w>=-1e-9)))
rows=[]
for y,z in centers:
 counts=[blocked(y+dy,z+dz) for dy in np.linspace(-2.4,2.4,11) for dz in np.linspace(-.75,.75,7)]
 rows.append({'center_yz':[y,z],'candidate_strap_cross_section_mm':[4.8,1.5],'rays_tested':len(counts),'blocked_ray_count':sum(c>0 for c in counts)})
print(json.dumps(rows,indent=2));(out/'strap-slot-ray-check.json').write_text(json.dumps(rows,indent=2))
sec=m.section(plane_origin=[1,0,0],plane_normal=[1,0,0]);fig,ax=plt.subplots(figsize=(9,9))
for loop in sec.discrete:ax.plot(loop[:,1],loop[:,2],color='#667885',lw=1)
for idx,(y,z) in enumerate(centers,1):
 ax.add_patch(Rectangle((y-2.4,z-.75),4.8,1.5,color='#db6c40'))
 ax.annotate(f'S{idx}\nY={y:.3f}, Z={z:.3f}',(y,z),xytext=(y-8 if y<0 else y+4,z+10 if z>0 else z-12),arrowprops={'arrowstyle':'->'},fontsize=9,ha='center')
ax.add_patch(Rectangle((-41.65,-17),63,34,fill=False,edgecolor='#447e45',linestyle='--',lw=1.5))
ax.text(-10.15,0,'63 x 34 mm battery footprint\nshown only in projection\nX placement NOT verified',ha='center',fontsize=10,color='#326633')
ax.set_title('Current community 3MF: object 12 / a.obj\nX=1 mm section; coordinates in original object frame')
ax.set_xlabel('Y [mm]');ax.set_ylabel('Z [mm]');ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlim(-55,55);ax.set_ylim(-42,42)
fig.tight_layout();fig.savefig(out/'object12-strap-interface.png',dpi=180)
