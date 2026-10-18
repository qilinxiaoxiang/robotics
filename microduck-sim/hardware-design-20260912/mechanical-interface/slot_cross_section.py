from pathlib import Path
import numpy as np,trimesh,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
src=Path('/tmp/microduck-hardware-inspection');out=Path(__file__).resolve().parent
d=np.load(src/'mesh-12.npz');m=trimesh.Trimesh(d['vertices'],d['faces'],process=True)
fig,axs=plt.subplots(1,3,figsize=(12,8))
for ax,y in zip(axs,[-28.5,8.2,0]):
 sec=m.section(plane_origin=[0,y,0],plane_normal=[0,1,0])
 for j,l in enumerate(sec.discrete):
  ax.plot(l[:,0],l[:,2],lw=1.2);mid=(l.max(0)+l.min(0))/2;ax.text(mid[0],mid[2],str(j),fontsize=9)
 ax.set_aspect('equal');ax.grid(alpha=.3);ax.set_title(f'12 / a.obj: Y={y} mm');ax.set_xlabel('X');ax.set_ylabel('Z')
fig.tight_layout();fig.savefig(out/'slot-cross-section.png',dpi=160)
