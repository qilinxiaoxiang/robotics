from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle
O=Path(__file__).resolve().parent;j=json.loads((O/'joint-fasteners.json').read_text());fig,axes=plt.subplots(5,3,figsize=(16,20));titles={1:'Right ankle',2:'Right knee',3:'Right hip pitch',4:'Right hip roll',5:'Right hip yaw',6:'Left ankle',7:'Left knee',8:'Left hip pitch',9:'Left hip roll',10:'Left hip yaw',11:'Head pitch',12:'Neck pitch',13:'Head yaw',14:'Head roll',15:'Jaw'}
for sid,ax in enumerate(axes.flat,1):
 ax.set_title(f'ID {sid} — {titles[sid]}',loc='left',fontsize=13,fontweight='bold');ax.set_aspect('equal');ax.set_xlim(-13,45);ax.set_ylim(-32,15);ax.axis('off')
 for side,dx,title in [(-1,0,'FRONT / active'),(1,31,'REAR / passive')]:
  ax.add_patch(Rectangle((dx-10,-24.5),20,34,facecolor='#f3f5f7',edgecolor='#8795a2',lw=1));ax.add_patch(Circle((dx,0),8,fill=False,ec='#aab5bf',lw=.7));ax.text(dx,11,title,ha='center',fontsize=8)
  rows=[c for c in j['connections'] if c['servo_ids']==[sid] and c['side']==side]
  for c in rows:
   _,y,z=c['hole_centers_mm'][0];xx=dx+y*(-1 if side==1 else 1);color={'horn':'#0066ad','case':'#c25618','rear_center':'#7c3da6'}[c['category']];ax.plot(xx,z,'o',ms=4,color=color)
   label=str(c['length_mm'])+('+W' if c['washer_mm'] else '')
   ax.text(xx+1.1,z+.7,label,fontsize=8,color=color,fontweight='bold')
  if not rows:ax.text(dx,-13,'No added\nservo screws',ha='center',fontsize=7,color='#56616d')
 ax.text(-10,-29,'Numbers = screw length in mm; W = 0.5 mm washer',fontsize=6.5)
fig.suptitle('MicroDuck — verified motor fastener locations',fontsize=23,fontweight='bold',y=.985)
fig.text(.5,.95,'Blue: M2 horn  |  Orange: M2 case  |  Purple: M2.6 rear center\nMotor shown shaft-high, connectors low. Rear view is mirrored. Locate motor IDs using the assembly servo map.',ha='center',fontsize=11)
fig.tight_layout(rect=(0,.025,1,.94),h_pad=2,w_pad=2)
fig.text(.5,.016,'Native geometry audit: 68 horn + 40 case + 10 rear-center screws. Separate idler horn/cap only on IDs 11 and 12. See guide for thread type and order.',ha='center',fontsize=10)
fig.savefig(O/'motor-fastener-locations.png',dpi=160);fig.savefig(O/'motor-fastener-locations.svg');print(O/'motor-fastener-locations.png')
