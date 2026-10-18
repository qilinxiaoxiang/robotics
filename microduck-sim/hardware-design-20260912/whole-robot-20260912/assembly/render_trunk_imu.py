from assembly_fk import *
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
O=Path(__file__).parent/'trunk-imu';C=O.parent/'compact-battery';scene=trimesh.Scene();parts=[]
for name,color,a in [('imu_clamp_holder_body.stl','#139e98',.85),('imu_rear_cover_body.stl','#16847f',.7),('imu_28x25x8_envelope_body.stl','#af58cc',.4)]:parts.append((name,trimesh.load(O/name),color,a))
for name,color,a in [('power-support-integrated-body.stl','#e2af3b',.4),('battery-max-envelope-body.stl','#7c7c7c',.2)]:parts.append((name,trimesh.load(C/name),color,a))
fig=plt.figure(figsize=(15,9))
for i,(az,el) in enumerate([(135,20),(205,20)],1):
 ax=fig.add_subplot(1,2,i,projection='3d')
 for n,m,c,a in parts:
  ax.add_collection3d(Poly3DCollection(m.triangles,facecolor=c,alpha=a,edgecolor='none'))
 ax.set(xlim=(-66,-18),ylim=(-29,29),zlim=(-42,40),xlabel='body X mm',ylabel='body Y mm',zlabel='body Z mm');ax.set_box_aspect((48,58,82));ax.view_init(el,az)
fig.tight_layout();fig.savefig(O/'imu-clamp-assembly.png',dpi=140)
for n,m,c,a in parts:m.visual.face_colors=matplotlib.colors.to_rgba(c,a);scene.add_geometry(m,geom_name=n)
scene.export(O/'imu-clamp-assembly.glb')
