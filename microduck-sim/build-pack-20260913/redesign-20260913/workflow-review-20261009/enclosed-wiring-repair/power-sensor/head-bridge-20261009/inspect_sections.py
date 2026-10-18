from pathlib import Path
import json,hashlib
import numpy as np,trimesh
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(__file__).resolve().parent
F=D.parent/'head-controller-study/final-integration-20261009'
p=F/'integrated-rigid-package.json';r=json.loads(p.read_text());fig,axs=plt.subplots(2,3,figsize=(15,10));rows=[]
colors={'fixed':'#555555','controller':'#ac5855','pi':'#1c9855','amp':'#c09900','speaker':'#4466cc','mounts':'#8e66aa','speaker_mounts':'#8e66aa'}
for q in r['parts']:
 m=trimesh.load_mesh(q['file']);m.apply_transform(q['worldTransform']);rows.append({'key':q['key'],'bounds':m.bounds.tolist()})
 for ax,y in zip(axs.flat,[-30,-20,-8,0,15,25]):
  if m.bounds[0,1]>y or m.bounds[1,1]<y:continue
  s=m.section([0,1,0],[0,y,0])
  if s is not None:
   for line in s.discrete:ax.plot(line[:,0],line[:,2],color=colors.get(q['group'],'#cc8800'),linewidth=.8)
for ax,y in zip(axs.flat,[-30,-20,-8,0,15,25]):
 ax.set(xlim=(-15,95),ylim=(95,165),title=f'Y={y} mm',xlabel='X',ylabel='Z',aspect='equal');ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(D/'head-sections.png',dpi=140);(D/'head-bounds.json').write_text(json.dumps({'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'parts':rows},indent=2));print('sections',len(rows))
