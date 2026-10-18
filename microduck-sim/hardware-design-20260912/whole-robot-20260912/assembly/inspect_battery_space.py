from assembly_fk import *
import json
from pathlib import Path
out=Path(__file__).parent
_,gs=fk();obs=[];records=[]
for g,m in world_meshes():
 records.append({'body':g['body'],'mesh':g['mesh'],'bounds':m.bounds.tolist(),'watertight':m.is_watertight,'volume':m.volume})
 if g['body']=='trunk_base' or g['body'] in ['neck','yaw_roll_motion']:obs.append((g,m))
(out/'zero-pose-geometries.json').write_text(json.dumps(records,indent=2))
npgeom=next(g for g in gs if g['mesh']=='np_f970');T=npgeom['world'];print('battery transform',T)
for g,m in obs:print(g['body'],g['mesh'],np.round(m.bounds,2).tolist(),'volume',round(m.volume,2),'wt',m.is_watertight)
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
fig=plt.figure(figsize=(16,10))
for i,(az,el) in enumerate([(0,0),(90,0),(35,20)],1):
 ax=fig.add_subplot(1,3,i,projection='3d')
 for g,m in obs:
  color='gold' if g['mesh']=='np_f970' else ('green' if g['mesh']=='power_support' else 'gray')
  c=Poly3DCollection(m.triangles[::max(1,len(m.faces)//7000)],alpha=.55 if color!='gray' else .14,facecolor=color,edgecolor='none');ax.add_collection3d(c)
 ax.set(xlim=(-60,40),ylim=(-60,60),zlim=(-55,75),xlabel='body X',ylabel='body Y',zlabel='body Z');ax.set_box_aspect((100,120,130));ax.view_init(el,az)
fig.tight_layout();fig.savefig(out/'battery-original-area.png',dpi=130)
