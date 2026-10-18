"""Verify selected mechanical joint fasteners against native source meshes and ROBOTIS CAD.
Run audit_motor_interfaces.py, measure_joint_stacks.py, audit_case_candidates.py,
audit_passive_centers.py, verify_manufacturer_geometry.py to regenerate inputs.
"""
from pathlib import Path
import json,hashlib,collections,numpy as np,subprocess,sys
O=Path(__file__).resolve().parent
if '--cached-inputs' not in sys.argv:
 for script in ['audit_motor_interfaces.py','measure_joint_stacks.py','audit_case_candidates.py','audit_passive_centers.py','verify_manufacturer_geometry.py','refine_jaw_head_seats.py']:
  result=subprocess.run([sys.executable,str(O/script)],capture_output=True,text=True)
  if result.returncode:print(result.stdout,result.stderr);raise SystemExit(result.returncode)
  print('Native geometry refreshed:',script,flush=True)
load=lambda n:json.loads((O/n).read_text())
manufacturer=load('manufacturer-geometry.json');assert manufacturer['passed']
sections=load('motor-interface-sections.json');stacks=load('joint-stack-measurements.json')['connections'];cases=load('all-case-candidates.json')['candidates'];passives=load('passive-centers.json')['motor_centers']
ids={('trunk_base',4):10,('trunk_base',9):5,('yaw2roll',1):9,('upper_leg_left',1):7,('upper_leg_left',4):8,('leg',2):6,('neck',1):12,('neck',2):11,('yaw_roll_motion',1):13,('jaw_soft',2):15,('jaw_soft',7):14,('bearing_roll',1):4,('upper_leg_right',0):2,('upper_leg_right',4):3,('leg_2',0):1}
transforms={(m['motor_body'],m['motor_index']):np.array(m['motor_world_transform']) for m in sections['motors']}
connections=[]
def append(key,kind,component,side,yz,seat,length,diam,collar=0,washer=0,source_ids=None,detail=None):
 sid=ids[key];T=transforms[key];datum=14.5 if kind=='horn' else 11.5
 penetration=[round(length-seat[1]-washer,5),round(length-seat[0]-washer,5)]
 if kind=='horn':passed=penetration[0]>1.6 and penetration[1]<=3.01;eng=penetration
 elif kind=='case':eng=[round(x-collar,5) for x in penetration];passed=eng[0]>=2.19 and penetration[1]<collar+15
 else:
  # Rear center pilot is x6.3..9.5; seat is an absolute motor-local x.
  tip=[seat[0]+washer-length,seat[1]+washer-length];eng=[round(9.5-tip[1],5),round(9.5-tip[0],5)];passed=min(tip)>=6.3-.01 and min(eng)>=1.5
  penetration=[round(11.5-tip[1],5),round(11.5-tip[0],5)]
 point=(T@np.array([side*(datum+np.mean(seat)) if kind!='rear_center' else np.mean(seat),*yz,1]))[:3]
 r=dict(id=f'S{sid:02d}-{kind}-{len(connections)+1:03d}',component=component,servo_ids=[sid],category=kind,quantity=1,spec=f'M{diam} x {length} TAP',length_mm=length,side=side,hole_centers_mm=[[side*datum,*yz]],frame=f'{key[0]}:xl330:{key[1]} local; Xshaft/Ywidth/Zheight; negativeXactivehorn',axis=[side,0,0],world_center_mm=point.tolist(),world_axis=(T[:3,:3]@np.array([side,0,0])).tolist(),stack_mm=seat,clearance_collar_mm=collar,washer_mm=washer,washer_spec='DIN433/ISO7092 M2.5 ID2.7 OD5 thickness0.5 metal' if washer else None,penetration_mm=penetration,engagement_mm=eng,source_ids=source_ids or [],passed=bool(passed),evidence=detail)
 connections.append(r)
for r in stacks:
 if r['kind']!='output':continue
 key=(r['motor_body'],r['motor_index']);seat=r['head_seat_from_motor_face_mm']
 if key==('jaw_soft',2):
  exact=next(x for x in load('jaw-head-seats.json')['seats'] if x['yz']==r['yz']);seat=[exact['seat_mm'],exact['seat_mm']]
 length=max(n for n in [4,5,6,7] if n-seat[0]<=3.01)
 append(key,'horn',r['part'],r['side'],r['yz'],seat,length,2,source_ids=[r['source_id']],detail='Actualcommunity3MF closedbore, eightnative triangleintersections at radius1.5mm; subtract active/idlerhorn surface14.5mm; manufacturerDP3.0Max; 0.01mm is mesh numeric tolerance, not physical printer tolerance.')
# Circle-detected case bores plus one open side-shell slot confirmed by 7/8 rays.
valid={(r['motor_body'],r['motor_index'],r['side'],tuple(r['yz'])) for r in stacks if r['kind']=='case'}
valid.add(('trunk_base',9,1,(8,7.5)))
for r in cases:
 key=(r['motor_body'],r['motor_index']);location=(*key,r['side'],tuple(r['yz']))
 if location not in valid:continue
 parts=r['parts'];assert parts,location
 outer=[max(p['outer_face_range_mm'][i] for p in parts) for i in [0,1]];seat=[x-11.5 for x in outer];collar=3.5 if r['side']==-1 else 4.5
 length=next(n for n in [6,8,10,12] if n-seat[1]-collar>=2.2-1e-5)
 append(key,'case',' + '.join(p['part'] for p in parts),r['side'],r['yz'],seat,length,2,collar,source_ids=[p['source_id'] for p in parts if p['source_id']],detail='All120casecorneraxes surveyed. Exactradialrays combine stacked parts. Manufacturer15mm tapregion after3.5front/4.5rearclearancecollar; selected minimum2.2mm threadedengagement equals officialFPX330S101 rear example.')
# Integrated centers, not extra idler horn/cap assemblies.
for r in passives:
 key=(r['motor_body'],r['motor_index']);sid=ids[key]
 for c in r['integral_retainer_candidates']:
  washer=.5 if sid in [1,4,6,9] else 0;length=8 if sid in [1,6] else 6
  append(key,'rear_center',c['component']+' integrated rear retainer',1,[0,0],c['seat_mm'],length,2.6,washer=washer,source_ids=[c['source_id']],detail='16exacttriangleintersectionraysatradius1.6 aroundintegralrearcenter. ManufacturerrearØ2.2pilotx6.3..9.5; selectedtipstayinsidethispilot. No separateprintedidlerhorn/cap here.')
for key in [('neck',1),('neck',2)]:append(key,'rear_center','Separate printed idler horn + cap',1,[0,0],[12.7,12.7],6,2.6,source_ids=[55,59],detail='ManufacturerCAD rearidlercap screw-bearingplanez−20.7 mapsx12.7; sourceprint horn/cap match dimensions and assembly. Onlytwo double-sidedneck stations require separatehorn/cap.')
# Opposed case screws must not meet; locating pegs remain separate.
case_by_axis=collections.defaultdict(list)
for c in connections:
 if c['category']=='case':case_by_axis[(c['servo_ids'][0],tuple(c['hole_centers_mm'][0][1:]))].append(c)
clearances=[]
for k,v in case_by_axis.items():
 if len(v)==2:
  clearance=23-sum(x['penetration_mm'][1] for x in v);assert clearance>0
  clearances.append({'servo_id':k[0],'yz':k[1],'tip_gap_mm':clearance})
pegs={(ids[(m['motor_body'],m['motor_index'])],h['side'],tuple(h['yz'])) for m in sections['motors'] for h in m['holes'] if h['kind']=='locating_peg'}
counts=collections.Counter(c['spec'] for c in connections);washer_count=sum(c['washer_mm']>0 for c in connections)
report=dict(passed=all(c['passed'] for c in connections),scope='Digital geometry, per-station installation quantities and screw selection. No physical fit, clamp torque, fatigue or strength claim.',motor_count=15,covered_servo_ids=sorted(set(s for c in connections for s in c['servo_ids'])),hole_counts={'horn':sum(c['category']=='horn' for c in connections),'case':sum(c['category']=='case' for c in connections),'rear_center':sum(c['category']=='rear_center' for c in connections)},integral_locating_pegs=len(pegs),standalone_idler_horns_installed=2,standalone_idler_caps_installed=2,printed_horn_cap_stock_each=14,printed_horn_cap_spares_each=12,fastener_totals=dict(counts),small_washers=washer_count,connections=connections,opposed_case_tip_clearance=clearances,source_hashes={str(p.relative_to(O)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list((O/'sources').glob('*'))+[O/'motor-interface-sections.json',O/'joint-stack-measurements.json',O/'all-case-candidates.json',O/'passive-centers.json',O/'manufacturer-geometry.json']},unverified_physical=['Printed bore tolerance and support cleanup','Hand-tight clamp test and free rotation','Real fastener head dimensions and thread form match specified TAP'])
assert report['hole_counts']=={'horn':68,'case':40,'rear_center':10},report['hole_counts']
assert len(pegs)==16
from evidence_sources import hashes, assembly_sources
source_scripts = ['verify_joint_fasteners.py','audit_motor_interfaces.py','measure_joint_stacks.py','audit_case_candidates.py','audit_passive_centers.py','verify_manufacturer_geometry.py','refine_jaw_head_seats.py','verify_retainer_clearance.py','verify_screw_heads.py']
A=O.parents[1]/'assembly'; S=O.parents[2]
report['source_hashes'].update(hashes(assembly_sources()+[O/n for n in source_scripts]+[
 O/'jaw-head-seats.json', A/'prepare_geometry.py', A/'inspect_joint_interfaces.py',
 A/'community-print-inventory.json', A/'source-surface-refinement.json',
 S/'Microduck-build-tutorial/microduck3D打印.3mf',
 A/'mouth-support/motor-support-coaxial-assembly.stl',
 S/'hardware-design-20260912/whole-robot-20260912/assembly/compact-battery/power-support-integrated-body.stl']))
report['source_hashes'].update({str(p.relative_to(O.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [O.parent/'current-print-queue.3mf',O.parent/'print-manifest.json']})
(O/'joint-fasteners.json').write_text(json.dumps(report,indent=2))
if '--cached-inputs' not in sys.argv:
 for script,artifact in [('verify_retainer_clearance.py','retainer-clearance.json'),('verify_screw_heads.py','screw-head-clearance.json')]:
  result=subprocess.run([sys.executable,str(O/script)],capture_output=True,text=True)
  if result.returncode:print(result.stdout,result.stderr);raise SystemExit(result.returncode)
  result_data=load(artifact);assert result_data['passed'],result_data
  report['source_hashes'][artifact]=hashlib.sha256((O/artifact).read_bytes()).hexdigest()
  print('Native clearance verified:',script,flush=True)
 report['clearance_checks_passed']=True
 (O/'joint-fasteners.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ['connections','source_hashes','opposed_case_tip_clearance']},indent=2));assert report['passed']
