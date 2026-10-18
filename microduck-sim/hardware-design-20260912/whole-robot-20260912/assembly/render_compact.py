from assembly_fk import *
import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
O=Path(__file__).parent/'compact-battery';scene=trimesh.Scene();items=[]
for g,m in world_meshes():
 if g['mesh'] in ['np_f970','power_support']:continue
 items.append((g['body']+'/'+g['mesh'],m,'gray',.1 if g['body']=='jaw_soft' else .2))
for file,color in [('power-support-integrated-body.stl','#1f9d74'),('battery-max-envelope-body.stl','#f5b52d'),('large_regulator-envelope-body.stl','#3265cc'),('small_regulator-envelope-body.stl','#bd4876'),('small-regulator-cover-body.stl','#b64371'),('two-retention-ties-envelope.stl','#222222')]:
 if (O/file).exists():items.append((file,trimesh.load(O/file),color,.8))
for n,m,c,a in items:
 m.visual.face_colors=matplotlib.colors.to_rgba(c,a);scene.add_geometry(m,geom_name=n,node_name=n)
scene.export(O/'whole-robot-compact-zero-pose.glb')
fig=plt.figure(figsize=(17,9))
for i,(az,el) in enumerate([(90,0),(0,0),(145,18)],1):
 ax=fig.add_subplot(1,3,i,projection='3d')
 for n,m,c,a in items:
  polys=Poly3DCollection(m.triangles[::max(1,len(m.faces)//1500) if c=='gray' else 1],facecolor=c,alpha=a,edgecolor='none');ax.add_collection3d(polys)
 ax.set(xlim=(-80,80),ylim=(-80,80),zlim=(-140,180),xlabel='X mm',ylabel='Y mm',zlabel='Z mm');ax.set_box_aspect((1,1,2));ax.view_init(el,az)
fig.tight_layout();fig.savefig(O/'whole-robot-compact-zero-pose.png',dpi=140)
fig=plt.figure(figsize=(15,10))
for i,(az,el) in enumerate([(90,0),(0,0),(145,20)],1):
 ax=fig.add_subplot(1,3,i,projection='3d')
 for n,m,c,a in items:
  if m.bounds[0,2]>45 or m.bounds[1,2]<-60:continue
  p=Poly3DCollection(m.triangles[::max(1,len(m.faces)//2000) if c=='gray' else 1],facecolor=c,alpha=a,edgecolor='none');ax.add_collection3d(p)
 ax.set(xlim=(-65,30),ylim=(-35,35),zlim=(-62,43),xlabel='X mm',ylabel='Y mm',zlabel='Z mm');ax.set_box_aspect((95,70,105));ax.view_init(el,az)
fig.tight_layout();fig.savefig(O/'compact-battery-regulators-detail.png',dpi=150)
