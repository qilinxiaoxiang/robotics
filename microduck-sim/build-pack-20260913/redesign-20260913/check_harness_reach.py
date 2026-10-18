from pathlib import Path
import json,numpy as np,mujoco,sys,itertools
O=Path(__file__).resolve().parent;P=O.parent;OLD=P.parent/'hardware-design-20260912/whole-robot-20260912';sys.path.insert(0,str(OLD/'assembly'))
from assembly_fk import XML
traj=Path(json.loads((O/'mechanical-geometry-verification.json').read_text())['trajectory']);rows=json.loads(traj.read_text())['rows'];M=mujoco.MjModel.from_xml_path(str(XML));D=mujoco.MjData(M)
rid=M.body('trunk_base').id;hid=M.body('jaw_soft').id;data=[]
for row in rows:
 D.qpos[:]=row['qpos'];mujoco.mj_forward(M,D);R=D.xmat[rid].reshape(3,3);p=D.xpos[rid]*1000
 H=R.T@D.xmat[hid].reshape(3,3);hp=R.T@(D.xpos[hid]*1000-p)
 gpio=H@np.array([3.935,-.011,-53.21])+hp
 regulator=np.array([-35.5,0,-14.]);imu=np.array([-57,0,15.]);neck_base_anchor=np.array([-20.,0,35.])
 direct=float(np.linalg.norm(gpio-regulator));imu_direct=float(np.linalg.norm(gpio-imu));route=float(np.linalg.norm(regulator-neck_base_anchor)+np.linalg.norm(neck_base_anchor-gpio))
 corners=[H@np.array([x,y,-53.21])+hp for x in [2.665,5.205] for y in [-25.411,25.389]]
 housing_corners=[H@np.array(q)+hp for q in itertools.product([.435,7.435],[-26.011,25.989],[-59.21,-44.21])]
 regulator_corners=[np.array(q) for q in itertools.product([-39.5,-31.5],[-13,13],[-29,1])]
 imu_corners=[np.array(q) for q in itertools.product([-61,-53],[-14,14],[2.5,27.5])]
 worst_reg_source_to_anchor=max(float(np.linalg.norm(q-neck_base_anchor)) for q in regulator_corners)
 worst_imu_source_to_anchor=max(float(np.linalg.norm(q-neck_base_anchor)) for q in imu_corners)
 worst_anchor_to_housing=max(float(np.linalg.norm(q-neck_base_anchor)) for q in housing_corners)
 worst_gpio=max(float(np.linalg.norm(p-regulator)) for p in corners);worst_imu=max(float(np.linalg.norm(p-imu)) for p in corners)
 worst_route=max(float(np.linalg.norm(regulator-neck_base_anchor)+np.linalg.norm(neck_base_anchor-p)) for p in corners)
 data.append({'time':row['time'],'gpio_in_trunk_mm':gpio.tolist(),'regulator_to_gpio_direct_mm':direct,'imu_to_gpio_direct_mm':imu_direct,'regulator_via_trunk_anchor_to_gpio_mm':route,'regulator_to_any_gpio_corner_mm':worst_gpio,'imu_to_any_gpio_corner_mm':worst_imu,'anchor_route_to_any_gpio_corner_mm':worst_route,'regulator_box_to_anchor_to_gpio_housing_max_mm':worst_reg_source_to_anchor+worst_anchor_to_housing,'imu_box_to_anchor_to_gpio_housing_max_mm':worst_imu_source_to_anchor+worst_anchor_to_housing})
result={'trajectory':str(traj),'method':'Exact recorded MuJoCo body transforms; connector-center endpoints. Distances are lower bounds before slack and exact component lead exits.','regulator_center_trunk_mm':[-35.5,0,-14],'pi_gpio_reference_head_mm':[3.935,-.011,-53.21],'imu_reference_trunk_mm':[-57,0,15],'trunk_anchor_for_route_mm':[-20,0,35],'samples':len(data),'direct_regulator_gpio_range_mm':[min(x['regulator_to_gpio_direct_mm'] for x in data),max(x['regulator_to_gpio_direct_mm'] for x in data)],'imu_gpio_range_mm':[min(x['imu_to_gpio_direct_mm'] for x in data),max(x['imu_to_gpio_direct_mm'] for x in data)],'simple_anchor_route_range_mm':[min(x['regulator_via_trunk_anchor_to_gpio_mm'] for x in data),max(x['regulator_via_trunk_anchor_to_gpio_mm'] for x in data)],'100mm_gpio_leads_fit_direct_lower_bound':max(x['regulator_to_gpio_direct_mm'] for x in data)<=100,'150mm_imu_cable_fits_direct_lower_bound':max(x['imu_to_gpio_direct_mm'] for x in data)<=150,'maximum_direct_case':max(data,key=lambda x:x['regulator_to_gpio_direct_mm'])}
result['full_header_corner_direct_max_mm']=max(r['regulator_to_any_gpio_corner_mm'] for r in data)
result['full_header_corner_imu_direct_max_mm']=max(r['imu_to_any_gpio_corner_mm'] for r in data)
result['full_header_corner_anchor_route_max_mm']=max(r['anchor_route_to_any_gpio_corner_mm'] for r in data)
result['conservative_regulator_box_anchor_gpio_housing_route_max_mm']=max(r['regulator_box_to_anchor_to_gpio_housing_max_mm'] for r in data)
result['conservative_imu_box_anchor_gpio_housing_route_max_mm']=max(r['imu_box_to_anchor_to_gpio_housing_max_mm'] for r in data)
result['selected_lead_length_mm']=250
result['pi_supply_leads']='Four 22AWG leads, each250mm finished length'
result['imu_leads']='Four250mm leads: retain100mmJST cable tail and join150mm female-precrimp wire with individual heatshrink over joints; stagger and support joins outside flex arc'
result['service_and_termination_allowance_mm']=50
result['available_length_after_50mm_allowance_mm']=200
result['250mm_pi_lead_length_screen_passed']=result['conservative_regulator_box_anchor_gpio_housing_route_max_mm']<=200
result['250mm_imu_lead_length_screen_passed']=result['conservative_imu_box_anchor_gpio_housing_route_max_mm']<=200
result['routing_scope']='Length screen includes extreme full-header pin endpoints and, conservatively, every converter/IMU box corner and full7x52x15mm GPIO housing corner routed through fixed torso anchor. It reserves50mm beyond the longest two-segment route for bends/terminations. It does not simulate flexible wire collisions or prove actual routing.'
result['passed']=result['250mm_pi_lead_length_screen_passed'] and result['250mm_imu_lead_length_screen_passed'] and not result['100mm_gpio_leads_fit_direct_lower_bound'] and not result['150mm_imu_cable_fits_direct_lower_bound']
(O/'harness-reach-review.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

sys.exit(0 if result['passed'] else 1)
