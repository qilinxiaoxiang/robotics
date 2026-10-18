import os,json
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import trimesh as tm,numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent;m=tm.load(D/'j4-native.stl',force='mesh');fig,axs=plt.subplots(1,4,figsize=(12,5));out=[]
for ax,y in zip(axs,[-33.5,-33.3,-32.9,-31.5]):
 s=m.section(plane_origin=[0,y,0],plane_normal=[0,1,0]);rows=[]
 for q in s.discrete:
  ax.plot(q[:,0],q[:,2]);rows.append(q.tolist())
 ax.set_title(f'native Y={y}');ax.set_aspect('equal');out.append({'y':y,'loops':rows})
fig.savefig(D/'j4-cross-sections.png',dpi=160);(D/'sections.json').write_text(json.dumps(out))
