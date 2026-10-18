from pathlib import Path
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
OUT=Path(__file__).resolve().parent

def add(ax,mesh,color,alpha=1):
 from matplotlib.colors import to_rgba
 if not hasattr(ax,'_cad_faces'): ax._cad_faces=[]; ax._cad_colors=[]
 vertices,faces=trimesh.remesh.subdivide_to_size(mesh.vertices,mesh.faces,max_edge=2.5,max_iter=7)
 m=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
 rgba=np.array(to_rgba(color,alpha));light=np.array([-.3,-.45,.84]);light=light/np.linalg.norm(light)
 intensity=.70+.30*np.clip(m.face_normals@light,-.5,1)
 colors=np.tile(rgba,(len(faces),1)); colors[:,:3]*=intensity[:,None]
 ax._cad_faces.extend(vertices[faces]); ax._cad_colors.extend(colors)

def finish(ax):
 coll=Poly3DCollection(ax._cad_faces,facecolors=ax._cad_colors,edgecolors='none',linewidths=0,zsort='average')
 ax.add_collection3d(coll)

def block(center,extent):
 m=trimesh.creation.box(extents=extent);m.apply_translation(center);return m

def assembled(m):
 m=m.copy();m.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[1,0,0]));m.apply_translation([-12.5,4.5,20.5]);return m

cradle=trimesh.load(OUT/'camera_cradle.stl',force='mesh');foot=trimesh.load(OUT/'camera_pitch_foot.stl',force='mesh')
pcb=block([12.5,23.862/2,7.2+1.12/2],[25,23.862,1.12]);body=block([12.5,14.4,8.32+4.07/2],[10.8,10.8,4.07]);lens=trimesh.creation.cylinder(radius=3.475,height=4.23,sections=48);lens.apply_translation([12.5,14.4,12.39+4.23/2]);ribbon=block([12.5,29.862,4.95],[20,12,.5])
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig=plt.figure(figsize=(14,9),facecolor='#f5f3ef')
fig.suptitle('Camera Module 3 Wide | adjustable mount',fontsize=22,fontweight='bold',x=.055,ha='left',y=.97)
fig.text(.055,.917,'Two printable parts  /  four M2 camera screws  /  one M3 pitch bolt',fontsize=12,color='#435261')
for idx,(elev,azim,title) in enumerate([(23,-60,'Front: lens remains fully open'),(20,118,'Rear: connector space and cable exit')],1):
 ax=fig.add_subplot(1,2,idx,projection='3d',facecolor='#f5f3ef');add(ax,foot,'#244455');add(ax,assembled(cradle),'#eaaa44');add(ax,assembled(pcb),'#26875a');add(ax,assembled(body),'#3d4146');add(ax,assembled(lens),'#151e23');add(ax,assembled(ribbon),'#d8dbe1',.7)
 # Hinge bolt is a visual reference, not a printed component.
 bolt=trimesh.creation.cylinder(radius=1.5,height=20,sections=20);bolt.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2,[0,1,0]));bolt.apply_translation([0,0,11]);add(ax,bolt,'#adb9c1');finish(ax)
 ax.set(xlim=(-20,20),ylim=(-20,20),zlim=(0,55));ax.set_box_aspect((40,40,55));ax.view_init(elev=elev,azim=azim);ax.set_axis_off();ax.set_title(title,pad=0,fontweight='bold')
fig.text(.06,.085,'Foot: 30 x 16 x 3 mm\nM3 mounting holes: 22 mm centre-to-centre\nPitch axis: 11 mm above the foot underside',fontsize=11,color='#243b4a')
fig.text(.55,.085,'Rear PCB clearance: 4.8 mm\nPrinted M2 spacer height: 4.8 mm\nCamera, cable and bolt are reference objects',fontsize=11,color='#243b4a')
fig.text(.06,.035,'CAD geometry verification only. Final robot-head mating and physical fit are separate checks.',fontsize=10,color='#6d7377')
fig.subplots_adjust(left=.015,right=.985,top=.86,bottom=.16,wspace=.02)
fig.savefig(OUT/'camera_mount_assembly.png',dpi=160);plt.close(fig)

fig=plt.figure(figsize=(14,7),facecolor='#f5f3ef');fig.suptitle('Print these two parts',fontsize=22,fontweight='bold',x=.065,ha='left',y=.96)
for idx,(mesh,title) in enumerate([(cradle,'1  Camera cradle | flat back on bed'),(foot,'2  Pitch foot | flat underside on bed')],1):
 ax=fig.add_subplot(1,2,idx,projection='3d',facecolor='#f5f3ef');add(ax,mesh,'#eaaa44' if idx==1 else '#244455');finish(ax);b=mesh.bounds;mid=b.mean(axis=0);span=max(mesh.extents)*1.2;ax.set(xlim=(mid[0]-span/2,mid[0]+span/2),ylim=(mid[1]-span/2,mid[1]+span/2),zlim=(0,span));ax.set_box_aspect((1,1,1));ax.view_init(elev=33,azim=-65);ax.set_axis_off();ax.set_title(title,fontweight='bold')
fig.text(.065,.075,'M2 nut pockets are on the underside. The hinge holes have a printable peaked roof.',fontsize=11,color='#243b4a');fig.text(.065,.035,'Units: mm. Use the individual STL files, not the assembly reference STEP.',fontsize=10,color='#6d7377');fig.subplots_adjust(top=.86,bottom=.13);fig.savefig(OUT/'camera_mount_print_parts.png',dpi=160)
