from pathlib import Path
import sys,numpy as np,trimesh,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
O=Path(__file__).resolve().parent;R=O.parent;S=R.parent.parent;H=S/'hardware-design-20260912/whole-robot-20260912/electrical/head-layout';sys.path.insert(0,str(H));from geometry import obstacles
T=np.array([[0,1,0],[0,0,-1],[1,0,0]])
fig=plt.figure(figsize=(13,7));ax=fig.add_subplot(111,projection='3d',computed_zorder=False)
for name,m,solid in obstacles(True):
 if name not in ['face_part','bottom_head_shell','motor_support']:continue
 if name=='motor_support':m=trimesh.load(R.parent/'assembly/mouth-support/motor-support-coaxial-assembly.stl')
 tri=m.triangles@T.T;ax.add_collection3d(Poly3DCollection(tri,facecolor={'face_part':'#ffcf64','bottom_head_shell':'#a8b2bd','motor_support':'#6994b8'}[name],alpha=.22,edgecolor='none'))
cap=trimesh.load(R/'head-cap-usb-service-body.stl');ax.add_collection3d(Poly3DCollection(cap.triangles@T.T,facecolor='#a1c3b0',alpha=.09,edgecolor='none'))
for label,pts,col in [('C: cap — M2.5 x 8',[[-3.3036,39,-67.5],[-3.3036,-39,-67.5],[-3.3036,0,31.5]],'#c43128'),('S: support — M2.5 x 6',[[-2.4,19,1.5],[-2.4,9.35,-41],[-2.4,-30,-34],[-2.4,-30,5]],'#1c4daa')]:
 for i,p in enumerate(pts):
  q=T@p;ax.scatter(*q,color=col,s=55,depthshade=False,zorder=10);ax.text(*(q+[0,0,3]),f'{label[0]}{i+1}',color=col,fontsize=12,zorder=11)
 ax.scatter([],[],[],color=col,label=label)
ax.set(xlim=(-50,50),ylim=(-45,85),zlim=(-20,45),xlabel='head Y (mm)',ylabel='−head Z (mm)',zlabel='head X (mm)');ax.set_box_aspect([100,130,65]);ax.view_init(elev=25,azim=35);ax.legend(loc='upper left');ax.set_title('Current head shell closure: 3 cap screws + 4 motor-support screws\nC3 upper boss restored; translucent CAD exposes the mounting locations')
fig.tight_layout();fig.savefig(O/'electronics-head-fastener-locations.png',dpi=160)
