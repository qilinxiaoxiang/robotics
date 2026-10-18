from pathlib import Path
import json,numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).parent;O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
fig,axs=plt.subplots(2,3,figsize=(13,8))
for ax,y in zip(axs.flat,[-7.5,-5,-2.5,0,5,10]):
 for key in ['motor4','motor3','motor2','right_thigh','right_plate','right_hip','right_yaw','right_lower','power_support']:
  r=json.loads((O/(key+'.json')).read_text());m=trimesh.load_mesh(r['file']);m.apply_translation(r.get('importTranslationMm',[0,0,0]));p=m.section([1,0,0],[y,0,0])
  if p:
   for i,line in enumerate(p.discrete):ax.plot(line[:,1],line[:,2],label=key if i==0 else None)
 ax.set(title=f'World X={y} mm',xlim=(-75,-20),ylim=(-55,5),xlabel='Y',ylabel='Z');ax.grid();ax.set_aspect('equal');ax.legend(fontsize=5)
fig.tight_layout();fig.savefig(D/'station-xsections.png',dpi=150)
