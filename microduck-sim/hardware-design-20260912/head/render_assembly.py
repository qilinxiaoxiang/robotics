from pathlib import Path
import numpy as np,trimesh,json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
P=Path(__file__).resolve().parent
T=np.array(json.loads((P/'validation.json').read_text())['camera_base_to_original_head_4x4'])
head=trimesh.load(P/'head-camera-holes-assembly.stl');pad=trimesh.load(P/'camera-conformal-saddle-assembly.stl');back=trimesh.load(P/'camera-inner-backing-assembly.stl');foot=trimesh.load(P.parent/'camera/camera_pitch_foot.stl');cradle=trimesh.load(P.parent/'camera/camera_cradle.stl')
foot.apply_transform(T)
cradle.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]));cradle.apply_translation([-12.5,4.5,20.5]);cradle.apply_transform(T)
parts=[(head,'#bcc6cf'),(pad,'#32738b'),(back,'#547a75'),(foot,'#2a4d62'),(cradle,'#eaa653')]
checks={}
for label,m in [('foot',foot),('cradle',cradle)]:
 a=trimesh.boolean.intersection([head,m],engine='manifold');checks[label+'_head_intersection_mm3']=0 if a.is_empty else a.volume
assert max(checks.values()) < .001
(P/'assembled-camera-clearance.json').write_text(json.dumps(checks,indent=2))
# Reorient original Y-up to plotted Z-up.
rot=np.array([[1,0,0,0],[0,0,-1,0],[0,1,0,0],[0,0,0,1.]])
fig=plt.figure(figsize=(13,7),facecolor='#faf9f6')
for j,view in enumerate([(25,-145),(18,-55)],1):
 ax=fig.add_subplot(1,2,j,projection='3d');ax.set_facecolor('#faf9f6')
 for original,color in parts:
  m=original.copy();m.apply_transform(rot); norm=m.face_normals;bright=np.clip(norm@np.array([.3,-.4,.85])*.32+.72,.25,1)
  rgba=np.tile(matplotlib.colors.to_rgba(color),(len(norm),1));rgba[:,:3]*=bright[:,None]
  ax.add_collection3d(Poly3DCollection(m.triangles,facecolors=rgba,edgecolors='none'))
 ax.set_xlim(-65,65);ax.set_ylim(-65,65);ax.set_zlim(-25,90);ax.set_box_aspect([130,130,115]);ax.view_init(*view);ax.set_axis_off()
 ax.set_title('Camera mount on original head shell' if j==1 else 'Two-bolt saddle and cable opening',fontsize=13)
fig.text(.5,.06,'Current 3MF shell + conformal saddle + inner backing + adjustable camera cradle\nLocal fit checked in CAD; complete robot movement and physical fit require assembly.',ha='center',fontsize=11,color='#46515b')
fig.tight_layout();fig.savefig(P/'head-camera-assembly.png',dpi=160)
print(checks)
