from pathlib import Path
import json,numpy as np,trimesh
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent;M=D.parent;O=M.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
fig,axs=plt.subplots(1,3,figsize=(15,6))
for ax,Y in zip(axs,[-67,-67.8,-68.5]):
 for key,col in [('right_thigh','orange'),('motor2','gray'),('motor3','slategray')]:
  ob=json.loads((O/f'{key}.json').read_text());m=trimesh.load_mesh(ob['file']);m.apply_translation(ob.get('importTranslationMm',[0,0,0]));s=m.section([0,1,0],[0,Y,0])
  if s:
   for l in s.discrete:ax.plot(l[:,0],l[:,2],color=col,lw=1)
 ax.set(xlim=(-48,20),ylim=(-58,0),title=f'Y={Y} section');ax.set_aspect('equal');ax.grid()
fig.savefig(D/'thigh-sections.png',dpi=160)
