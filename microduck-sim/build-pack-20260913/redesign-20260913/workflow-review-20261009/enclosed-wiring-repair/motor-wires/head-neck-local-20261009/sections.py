from check_local import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
plan=json.loads((D/'plan.json').read_text());fig,axs=plt.subplots(2,3,figsize=(15,10));zz=[105,115,125,130,133,136]
for o in plan['obstacles']:
 m=load(o)
 for ax,z in zip(axs.flat,zz):
  if not m.bounds[0,2]<=z<=m.bounds[1,2]:continue
  s=m.section(plane_origin=[0,0,z],plane_normal=[0,0,1])
  if s is None:continue
  c='tab:orange' if 'OpenRB' in o['key'] else 'tab:blue' if 'motor' in o['key'] else 'black'
  for p in s.discrete:ax.plot(p[:,0],p[:,1],c=c,lw=.45)
for ax,z in zip(axs.flat,zz):
 ax.set_title('World Z '+str(z));ax.set_xlim(-38,55);ax.set_ylim(-40,35);ax.set_aspect('equal');ax.grid(True);ax.axvline(6,color='red',lw=.4);ax.axhline(-9,color='red',lw=.4)
fig.tight_layout();fig.savefig(D/'head-sections.png',dpi=130)
