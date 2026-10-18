"""P5/P6 current electronics fastening audit. Read-only models; writes only this audit.
Run with the requirements-design.txt CAD Python. Millimetres throughout.
Smooth shaft/head envelopes and source stack arithmetic; no physical torque claims.
"""
from pathlib import Path
import sys,json,hashlib,datetime
import numpy as np,trimesh,manifold3d as md
O=Path(__file__).resolve().parent; R=O.parent; P=R.parent; S=P.parent
W=S/'hardware-design-20260912/whole-robot-20260912'; H=W/'electrical/head-layout'; F=H/'final'
sys.path.insert(0,str(H))
from geometry import man,tri,box,obstacles,hits,fk,raw
# Run the native cap/motion acceptance first: a stale successful JSON cannot
# substitute for checking the actual cap loaded by this run.
import subprocess
closure_run=subprocess.run([sys.executable,str(O/'electronics_head_closure_check.py')],capture_output=True,text=True)
if closure_run.returncode:
 print(closure_run.stdout);print(closure_run.stderr,file=sys.stderr);sys.exit(closure_run.returncode)
closure_path=O/'electronics-head-closure-verification.json'
closure_evidence=json.loads(closure_path.read_text())
assert closure_evidence['passed']
assert closure_evidence['source_hashes'][str(R/'head-cap-usb-service-body.stl')]==hashlib.sha256((R/'head-cap-usb-service-body.stl').read_bytes()).hexdigest()
from evidence_sources import hashes, assembly_sources
sources=hashes(assembly_sources()+[H/'geometry.py', F/'camera-fastener-validation.json', closure_path])
sources.update(closure_evidence['source_hashes'])
def load(p):
 p=Path(p);sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();return trimesh.load(p,force='mesh')
def obj(n,p):
 m=load(p);return n,m,man(m)
def cylinder(center,r,length,axis=2):
 t=np.eye(4)
 if axis==0:t[:3,:3]=[[0,0,1],[0,1,0],[-1,0,0]]
 if axis==1:t[:3,:3]=[[1,0,0],[0,0,1],[0,-1,0]]
 t[:3,3]=center;return man(trimesh.creation.cylinder(radius=r,height=length,sections=64,transform=t))
def screw(point,axis,length,dia,head_dia,head_h):
 p=np.array(point,float);a=np.array(axis,float);sh=cylinder([0,0,length/2],dia/2,length);hd=cylinder([0,0,-head_h/2],head_dia/2,head_h)
 t=trimesh.geometry.align_vectors([0,0,1],a);t[:3,3]=p;return (sh+hd).transform(t[:3])
def check_shapes(ss,obs):return [dict(index=i,collisions=hits(s,obs)) for i,s in enumerate(ss)]
cap=obj('CURRENT_usb_service_cap',R/'head-cap-usb-service-body.stl')
headobs=[o for o in obstacles(True) if o[0]!='motor_support']+[cap,obj('current_motor_support',P/'assembly/mouth-support/motor-support-coaxial-assembly.stl')]
for n in ['audio_carrier_assembly','openrb_actual_box_proxy_assembly','amp_reservation_assembly','speaker_reservation_assembly','camera_pitch_foot_assembly','camera_cradle_assembly','camera_module3_wide_assembly']:
 headobs.append(obj(n,F/(n+'.stl')))
headobs.append(obj('accepted_current_usb_data_plug',R/'usb-data-plug-acceptance-envelope.stl'))
# Current GPIO housing envelope from the accepted current design.
gpio=box([3.935,-.011,-51.71],[7,52,15]);headobs.append(('gpio_2x20',gpio,man(gpio)))
connections=[]
def add(id,component,qty,spec,points,axis,stack,engagement,ss,obs,**extra):
 checks=check_shapes(ss,obs);r=dict(coordinate_frame='trunk_base' if id in ['fuse_carrier','imu_rear_cover','imu_clamp','optional_empty_cover'] else 'jaw_soft',id=id,component=component,quantity=qty,spec=spec,hole_centers_mm=points,axis=axis,stack_mm=stack,engagement_mm=engagement,evidence=checks,**extra);r['passed']=all(not v['collisions'] for v in checks) and extra.get('full_nut_engagement',True);connections.append(r);return r
pts=[[x,y,-59.21] for x in [3.935,26.935] for y in [-29.011,28.989]]
add('pi_old_max_head','Pi Zero 2 W to face',4,'M2.5 x 6 TAP; head <=4.5 diameter x1.8 high; no nuts',pts,[0,0,-1],{'pcb':1.6,'pilot_depth_approx':5.5},4.4,[screw(p,[0,0,-1],6,2.5,4.5,1.8) for p in pts],[o for o in headobs if o[0] not in ['face_part','gpio_2x20']]+[('old54mm_gpio_envelope',box([3.935,-.011,-51.71],[7,54,15]),man(box([3.935,-.011,-51.71],[7,54,15])))],tip_to_blind_end_mm=1.1)
add('pi','Pi Zero 2 W to face',4,'M2.5 x 6 TAP Uxcell a16060200ux0367; head4 diameter x1.5 high; no nuts',pts,[0,0,-1],{'pcb':1.6,'pilot_depth_approx':5.5},4.4,[screw(p,[0,0,-1],6,2.5,4,1.5) for p in pts],[o for o in headobs if o[0]!='face_part'],tip_to_blind_end_mm=1.1,head_to_gpio_nominal_min_gap_mm=1.0,head_source='procurement/sources/harf-pi-screws.html; a16060200ux0367')
pts=[[24.5,y,z] for y in [-10.25,10.25] for z in [-48.75,12.75]]
add('openrb','OpenRB to current cap',4,'M2 x 18 machine + M2 nut',pts,[1,0,0],{'pcb':1.6,'post_until_nut':14.1,'nut':1.6},1.6,[screw(p,[1,0,0],18,2,4,1.72) for p in pts],headobs,tip_beyond_nut_mm=.7,nut_quantity=4)
pts=[[17.2,y,23] for y in [-36,36]]
add('audio_carrier','Audio carrier to current cap',2,'M2 x 25 machine + M2 nut',pts,[1,0,0],{'carrier':1.2,'post_until_nut':21.8,'nut':1.6},1.6,[screw(p,[1,0,0],25,2,4,1.72) for p in pts],headobs,tip_beyond_nut_mm=.4,nut_quantity=2)
CF=np.array(json.loads((F/'camera-fastener-validation.json').read_text())['camera_cf_mm']); C0=np.eye(4);C0[:3,:3]=[[1,0,0],[0,0,-1],[0,1,0]];C0[:3,3]=[-12.5,4.5,20.5]; CT=CF@C0
localpts=[[x,y,8.32] for x,y in [(2,2),(23,2),(2,14.5),(23,14.5)]];pts=[(CT@np.r_[p,1])[:3].tolist() for p in localpts];axis=(CT[:3,:3]@np.array([0,0,-1])).tolist()
# Audit original length and the next 2mm standard length; do not alter print geometry.
for length in [8,10]:
 add('camera_pcb_'+str(length),'Camera PCB to cradle',4,f'M2 x {length} machine + M2 nut',pts,axis,{'pcb':1.12,'standoff':4.8,'backplate':2.4,'nut_recess':1.65,'nut':1.6},min(1.6,length-(8.32-1.65)),[screw(p,axis,length,2,4,1.72) for p in pts],headobs,nut_quantity=4,tip_beyond_nut_mm=length-8.27,full_nut_engagement=length>=8.27)
pts=[[46.16671433493411,y,-37.84501011669636] for y in [-11,11]]
add('camera_foot','Camera foot to cap',2,'M3 x 10 button head + 0.5 washer + M3 nut',pts,[-1,0,0],{'washer':.5,'foot':3,'cap_to_nut':1.91671433493411,'nut':2.4},2.4,[screw(p,[-1,0,0],10,3,5.7,2.46) for p in pts],headobs,nut_quantity=2,washer_quantity=2,tip_beyond_nut_mm=2.18328566506589)
p=(CF@np.array([-8.5,0,11,1]))[:3].tolist();a=(CF[:3,:3]@np.array([1,0,0])).tolist()
add('camera_hinge','Camera cradle pitch hinge',1,'M3 x 20 + two 0.5 washers + M3 nut',[p],a,{'ears_plus_gap':16,'washers':1,'nut':2.4},2.4,[screw(p,a,20,3,5.7,2.46)],headobs,nut_quantity=1,washer_quantity=2,tip_beyond_nut_mm=.6)
pts=[[-3.3036,y,z] for y,z in [(39,-67.5),(-39,-67.5),(0,31.5)]]
add('head_cap_closure','Current three-point cap to bottom head shell',3,'M2.5 x 8 TAP head<=4 diameter x1.5 high; no nuts',pts,[1,0,0],{'bottom_shell_skin':2.0036,'lower_original_pilot_entry_chamfer':.8,'upper_restored_pilot_entry_chamfer':0},5.1964,[screw(p,[1,0,0],8,2.5,4,1.5) for p in pts],[o for o in headobs if o[0]!='CURRENT_usb_service_cap'],upper_restored_pilot_engagement_mm=5.9964,upper_tip_margin_mm=6.3036,pilot_diameter_mm=2.1)
pts=[[-2.4,y,z] for y,z in [(19,1.5),(9.35,-41),(-30,-34),(-30,5)]]
add('motor_support_frame','Revised motor support to bottom head shell',4,'M2.5 x 6 TAP head<=4 diameter x1.5 high; no nuts',pts,[-1,0,0],{'support_plate':1.7,'pilot_entry_chamfer':.7},3.6,[screw(p,[-1,0,0],6,2.5,4,1.5) for p in pts],[o for o in headobs if o[0]!='bottom_head_shell'],pilot_diameter_mm=2.2,shortest_tip_margin_mm=2.1)
trunk=[];geom=json.loads((P/'phase1/simulation/geometry-manifest.json').read_text());removed=set(geom['remove_meshes'])
for g in fk()[1]:
 if g['body']=='trunk_base' and g['mesh'] not in removed:
  m=raw(g['mesh']).apply_transform(g['local']);trunk.append((g['mesh'],m,man(m)))
for n,p in [('support',W/'assembly/compact-battery/power-support-integrated-body.stl'),('imu_holder',W/'assembly/trunk-imu/imu_clamp_holder_body.stl'),('imu_cover',W/'assembly/trunk-imu/imu_rear_cover_body.stl'),('imu_board',W/'assembly/trunk-imu/imu_28x25x8_envelope_body.stl'),('fuse_carrier',P/'assembly/service-mounts/fuse-bank-body.stl'),('dfr1202',R/'dfr1202-envelope-body.stl'),('dfr_insert',R/'regulator-open-insert-body.stl')]:trunk.append(obj(n,p))
pts=[[x,y,-69] for x in [-54.931,-16.069] for y in [-12.7,12.7]]
add('fuse_carrier','Fuse carrier retained without old regulator board',4,'M2 x 20 machine + M2 nut',pts,[0,0,1],{'carrier_post':11.5,'shelf':2,'integral_spacer':2,'nut':1.6},1.6,[screw(p,[0,0,1],20,2,4,1.72) for p in pts],trunk,nut_quantity=4,tip_beyond_nut_mm=2.9,old_pcb_removed_mm=1.6)
pts=[[-62.6,y,z] for y in [-17.5,17.5] for z in [4,26]]
add('imu_rear_cover','Rear cover without removed alarm carrier',4,'M2 x 6 into existing plastic pilot; no nuts',pts,[1,0,0],{'cover':1.2,'pilot_boss':5},4.8,[screw(p,[1,0,0],6,2,4,1.72) for p in pts],[o for o in trunk if o[0]!='imu_holder'],tip_to_boss_end_mm=.2,pilot_diameter_mm=1.6,obsolete_M2x8_tip_past_boss_mm=1.8)
pts=[[-48,y,34.5] for y in [-18,18]]
add('imu_clamp','IMU clamp pressure screws',2,'M2 x 5 into1.6 pilot; no nuts',pts,[0,0,-1],{'pilot_thickness':4.2,'head_standoff_at_contact':.8},4.2,[screw(p,[0,0,-1],5,2,4,1.72) for p in pts],[o for o in trunk if o[0]!='imu_holder'],contact_plane_z_mm=29.5)
# Printed-stock empty small-regulator cover may optionally be retained.
smallcover=obj('empty_small_regulator_cover',W/'assembly/compact-battery/small-regulator-cover-body.stl')
pts=[[x,7,z] for x in [-16.8,8.8] for z in [4.3,30.7]]
add('optional_empty_cover','Empty small-regulator pocket cover',4,'M2 x 12 into plastic pilot; no nuts',pts,[0,-1,0],{'cover':1.2,'pilot_boss':12.4},10.8,[screw(p,[0,-1,0],12,2,4,1.72) for p in pts],[o for o in trunk if o[0]!='support']+[smallcover],tip_to_boss_end_mm=1.6,conditional='Excluded from current installed design: old small regulator absent; retained printed stock only; old bottom screw heads collide hip motors')
optional_cover_length_screen=[]
for length in [3,6,12]:
 ss=[screw([x,7,4.3],[0,-1,0],length,2,4,1.72) for x in [-16.8,8.8]]
 optional_cover_length_screen.append({'length_mm':length,'checks':check_shapes(ss,[o for o in trunk if o[0]!='support'])})
# Header-length tolerance screen at existing pin center; no model modification.
header_length_checks=[]
pi_shapes=[screw([x,y,-59.21],[0,0,-1],6,2.5,4,1.5) for x in [3.935,26.935] for y in [-29.011,28.989]]
for length in [52,54,55]:
 m=box([3.935,-.011,-51.71],[7,length,15]);checks=check_shapes(pi_shapes,[('housing',m,man(m))]);header_length_checks.append({'housing_xyz_mm':[7,length,15],'screw_head_diameter_mm':4,'nominal_end_gap_mm':29-length/2-2,'checks':checks,'positive_clearance':29-length/2-2>0})
# Hex nut and washer envelopes, separately checked against current solids.
def nut(center,axis,af,h,thread):
 m=trimesh.creation.cylinder(radius=af/np.sqrt(3),height=h,sections=6);n=man(m)-cylinder([0,0,0],thread/2,h+1);t=trimesh.geometry.align_vectors([0,0,1],axis);t[:3,3]=center;return n.transform(t[:3])
nut_groups={}
nut_groups['openrb']=[nut([41,y,z],[1,0,0],4,1.6,2) for y in [-10.25,10.25] for z in [-48.75,12.75]]
nut_groups['audio_carrier']=[nut([41,y,23],[1,0,0],4,1.6,2) for y in [-36,36]]
nut_groups['camera_pcb_10']=[nut([x,y,.85],[0,0,1],4,1.6,2).transform(CT[:3]) for x,y in [(2,2),(23,2),(2,14.5),(23,14.5)]]
nut_groups['camera_foot']=[nut([39.55,y,-37.84501011669636],[1,0,0],5.5,2.4,3) for y in [-11,11]]
nut_groups['camera_hinge']=[nut((CF@np.array([9.7,0,11,1]))[:3],CF[:3,:3]@np.array([1,0,0]),5.5,2.4,3)]
nut_groups['fuse_carrier']=[nut([x,y,-52.7],[0,0,1],4,1.6,2) for x in [-54.931,-16.069] for y in [-12.7,12.7]]
for c in connections:
 if c['id'] in nut_groups:
  c['nut_collision_checks']=check_shapes(nut_groups[c['id']],trunk if c['id']=='fuse_carrier' else headobs)
  c['passed']=c['passed'] and all(not v['collisions'] for v in c['nut_collision_checks'])
washer_groups={}
def washer(center,axis):
 w=cylinder([0,0,0],3.5,.5)-cylinder([0,0,0],1.6,1);t=trimesh.geometry.align_vectors([0,0,1],axis);t[:3,3]=center;return w.transform(t[:3])
washer_groups['camera_foot']=[washer([45.91671433493411,y,-37.84501011669636],[1,0,0]) for y in [-11,11]]
washer_groups['camera_hinge']=[washer((CF@np.array([x,0,11,1]))[:3],CF[:3,:3]@np.array([1,0,0])) for x in [-8.25,8.25]]
for c in connections:
 if c['id'] in washer_groups:
  c['washer_collision_checks']=check_shapes(washer_groups[c['id']],headobs)
  c['passed']=c['passed'] and all(not v['collisions'] for v in c['washer_collision_checks'])
# Check longer camera PCB fasteners through accepted0..15degree downward pitch.
from scipy.spatial.transform import Rotation
pitch_checks=[]
ss=[screw(p,axis,10,2,4,1.72) for p in [(CT@np.r_[q,1])[:3].tolist() for q in localpts]]
for deg in [0,5,10,15]:
 t=np.eye(4);t[:3,:3]=Rotation.from_euler('x',deg,degrees=True).as_matrix();pivot=np.array([0,0,11]);t[:3,3]=pivot-t[:3,:3]@pivot;move=CF@t@np.linalg.inv(CF)
 pitch_checks.append({'degrees':deg,'checks':check_shapes([q.transform(move[:3]) for q in ss],[o for o in headobs if o[0] not in ['camera_module3_wide_assembly','camera_cradle_assembly']])})
for p in [Path(__file__),H/'build_head_electronics.py',H/'export_head_manifest.py',W/'assembly/build_trunk_imu.py',W/'assembly/build_compact_battery.py',P/'assembly/build_service_mounts.py',S/'hardware-design-20260912/camera/build_camera_mount.py',P/'procurement/sources/harf-pi-screws.html']:
 sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
# Whole legacy fastener reference vs actual current cap, including every existing head.
ref=load(F/'head_fastener_reference_assembly.stl');wholecap=max(0.,float((man(ref)^cap[2]).volume()))
# Derive full-nut result, without silently accepting partial engagement.
recommended=[c for c in connections if c['id'] not in ['camera_pcb_8','pi_old_max_head','optional_empty_cover']]
result={'verified_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'problem_ids':['P5','P6'],'scope':'Selected current electronics/fuse mount screws; obsolete empty cover rejected separately. Static smooth-shaft/head geometry + documented dimensional stacks; not robot joints or physical commissioning','connections':recommended,'optional_connections':[c for c in connections if c['id']=='optional_empty_cover'],'obsolete_cover_length_screen':optional_cover_length_screen,'negative_cases':[c for c in connections if c['id'] in ['camera_pcb_8','pi_old_max_head']],'camera_M2x10_pitch_checks':pitch_checks,'header_length_checks':header_length_checks,'primary_dimension_sources':[{'url':'https://datasheets.raspberrypi.com/camera/camera-module-3-wide-mechanical-drawing.pdf','verified_at':'2026-09-26','pcb_thickness_mm':1.12},{'file':'procurement/sources/harf-pi-screws.html','sku':'a16060200ux0367','head_diameter_mm':4,'head_height_mm':1.5}],'current_cap_vs_original_head_fastener_reference_intersection_mm3':wholecap,'source_hashes':sources,'head_closure_native_verification':{'path':str(closure_path),'sha256':hashlib.sha256(closure_path.read_bytes()).hexdigest(),'passed':closure_evidence['passed']},'negative_case_ids':['pi_old_max_head','camera_pcb_8'],'non_screw_retention':[{'component':'DFR1202 in open insert','method':'existing two4.8mm support bands; insulating edge liner and removable narrow ties; no screw holes','screw_quantity':0,'evidence':'mechanical_geometry_check.py; board box8x26x30 and carrier inside original battery envelope; component-detail CAD unavailable so receiving component/tie placement remains physical'},{'component':'MAX98357A and speaker','method':'two loops per component/four loops total, eight short ties; insulation under amp; speaker rim restrained, diaphragm free','screw_quantity':0},{'component':'BNO085 board','method':'retained by cavity and rear cover; two clamp screws attach holder to support rails','screw_quantity':0}],'obsolete_excluded':[{'item':'Alarm carrier','action':'removed; replace rearcover M2x8 with original M2x6; do not remove rearcover screws'},{'item':'Old D42V110F5 board','action':'removed; retain four M2x20 and nuts for fuse carrier; stack shorter1.6mm'},{'item':'Small regulator cover M2x12 x4','action':'Old small regulator absent; do not install empty pocket cover: two lower M2 heads collide hip servo envelopes. Retained printed stock is not current installed hardware; four M2x12 excluded with this accessory.'}],'findings':[{'id':'camera_M2x8_partial_nut','original_spec':'M2x8','remaining_unreached_nut_mm':.27,'action':'M2x10 selected: full1.6mm nut engagement; static and0..15degree head/cap collision checks pass','modeled_full_nut_engagement_8mm':False}],'passed':all(c['passed'] for c in recommended) and wholecap<.001 and all(not r['collisions'] for p in pitch_checks for r in p['checks']),'limits':['Pi selected4mm head has1mm nominal end clearance only with housing and wire exits constrained to7x52x15mm at documentedcenter; genericclubstock not yet verified','No threads modeled; plastic pilot thread/torque require printed first article','Nut engagement uses1.6mm M2/2.4mm M3 nominal thickness; actual nut must match','DFR1202 component details absent; ties must avoid exposed pads/chips','Static electronics review does not certify joint-fastener counts or physical assembly']}
(O/'electronics-fasteners.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'connections':[{k:r[k] for k in ['id','passed','evidence']} for r in connections],'current_cap_intersection':wholecap},indent=2))

sys.exit(0 if result['passed'] and all(not r['passed'] for r in result['negative_cases']) else 1)
