from check_local import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=json.loads((D/'head-bottom-clearance-report.json').read_text());m=load(r['source']);n=trimesh.load_mesh(r['output']['file'],process=True)
fig,axs=plt.subplots(1,2,figsize=(12,6))
for ax,y in zip(axs,[-9,-14]):
 for mesh,color,label in [(m,'black','Original'),(n,'red','Internal relief')]:
  q=mesh.section(plane_origin=[0,y,0],plane_normal=[0,1,0])
  for i,p in enumerate(q.discrete):ax.plot(p[:,0],p[:,2],color=color,lw=1,label=label if i==0 else None)
 ax.set_xlim(-22,-4);ax.set_ylim(97,111);ax.set_aspect('equal');ax.grid(True);ax.set_title(f'World Y={y} mm');ax.legend()
fig.tight_layout();fig.savefig(D/'head-bottom-clearance-sections.png',dpi=140)
