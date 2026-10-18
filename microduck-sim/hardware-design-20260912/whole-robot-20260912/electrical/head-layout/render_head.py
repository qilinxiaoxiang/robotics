"""Render final head CAD in a conventional view (body X is up)."""
from geometry import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
D=HERE/'final'
T=np.eye(4);T[:3,:3]=[[0,1,0],[0,0,-1],[1,0,0]]
fig=plt.figure(figsize=(14,8))
for i,title in enumerate(['Assembled: camera faces the beak','Inside: original Pi retained; OpenRB and audio installed']):
 ax=fig.add_subplot(1,2,i+1,projection='3d',computed_zorder=False)
 def draw(m,c,a=1):
  m=m.copy().apply_transform(T);f=m.triangles
  if len(f)>25000:f=f[np.arange(0,len(f),int(len(f)/25000)+1)]
  coll=Poly3DCollection(f,facecolor=c,alpha=a,linewidth=.01,edgecolor=(0,0,0,.02));coll.set_zorder(len(ax.collections));ax.add_collection3d(coll)
 for n,m,mm in obstacles(True):
  if i==1 and n in ['face_part','jaw','bottom_head_shell','noenoeil']:continue
  draw(m,'#e9b953' if n in ['face_part','jaw','noenoeil'] else '#c4ced7',1 if i==0 else .14)
 draw(trimesh.load(D/'head_cap_assembly.stl'),'#bdcad5',1 if i==0 else .055)
 for n,c in [('camera_pitch_foot','#274b61'),('camera_cradle','#eda747'),('camera_pcb','#27845b'),('camera_lens_body','#333940'),('camera_lens','#101922')]:
  draw(trimesh.load(D/(n+'_assembly.stl')),c)
 if i==1:
  for n,c,a in [('audio_carrier','#e8a141',1),('openrb_actual_box_proxy','#2583ac',1),('amp_reservation','#b851b5',.85),('speaker_reservation','#333c48',.85),('pi_inside_components_reservation','#24825a',.85),('pi_gpio_connection_reservation','#164d39',.7)]:draw(trimesh.load(D/(n+'_assembly.stl')),c,a)
  for n in ['openrb_usb_plug','pi_usb_data_plug','pi_usb_power_plug','pi_camera_connector']:draw(trimesh.load(D/(n+'_reservation_assembly.stl')),'#dc5535',.45)
  for label,p in [('OpenRB',[29,0,-18]),('Amp',[25,-27,-26]),('Speaker',[20,28,0]),('Pi',[15.4,0,-60])]:
   q=(T@np.r_[p,1])[:3];ax.text(*q,label,fontsize=10)
 ax.set(xlim=(-50,50),ylim=(-45,90),zlim=(-18,90),title=title)
 ax.set_box_aspect([100,135,108]);ax.view_init(elev=23,azim=42);ax.set_axis_off()
fig.suptitle('MicroDuck: final head CAD and camera, 12 September 2026',fontsize=15)
fig.tight_layout();fig.savefig(D/'head-final-assembly.png',dpi=190,bbox_inches='tight')
