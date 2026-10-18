from context import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
parts,hashes=inventory();fig,axs=plt.subplots(2,3,figsize=(15,10))
for p in parts:
 m=trimesh.load_mesh(p['file']);m.apply_transform(p['worldTransform'])
 for ax,z in zip(axs.flat,[55,70,85,95,100,110]):
  if m.bounds[0,2]>z or m.bounds[1,2]<z:continue
  s=m.section([0,0,1],[0,0,z])
  if s is not None:
   for line in s.discrete:ax.plot(line[:,0],line[:,1],color='#446688'if p['key'].startswith('motor')else'#777777',linewidth=.65)
for ax,z in zip(axs.flat,[55,70,85,95,100,110]):
 ax.set(xlim=(-25,45),ylim=(-42,42),title=f'Z={z}mm',aspect='equal');ax.grid(alpha=.2)
 ax.plot([6,6,6],[-7.6,-3.8,1],'ro',markersize=3);ax.plot([17.9,20.7,23,24.45,25.55,26.65,27.75],[12]*7,'go',markersize=3)
fig.tight_layout();fig.savefig(D/'neck-sections.png',dpi=140);print('sections')
