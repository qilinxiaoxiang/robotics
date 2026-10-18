from assembly_fk import *
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
obs=world_meshes();fig,axs=plt.subplots(2,2,figsize=(12,12))
for ax,z in zip(axs.ravel(),[-30.821742,5.877258,27.5,-36.5]):
 for g,m in obs:
  if g['mesh']=='np_f970':continue
  sec=m.section([0,0,1],[0,0,z])
  if sec:
   for p in sec.discrete:ax.plot(p[:,0],p[:,1],color='green' if g['mesh']=='power_support' else 'gray',lw=.8)
 from matplotlib.patches import Rectangle
 ax.add_patch(Rectangle((-48.6,-17),22,34,color='gold',alpha=.5));ax.set(xlim=(-55,-12),ylim=(-31,31),title=f'body Z {z}',xlabel='body X',ylabel='body Y',aspect='equal');ax.grid()
fig.savefig(Path(__file__).with_name('battery-cross-sections.png'),dpi=140)
