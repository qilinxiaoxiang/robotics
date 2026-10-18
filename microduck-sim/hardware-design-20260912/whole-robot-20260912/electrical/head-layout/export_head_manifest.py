"""Frozen head assembly exports, fastener/optical checks, labelled mass inputs."""
from geometry import *
import json, hashlib, cadquery as cq
from scipy.spatial.transform import Rotation
D=HERE/'final';CAM=HERE.parents[2]/'camera'
# Import only camera constructors, without rerunning the previous CAD export.
ns={'__file__':str(CAM/'build_camera_mount.py')};exec((CAM/'build_camera_mount.py').read_text().split('cradle=make_cradle();')[0],ns)
def cqt(s):
 v,f=s.val().tessellate(.035,.08)
 return trimesh.Trimesh([[a.x,a.y,a.z] for a in v],f,process=True)
def cylinder(c,r,h,axis=0):
 T=np.eye(4)
 if axis==0:T[:3,:3]=np.array([[0,0,1],[0,1,0],[-1,0,0]])
 elif axis==1:T[:3,:3]=np.array([[1,0,0],[0,0,1],[0,-1,0]])
 T[:3,3]=c
 return man(trimesh.creation.cylinder(radius=r,height=h,sections=48,transform=T))
def union(xs):return manifold3d.Manifold.batch_boolean(xs,manifold3d.OpType.Add)
def export(n,m):m.export(D/(n+'.stl'));return {'mesh_file':str(D/(n+'.stl')),'body':'jaw_soft','units':'mm','position_mm':[0,0,0],'rotation_matrix':np.eye(3).tolist(),'center_of_mass_mm':m.center_mass.tolist(),'bounds_mm':m.bounds.tolist()}
CF=np.eye(4);CF[:3,:3]=[[0,0,1],[1,0,0],[0,1,0]];CF[:3,3]=[42.66671433493411,.00007450580597,-37.84501011669636]
# This includes 180-degree rotation around the foot normal: camera faces the beak.
base=trimesh.load(CAM/'camera_pitch_foot.stl').apply_transform(CF)
cradle0=cqt(ns['to_assembly'](ns['make_cradle']()))
proxy0={n:cqt(ns['to_assembly'](s)) for n,s in ns['make_proxy']().items()}
pieces=[]
def item(n,m,mass,kind,**kw):
 r={'id':n,**export(n+'_assembly',m),'mass_g':mass,'mass_basis':kind,**kw};pieces.append(r);return r
for n in ['head_cap','audio_carrier']:
 m=trimesh.load(D/(n+'_assembly.stl'));item(n,m,float(m.volume*.00127),'solid PETG volume upper bound; replace with slice mass')
item('camera_pitch_foot',base,base.volume*.00127,'solid PETG volume upper bound')
cradle=cradle0.copy().apply_transform(CF)
item('camera_cradle',cradle,cradle.volume*.00127,'solid PETG volume upper bound')
camera_actual=[]
for n,m in proxy0.items():
 bm=m.copy().apply_transform(CF);export('camera_'+n+'_assembly',bm)
 if n!='ribbon_keepout':camera_actual.append(bm)
camera=trimesh.util.concatenate(camera_actual)
item('camera_module3_wide',camera,4,'manufacturer total mass; distribute once across this combined mesh',mass_interval_g=[3.6,4.4])
openrb=trimesh.load(HERE.parent/'sources/openrb-official.stl').apply_transform(np.block([[np.array([[0,0,1],[1,0,0],[0,1,0]]),np.array([[24.5],[0],[-18]])],[np.zeros((1,3)),np.ones((1,1))]]))
item('openrb',openrb,13,'manufacturer mass; manufacturer 136-solid STEP geometry',mass_interval_g=[11.7,14.3])
for n,mass,interval in [('amp',1.2,[1.2,5]),('speaker',3,[2.7,3.3])]:
 item(n,trimesh.load(D/(n+'_reservation_assembly.stl')),mass,'supplier mass / engineering installation box',mass_interval_g=interval)
pi=next(m for n,m,mm in obstacles() if n=='pcb__raspberry_pi_zero_2_w')
item('pi_retained',pi,0,'zero delta: original Pi and its original mass remain; do not add another 10 g',absolute_mass_reference_g=10)
for n,c,d in PI_KEEP:export(n+'_reservation_assembly',box(c,d))
# Fasteners: placement proxies, no thread geometry. Face of PCB underside X24.5.
screws=[]
for y in [-10.25,10.25]:
 for z in [-48.75,12.75]:
  screws+=[cylinder([33.5,y,z],1,18),cylinder([23.7,y,z],1.9,1.6)]
for y in [-36,36]:
 screws+=[cylinder([29.7,y,23],1,25),cylinder([16.4,y,23],1.9,1.6)]
for y in [-11,11]:
 # M3x10, 0.5 mm washer; under-head plane X46.1667.
 screws+=[cylinder([41.16671433493411,y,-37.84501011669636],1.5,10),cylinder([47.4,y,-37.84501011669636],2.85,2.46)]
# Camera PCB M2x8 and pitch-hinge M3x20 reference shafts/heads.
C0=np.eye(4);C0[:3,:3]=Rotation.from_euler('x',90,degrees=True).as_matrix();C0[:3,3]=[-12.5,4.5,20.5]
for xx,yy in [(2,2),(23,2),(2,14.5),(23,14.5)]:
 screws += [cylinder([xx,yy,4.32],1,8,2).transform((CF@C0)[:3]),cylinder([xx,yy,9.12],1.9,1.6,2).transform((CF@C0)[:3])]
screws += [cylinder([1.5,0,11],1.5,20).transform(CF[:3]),cylinder([-9.73,0,11],2.85,2.46).transform(CF[:3])]
fast=union(screws)
# Steel upper bound: full cylinders (threads/rounded heads only remove material),
# ten M2 nuts, three M3 nuts, and four 7x3.2x0.5 mm M3 washers.
nut2=(np.sqrt(3)/2*4**2-np.pi)*1.6
nut3=(np.sqrt(3)/2*5.5**2-np.pi*1.5**2)*2.4
washer=np.pi*(3.5**2-1.6**2)*.5
hardware_g=float((fast.volume()+10*nut2+3*nut3+4*washer)*.00785)
export('head_fastener_reference_assembly',tri(fast))
fixed=add_pi(obstacles(True));actualor=man(trimesh.load(D/'openrb_actual_box_proxy_assembly.stl'))
components=[('openrb',tri(actualor),actualor)]+[(n,trimesh.load(D/(n+'_reservation_assembly.stl')),man(trimesh.load(D/(n+'_reservation_assembly.stl')))) for n in ['amp','speaker','openrb_usb_plug','pi_usb_data_plug','pi_usb_power_plug','pi_camera_connector']]
checks={'fasteners_vs_electronics':hits(fast,components+[('camera_module',camera,man(camera))]),'fastener_solid_steel_upper_g':hardware_g,'fasteners_vs_retained_geometry':hits(fast,fixed),'camera_cf_mm':CF.tolist(),'pitch':[]}
cap=man(trimesh.load(D/'head_cap_assembly.stl'))
fixedcamera=[('cap',tri(cap),cap),('foot',base,man(base))]+fixed
for deg in range(-45,46,5):
 P=np.eye(4);P[:3,:3]=Rotation.from_euler('x',deg,degrees=True).as_matrix();p=np.array([0,0,11]);P[:3,3]=p-P[:3,:3]@p
 M=CF@P;cr=cradle0.copy().apply_transform(M)
 lens=M@np.array([0,-12.12,34.9,1]);dirs=[]
 # Finite 200 mm frustum begins 0.05 mm beyond lens-front center.
 for length in [.05,200]:
  for h in [-1,1]:
   for v in [-1,1]:dirs.append(lens[:3]+M[:3,:3]@np.array([h*length*np.tan(np.deg2rad(51)),-length,v*length*np.tan(np.deg2rad(33.5))]))
 fr=man(trimesh.convex.convex_hull(dirs))
 checks['pitch'].append({'degrees_positive_down':deg,'mount_intersections':hits(man(cr),fixedcamera),'full_102x67_degree_view_intersections':hits(fr,fixedcamera+[('cradle',cr,man(cr))])})
 if deg==0:export('camera_view_reference_assembly',tri(fr))
checks['fov_source']='https://www.raspberrypi.com/documentation/accessories/camera.html#hardware-specification'
checks['fov_limit']='Geometric unobstructed frustum, 200 mm range. No optical calibration, distortion, image quality, flex-cable dynamics, or camera occlusion by moving limbs tested here.'
(D/'camera-fastener-validation.json').write_text(json.dumps(checks,indent=2)+'\n')
oldtop=next(m for n,m,mm in obstacles() if n=='top_head_shell')
oldparts=[]
for g in fk()[1]:
 if g['body']=='jaw_soft' and g['mesh'] in REMOVE|{'top_head_shell'}:
  m=raw(g['mesh']).apply_transform(g['local']);oldparts.append({'id':g['mesh'],**export('removed_'+g['mesh']+'_reference',m),'mass_g':None if g['mesh']!='top_head_shell' else float(m.volume*.00127),'mass_basis':'unknown lumped mass; sample removal' if g['mesh']!='top_head_shell' else 'solid PETG assumption for old shell, pair with same density new shell'})
newfixed=sum(r['mass_g'] for r in pieces if r['id']!='pi_retained')-oldtop.volume*.00127
item('head_fasteners',tri(fast),hardware_g,'full-steel cylinders, nut and washer volume upper bound; nut geometry not in reference mesh')
manifest={'schema_version':1,'frame':'jaw_soft','units':'mm','frozen_date':'2026-09-12','camera_foot_to_body_mm':CF.tolist(),'pieces':pieces,'reservation_meshes':[{'id':p.stem,'mesh_file':str(p),'body':'jaw_soft','units':'mm','mass_g':0} for p in D.glob('*_reservation_assembly.stl')],'remove_original_geoms':[r['id'] for r in oldparts],'removed_original_references':oldparts,'discard_previous_proposal_parts':['camera-conformal-saddle','camera-inner-backing'],'retain_original_pi':True,'imu_location':'trunk_base; no head IMU added','head_delta_accounting':{'new_electronics_and_print_delta_g':float(newfixed),'new_head_fastener_solid_steel_upper_g':hardware_g,'new_head_cable_allowance_g':4,'old_electronics_removed_g':None,'equation':'head_delta = electronics + new print mass - old print mass + new hardware + head cable allowance - old hat/speaker/lens/holder mass','sample_old_removed_g':[0,10,20,30],'sample_result_head_delta_g':[float(newfixed+hardware_g+4-v) for v in [0,10,20,30]],'interval_warning':'Old individual masses are unknown. These are sensitivity scenarios, not a measured 20–35 g payload. Do not duplicate the 4 g head cable allowance if the global harness mass already includes it.'},'fasteners':[{'use':'OpenRB four PCB holes','quantity':4,'spec':'M2 x 18 mm pan-head + M2 hex nut; hole diameter 2.4 mm'},{'use':'Audio carrier to cap','quantity':2,'spec':'M2 x 25 mm pan-head + M2 hex nut'},{'use':'Camera foot to integrated cap bosses','quantity':2,'spec':'M3 x 10 mm button-head + 0.5 mm flat washer + M3 hex nut; replaces old M3x20'},{'use':'Camera PCB/cradle and pitch hinge','spec':'Retain camera/README.md M2 hardware and M3 hinge fastener'}],'notes':['Masses in pieces are absolute values unless pi_retained; adding all pieces without removing old head shell and old electronics double counts.','Manufacturer STEP OpenRB STL has multiple solids; use its separate padded component envelope for collision.','All *_assembly.stl already use body coordinates; position zero / identity rotation.','construction.step files contain editable primitives only; use parameter script and final STL for complete boolean result.']}
(D/'head-mesh-mass-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
(D/'frozen-sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.glob('*_print.stl')},indent=2)+'\n')
print(json.dumps({'fasteners':checks['fasteners_vs_electronics'],'fasteners_fixed':checks['fasteners_vs_retained_geometry'],'zero_pitch':checks['pitch'][9],'head_delta':manifest['head_delta_accounting']},indent=2))
