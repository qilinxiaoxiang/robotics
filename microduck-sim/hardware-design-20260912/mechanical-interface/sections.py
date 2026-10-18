from pathlib import Path
import numpy as np,trimesh,matplotlib,json
matplotlib.use('Agg');import matplotlib.pyplot as plt
src=Path('/tmp/microduck-hardware-inspection');out=Path(__file__).resolve().parent
planes={12:(0,[-2,-1,0,1,3,6]),40:(1,[-1,0,1]),42:(1,[-3,0,3]),72:(2,[8.1,10.1,11,12,13]),74:(2,[-13,-12,-11,-10.1,-8.1])}
info={}
for id,(ax,coords) in planes.items():
 d=np.load(src/f'mesh-{id}.npz');m=trimesh.Trimesh(d['vertices'],d['faces'],process=True);other=[a for a in range(3) if a!=ax]
 fig,axes=plt.subplots(1,len(coords),figsize=(5*len(coords),6));axes=np.atleast_1d(axes);info[id]={}
 for axis,coord in zip(axes,coords):
  normal=np.eye(3)[ax];origin=np.zeros(3);origin[ax]=coord;sec=m.section(plane_origin=origin,plane_normal=normal);loops=sec.discrete if sec else []
  info[id][coord]=[]
  for j,loop in enumerate(loops):
   points=loop[:,other];axis.plot(*points.T,lw=.8);center=(points.max(0)+points.min(0))/2
   axis.text(*center,str(j),fontsize=7);bbox=np.stack([points.min(0),points.max(0)]);info[id][coord].append({'loop':j,'min':bbox[0].tolist(),'max':bbox[1].tolist(),'center':center.tolist(),'extent':(bbox[1]-bbox[0]).tolist()})
  axis.set_aspect('equal');axis.grid(alpha=.3);axis.set_title(f'ID {id} {"XYZ"[ax]}={coord} mm');axis.set_xlabel('XYZ'[other[0]]);axis.set_ylabel('XYZ'[other[1]])
 fig.tight_layout();fig.savefig(out/f'sections-{id}.png',dpi=160)
(out/'section-loops.json').write_text(json.dumps(info,indent=2))
