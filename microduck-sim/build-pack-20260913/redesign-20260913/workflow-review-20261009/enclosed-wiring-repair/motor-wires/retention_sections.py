from pathlib import Path
import json,numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).parent;O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
fig,axs=plt.subplots(1,3,figsize=(15,5));out={}
for ax,z in zip(axs,[-20,-30,-40]):
 out[str(z)]={}
 for key in ['motor4','motor3','motor2','right_thigh','right_plate','right_hip','right_lower','power_support']:
  r=json.loads((O/(key+'.json')).read_text());m=trimesh.load_mesh(r['file']);m.apply_translation(r.get('importTranslationMm',[0,0,0]));p=m.section([0,0,1],[0,0,z])
  if p:
   out[str(z)][key]=[line.tolist() for line in p.discrete]
   for i,line in enumerate(p.discrete):ax.plot(line[:,0],line[:,1],label=key if i==0 else None)
 ax.set(title=f'World Z={z} mm',xlim=(-50,25),ylim=(-75,-25),xlabel='X',ylabel='Y');ax.grid();ax.set_aspect('equal');ax.legend(fontsize=5)
fig.tight_layout();fig.savefig(D/'retention-sections.png',dpi=120)
(D/'retention-sections.json').write_text(json.dumps(out))
