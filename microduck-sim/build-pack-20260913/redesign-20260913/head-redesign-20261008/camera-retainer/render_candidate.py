from pathlib import Path
import trimesh,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
D=Path(__file__).resolve().parent
fig=plt.figure(figsize=(14,7),facecolor='#faf9f5')
for i,title in enumerate(['Rear view: removable U-frame and four camera pads','Detached face: camera fixed first, Pi mounted last'],1):
 ax=fig.add_subplot(1,2,i,projection='3d',computed_zorder=False);ax.set_facecolor('#faf9f5')
 objs=[('camera-retainer-world.stl','#de982f',1),('camera-shifted-reference-world.stl','#448b79',.9),('camera-ribbon-shifted-reference-world.stl','#8a64b5',1),('camera-all-six-screw-envelopes-world.stl','#74818b',1)]
 if i==2:objs.insert(0,('face-with-camera-anchors-world.stl','#d7dce1',.20))
 for n,c,a in objs:
  m=trimesh.load_mesh(D/n);p=Poly3DCollection(m.triangles,facecolor=c,edgecolor='none',alpha=a,linewidths=0);ax.add_collection3d(p)
 ax.set_xlim(67,89);ax.set_ylim(-45 if i==2 else -24,45 if i==2 else 24);ax.set_zlim(109,155);ax.set_box_aspect((22,90 if i==2 else 48,46));ax.view_init(elev=15,azim=170);ax.set_proj_type('ortho');ax.set_xlabel('X / mm');ax.set_ylabel('Y / mm');ax.set_zlabel('Z / mm');ax.set_title(title,fontsize=12,pad=14);ax.grid(False);ax.set_axis_off()
fig.text(.05,.025,'Orange: printed retainer   Green: camera envelope   Grey: 6 M2 x 6 TAP screws   Purple: initial ribbon reservation\nDigital candidate only. Original curved shell and visible face outline are preserved. Full camera rear electronics and print strength need physical checks.',fontsize=10,color='#27323b')
plt.tight_layout(rect=[0,.10,1,.94]);fig.savefig(D/'camera-retainer-candidate.png',dpi=160)
