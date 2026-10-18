import os,json
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent;H=D.parents[2]/'head-redesign-20261008';cap=tm.load(H/'curved-head/community-curved-head-world.stl',force='mesh');plug=tm.load(H/'usb-access/full-harness/openrb-usb-c-published-envelope-world.stl',force='mesh');plug.apply_translation([10,0,0]);fig,axs=plt.subplots(1,3,figsize=(12,5));rows=[]
for ax,z in zip(axs,[132,140,147]):
 for label,m,col in [('original cap',cap,'black'),('USB-C after +X10',plug,'orange')]:
  s=m.section(plane_normal=[0,0,1],plane_origin=[0,0,z]);curves=[]
  if s:
   for q in s.discrete:ax.plot(q[:,0],q[:,1],color=col,lw=1);curves.append(q.tolist())
  rows.append({'z':z,'part':label,'curvesMm':curves})
 ax.set_aspect('equal');ax.set_xlim(-35,95);ax.set_ylim(-50,50);ax.set_title(f'World Z={z} mm');ax.set_xlabel('X mm');ax.set_ylabel('Y mm')
fig.suptitle('Original closed duck shell (black); seated 27 mm USB-C after +X10 (orange)');fig.tight_layout();fig.savefig(D/'closed-cap-sections.png',dpi=150);(D/'closed-cap-sections.json').write_text(json.dumps(rows))
