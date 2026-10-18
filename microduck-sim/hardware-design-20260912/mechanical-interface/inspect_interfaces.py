from pathlib import Path
import numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.collections import PolyCollection
src=Path('/tmp/microduck-hardware-inspection')
out=Path(__file__).resolve().parent
ids=[40,42,12,72,74]
fig,axs=plt.subplots(len(ids),3,figsize=(15,22))
for ri,i in enumerate(ids):
 d=np.load(src/f'mesh-{i}.npz');v=d['vertices'];f=d['faces'];m=trimesh.Trimesh(v,f,process=True)
 print(i, 'watertight',m.is_watertight,'volume',m.volume,'bounds',m.bounds.tolist())
 for ci,(a,b) in enumerate([(0,2),(1,2),(0,1)]):
  ax=axs[ri,ci];xy=v[:,[a,b]];tri=xy[f]
  ax.add_collection(PolyCollection(tri,facecolor='#a7c8de',edgecolor='#7993a5',linewidth=.035))
  ax.set_xlim(xy[:,0].min()-3,xy[:,0].max()+3);ax.set_ylim(xy[:,1].min()-3,xy[:,1].max()+3);ax.set_aspect('equal');ax.set_title(f'ID {i}, {"XYZ"[a]} vs {"XYZ"[b]} mm');ax.grid(alpha=.3)
fig.tight_layout();fig.savefig(out/'orthographic-projections.png',dpi=160)
