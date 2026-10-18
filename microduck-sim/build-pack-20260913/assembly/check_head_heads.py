from pathlib import Path
import sys,json,numpy as np,trimesh
from scipy.spatial.transform import Rotation
H=Path(__file__).resolve().parent
D=H.parents[1]/'hardware-design-20260912/whole-robot-20260912/electrical/head-layout'
sys.path.insert(0,str(D));from geometry import man,tri,obstacles,add_pi,hits
F=D/'final'
def cyl(c,axis):
 T=np.eye(4)
 if axis==0:T[:3,:3]=[[0,0,1],[0,1,0],[-1,0,0]]
 T[:3,3]=c
 return man(trimesh.creation.cylinder(radius=2,height=1.72,sections=64,transform=T))
CF=np.array(json.loads((F/'head-mesh-mass-manifest.json').read_text())['camera_foot_to_body_mm']);C0=np.eye(4);C0[:3,:3]=Rotation.from_euler('x',90,degrees=True).as_matrix();C0[:3,3]=[-12.5,4.5,20.5]
heads=[]
for y in [-10.25,10.25]:
 for z in [-48.75,12.75]:heads.append(('OpenRB',cyl([24.5-.86,y,z],0)))
for y in [-36,36]:heads.append(('Audio',cyl([17.2-.86,y,23],0)))
for x,y in [(2,2),(23,2),(2,14.5),(23,14.5)]:heads.append(('Camera',cyl([x,y,8.32+.86],2).transform((CF@C0)[:3])))
obs=add_pi(obstacles(True))
for name in ['head_cap_assembly','audio_carrier_assembly','camera_cradle_assembly','camera_module3_wide_assembly','openrb_actual_box_proxy_assembly','amp_reservation_assembly','speaker_reservation_assembly','openrb_usb_plug_reservation_assembly','pi_usb_data_plug_reservation_assembly','pi_usb_power_plug_reservation_assembly']:
 m=trimesh.load(F/(name+'.stl'),force='mesh');obs.append((name,m,man(m)))
r=[{'use':n,'hits':hits(s,obs)} for n,s in heads]
res={'head_diameter_mm':4,'head_height_mm':1.72,'under_head_planes_unchanged':True,'checks':r,'passed':all(not x['hits'] for x in r),'scope':'Static pan-head envelope only; thread engagement and physical printed tolerance remain separate.'}
(H/'head-din7985-check.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
