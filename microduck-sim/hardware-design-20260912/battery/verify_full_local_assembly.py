from pathlib import Path
import trimesh,json,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import to_rgb
O=Path(__file__).resolve().parent
names=['battery_tray','frame_riser','battery_lid','electronics_deck','audio_enclosure','audio_grille']
meshes={n:trimesh.load(O/(n+'_assembly_position.ply'),force='mesh') for n in names}
meshes['a_obj']=trimesh.load(O/'a_obj_reference_local.stl',force='mesh')
components={n:trimesh.load(O/(n+'_envelope.ply'),force='mesh') for n in ['large_regulator','small_regulator','amplifier','speaker']}
b=trimesh.creation.box([34,63,22]);b.apply_translation([0,0,14.5]);components['battery']=b
checks={}
for cname,component in components.items():
 for name,mesh in meshes.items():
  x=trimesh.boolean.intersection([component,mesh],engine='manifold');vol=abs(float(x.volume));checks[cname+'_vs_'+name]=vol
for i,name in enumerate(names):
 for other in names[i+1:]:
  x=trimesh.boolean.intersection([meshes[name],meshes[other]],engine='manifold');checks[name+'_vs_'+other]=abs(float(x.volume))
for i in [1,2]:
 s=trimesh.load(O/f'strap_{i}_reference.ply',force='mesh')
 for n,m in meshes.items():checks[f'strap_{i}_vs_{n}']=abs(float(trimesh.boolean.intersection([s,m],engine='manifold').volume))
report={'intersection_volumes_mm3':checks,'passed':all(v<1e-5 for v in checks.values()),'check_count':len(checks),'scope':'Current a.obj + carrier + stipulated rectangular component envelopes + nonrounded ideal strap-route envelopes only; not full robot, screw head, wire or swept motion geometry.'}
(O/'full-local-collision-check.json').write_text(json.dumps(report,indent=2));print(json.dumps({'passed':report['passed'],'count':len(checks),'nonzero':{n:v for n,v in checks.items() if v>1e-5}},indent=2))
color={'a_obj':'#70818f','battery_tray':'#e68454','frame_riser':'#ddb558','battery_lid':'#d9bb89','electronics_deck':'#779e72','audio_enclosure':'#65789d','audio_grille':'#b5bfd0','battery':'#476ba0','large_regulator':'#414f62','small_regulator':'#456640','amplifier':'#37613e','speaker':'#424449'}
def add(ax,m,c,shift=(0,0,0)):
 v=m.vertices+np.array(shift);shade=.5+.5*np.abs(m.face_normals@np.array([.4,-.6,.7]));fc=np.array(to_rgb(c))[None,:]*shade[:,None];ax.add_collection3d(Poly3DCollection(v[m.faces],facecolor=fc,edgecolors='none'))
fig=plt.figure(figsize=(16,9))
for k in [1,2]:
 ax=fig.add_subplot(1,2,k,projection='3d')
 for n,m in meshes.items():
  if k==1 and n=='audio_grille':continue
  shift=(0,0,25) if k==2 and n=='audio_grille' else (0,0,0)
  add(ax,m,color[n],shift)
 for n,m in components.items():
  if n=='battery':continue
  add(ax,m,color[n])
 ax.set_xlim(-50,50);ax.set_ylim(-55,55);ax.set_zlim(-20,95);ax.set_box_aspect([1,1,1.1]);ax.view_init(25,-55 if k==1 else 135)
 ax.set_xlabel('U [mm]');ax.set_ylabel('V [mm]');ax.set_zlabel('W [mm]');ax.set_title('Outer electronics deck and open audio enclosure' if k==1 else 'Local attachment to current community a.obj')
fig.suptitle('External engineering prototype: 64 x 86 x 68.6 mm; complete-robot fit and walking unverified',fontsize=14)
fig.tight_layout();fig.savefig(O/'complete-external-backpack.png',dpi=170)
