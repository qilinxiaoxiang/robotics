"""Bounded rigid-endpoint power/data harness reach screen; no flexible cable collision claim."""
from pathlib import Path
import json,sys,itertools,numpy as np,mujoco,trimesh
O=Path(__file__).resolve().parent;P=O.parent;OLD=P.parent/'hardware-design-20260912/whole-robot-20260912';sys.path.insert(0,str(OLD/'assembly'))
from assembly_fk import fk,raw,XML
IDS={('trunk_base',4):10,('trunk_base',9):5,('yaw2roll',1):9,('upper_leg_left',1):7,('upper_leg_left',4):8,('leg',2):6,('neck',1):12,('neck',2):11,('yaw_roll_motion',1):13,('jaw_soft',2):15,('jaw_soft',7):14,('bearing_roll',1):4,('upper_leg_right',0):2,('upper_leg_right',4):3,('leg_2',0):1}
GROUPS=[[1,2],[3,4],[5,10],[6,7],[8,9],[11,12],[13,14],[15]]
CHAIN=[0,15,14,13,11,12,5,4,3,2,1,6,7,8,9,10]
M=mujoco.MjModel.from_xml_path(str(XML));D=mujoco.MjData(M);rid=M.body('trunk_base').id
traj=Path(json.loads((O/'harness-reach-review.json').read_text())['trajectory']);rows=json.loads(traj.read_text())['rows']
parts={}
for g in fk()[1]:
 if g['mesh']!='xl330':continue
 m=raw(g['mesh']).apply_transform(g['local']);parts[IDS[(g['body'],g['index'])]]=(g['body'],np.array(list(itertools.product(*zip(m.bounds[0],m.bounds[1])))))
rb=trimesh.load(OLD/'electrical/head-layout/final/openrb_actual_box_proxy_assembly.stl',force='mesh');parts[0]=('jaw_soft',np.array(list(itertools.product(*zip(rb.bounds[0],rb.bounds[1])))))
fuses=json.loads((P/'assembly/service-mounts/design.json').read_text())['fuses']
group_results=[]
for i,ids in enumerate(GROUPS):
 # Physical slot1=F0 main, slot2=F1, etc. Head feeds leave upward; legs leave their own side.
 c=np.array(fuses[i+1]['center_mm']);d=np.array(fuses[i+1]['envelope_mm'])/2;corners=np.array(list(itertools.product(*zip(c-d,c+d))))
 anchor=np.array([-20.,0,35]) if i>=5 else np.array([-20.,(-30 if i in [0,1] else 30 if i in [3,4] else 0),-20.])
 group_results.append({'fuse':f'F{i+1}','servo_ids':ids,'physical_fuse_slot':i+2,'fuse_center_trunk_mm':c.tolist(),'trunk_route_anchor_mm':anchor.tolist(),'y_shift_toward_trunk_anchor_mm':20 if i==6 else 30 if i==7 else 0,'feed_via_anchor_to_y_max_mm':0.,'fuse_box_to_servo_direct_max_mm':0.,'y_to_servo_box_max_mm':{str(k):0. for k in ids},'_corners':corners,'_anchor':anchor})
links=[{'from':a,'to':b,'max_all_box_corner_distance_mm':0.} for a,b in zip(CHAIN[:-1],CHAIN[1:])]
ankle_bridge_via_leg_centers_max=0.
for row in rows:
 D.qpos[:]=row['qpos'];mujoco.mj_forward(M,D);R=D.xmat[rid].reshape(3,3);p=D.xpos[rid]*1000;world={}
 for sid,(body,corners) in parts.items():
  bi=M.body(body).id;H=R.T@D.xmat[bi].reshape(3,3);hp=R.T@(D.xpos[bi]*1000-p);world[sid]=corners@H.T+hp
 for g in group_results:
  ids=g['servo_ids'];y=np.mean([world[i].mean(0) for i in ids],axis=0);anchor=g['_anchor'];y=y+(anchor-y)/np.linalg.norm(anchor-y)*g['y_shift_toward_trunk_anchor_mm'];feed=float(np.max(np.linalg.norm(g['_corners']-anchor,axis=1))+np.linalg.norm(anchor-y))
  if feed>g['feed_via_anchor_to_y_max_mm']:g['feed_via_anchor_to_y_max_mm']=feed;g['worst_feed_time_s']=row['time'];g['worst_y_trunk_mm']=y.tolist()
  for sid in ids:
   tail=float(np.max(np.linalg.norm(world[sid]-y,axis=1)));direct=float(np.max(np.linalg.norm(g['_corners'][:,None,:]-world[sid][None,:,:],axis=2)))
   g['y_to_servo_box_max_mm'][str(sid)]=max(g['y_to_servo_box_max_mm'][str(sid)],tail);g['fuse_box_to_servo_direct_max_mm']=max(g['fuse_box_to_servo_direct_max_mm'],direct)
 bridge_tour=[1,2,3,5,10,8,7,6];bridge_centers=[world[q].mean(0) for q in bridge_tour]
 bridge=float(np.max(np.linalg.norm(world[1]-bridge_centers[1],axis=1))+sum(np.linalg.norm(a-b) for a,b in zip(bridge_centers[1:-2],bridge_centers[2:-1]))+np.max(np.linalg.norm(world[6]-bridge_centers[-2],axis=1)))
 ankle_bridge_via_leg_centers_max=max(ankle_bridge_via_leg_centers_max,bridge)
 for link in links:
  dist=float(np.max(np.linalg.norm(world[link['from']][:,None,:]-world[link['to']][None,:,:],axis=2)))
  if dist>link['max_all_box_corner_distance_mm']:link['max_all_box_corner_distance_mm']=dist;link['worst_time_s']=row['time']
for g in group_results:
 del g['_corners'];del g['_anchor']
 g['inherited_150mm_feed_after_20mm_prefuse_and_40mm_service_mm']=90
 g['inherited_150mm_feed_passed']=g['feed_via_anchor_to_y_max_mm']<=90
 g['selected_feed_total_mm']=250
 g['selected_feed_available_after_20mm_prefuse_and_40mm_service_mm']=190
 g['selected_feed_passed']=g['feed_via_anchor_to_y_max_mm']<=190
 g['factory_tail_length_mm']=90;g['tail_service_allowance_mm']=30;g['tails_passed']=max(g['y_to_servo_box_max_mm'].values())<=60
for link in links:
 link['service_and_splice_allowance_mm']=30;link['original_180mm_passed']=link['max_all_box_corner_distance_mm']<=150
 link['selected_total_data_length_mm']=180 if link['original_180mm_passed'] else 250
 link['ordinary_data_wire_extension_mm']=link['selected_total_data_length_mm']-180
 if (link['from'],link['to'])==(1,6):
  link['route']='Follow right ankle-to-knee-to-hip links, cross fixed torso, then descend left leg; no free cable bridge between ankles'
  link['routed_via_leg_centers_max_mm']=ankle_bridge_via_leg_centers_max
  link['selected_total_data_length_mm']=400
  link['ordinary_data_wire_extension_mm']=220
  link['negative_350mm_routed_bridge_rejected']=ankle_bridge_via_leg_centers_max+30>350
 link['selected_passed']=link.get('routed_via_leg_centers_max_mm',link['max_all_box_corner_distance_mm'])+30<=link['selected_total_data_length_mm']
result={'trajectory':str(traj),'samples':len(rows),'servo_count':15,'scope':'Model kinematics with every rigid servo-case corner as conservative unknown connector endpoint; no exact connector or flex-wire collision simulation. Group Y follows group case-center midpoint with a supported loose arc, never attached to shaft. Fuse physical slots2-9 carry F1-F8.','power_groups':group_results,'data_chain':CHAIN,'ankle_bridge_routed_path_servo_centers':[1,2,3,5,10,8,7,6],'data_links':links,'zero_means':'OpenRB head-mounted proxy box','power_passed':all(g['selected_feed_passed'] and g['tails_passed'] for g in group_results),'data_passed':all(x['selected_passed'] for x in links),'routing':'Keep DATA-only continuity, individual motor VDD/GND return paths. Arrange Y near midpoint between adjacent pair cases; anchor feed to fixed torso at listed waypoint then use articulated service arc. Do not tighten Y to a moving output horn. Route same-leg links along links with slack around pivots. Extend DATA only on1-to6 to400mm finished length and follow right leg up through torso and left leg down; never leave a loose direct bridge between ankles. Final physical snag check remains required.','physical_tests':0}
result['passed']=result['power_passed'] and result['data_passed']
(O/'motor-harness-reach.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));sys.exit(0 if result['power_passed'] and result['data_passed'] else 1)
