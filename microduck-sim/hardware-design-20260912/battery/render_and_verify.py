from pathlib import Path
import numpy as np,trimesh,json,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from matplotlib.colors import to_rgb
O=Path(__file__).resolve().parent
parts={n:trimesh.load(O/(n+'_assembly_position.ply'),force='mesh') for n in ['battery_tray','frame_riser','battery_lid']}
frame=trimesh.load(O/'a_obj_reference_local.stl',force='mesh')
battery=trimesh.creation.box([34,63,22]);battery.apply_translation([0,0,14.5])
# A non-rounded geometric route envelope for 4.8 x 1.0 mm ties.
def block(ext,pos):
 m=trimesh.creation.box(ext);m.apply_translation(pos);return m
straps=[]
for v in [-18.3495,18.3495]:
 bits=[block([36.73,4.8,1],[0,v,-13.1]),block([42.8,4.8,1],[0,v,29.5])]
 for s in [-1,1]:
  bits.append(block([1,4.8,6.6],[s*18.365,v,-9.8]))
  bits.append(block([3.035+1,4.8,1],[s*((18.365+21.4)/2),v,-6.5]))
  bits.append(block([1,4.8,36],[s*21.4,v,11.5]))
 strap=trimesh.boolean.union(bits,engine='manifold');straps.append(strap)
checks={}
for i,s in enumerate(straps):
 for name,m in {'a_obj':frame,**parts}.items():
  inter=trimesh.boolean.intersection([s,m],engine='manifold');checks[f'strap{i+1}_vs_{name}']=float(inter.volume)
for name,m in parts.items():
 checks[f'battery_vs_{name}']=float(trimesh.boolean.intersection([battery,m],engine='manifold').volume)
for a,b in [('battery_tray','frame_riser'),('battery_tray','battery_lid'),('frame_riser','battery_lid')]:
 checks[f'{a}_vs_{b}']=float(trimesh.boolean.intersection([parts[a],parts[b]],engine='manifold').volume)
(O/'assembly-collision-check.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
for i,s in enumerate(straps):s.export(O/f'strap_{i+1}_reference.ply')
colors={'a_obj':'#70838f','frame_riser':'#efb75e','battery_tray':'#e47a48','battery':'#5b92c9','battery_lid':'#edd2aa','strap':'#444444'}
fig=plt.figure(figsize=(15,9))
def draw(ax,m,color,shift=0,alpha=1):
 v=m.vertices.copy();v[:,2]+=shift
 light=np.array([.4,-.6,.7]);normals=m.face_normals;shade=np.clip(.45+.55*np.abs(normals@light),.35,1)
 fc=np.array(to_rgb(color))[None,:]*shade[:,None];col=Poly3DCollection(v[m.faces],facecolors=fc,edgecolors='none',alpha=alpha);ax.add_collection3d(col)
for i,(elev,azim,exploded) in enumerate([(22,-50,False),(22,40,True)],1):
 ax=fig.add_subplot(1,2,i,projection='3d')
 draw(ax,frame,colors['a_obj']);draw(ax,parts['frame_riser'],colors['frame_riser'],shift=5 if exploded else 0)
 draw(ax,parts['battery_tray'],colors['battery_tray'],shift=15 if exploded else 0)
 if exploded:draw(ax,battery,colors['battery'],shift=28)
 draw(ax,parts['battery_lid'],colors['battery_lid'],shift=43 if exploded else 0)
 if not exploded:
  for s in straps:draw(ax,s,colors['strap'])
 ax.set_xlim(-50,50);ax.set_ylim(-50,50);ax.set_zlim(-20,80 if exploded else 60);ax.set_box_aspect([1,1,1]);ax.view_init(elev,azim);ax.set_xlabel('U [mm]');ax.set_ylabel('V [mm]');ax.set_zlabel('W [mm]');ax.set_title('Current a.obj + local backpack assembly' if not exploded else 'Exploded: riser / tray / battery / lid')
fig.suptitle('MicroDuck battery carrier: local part fit verified; complete robot fit not yet verified',fontsize=14)
fig.tight_layout();fig.savefig(O/'battery-backpack-assembly.png',dpi=170)
# Close-up of frame side and tie channel cross-section.
fig=plt.figure(figsize=(10,7));ax=fig.add_subplot(111,projection='3d')
draw(ax,frame,colors['a_obj']);draw(ax,parts['frame_riser'],colors['frame_riser']);
for s in straps:draw(ax,s,colors['strap'])
ax.set_xlim(-35,35);ax.set_ylim(-45,45);ax.set_zlim(-20,35);ax.set_box_aspect([1,1,1]);ax.view_init(20,140);ax.set_xlabel('U');ax.set_ylabel('V');ax.set_zlabel('W');ax.set_title('Eight riser feet avoid four original slots; ties return behind web')
fig.tight_layout();fig.savefig(O/'frame-strap-routing.png',dpi=170)
