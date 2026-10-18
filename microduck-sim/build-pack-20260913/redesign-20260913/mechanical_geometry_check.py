"""Regulator insert and bounded clearance recheck; canonical print queues are unchanged."""
from pathlib import Path
import sys,json,hashlib,itertools,time
import numpy as np,trimesh,manifold3d as md,mujoco
O=Path(__file__).resolve().parent; PACK=O.parent;SIM=PACK.parent
OLD=SIM/'hardware-design-20260912/whole-robot-20260912';C=OLD/'assembly/compact-battery'
sys.path.insert(0,str(OLD/'assembly'))
from assembly_fk import fk,raw,XML

def box(c,d):return trimesh.creation.box(d).apply_translation(c)
def solid(m):return md.Manifold(md.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def over(a,b):return np.all(a[1]>=b[0]) and np.all(b[1]>=a[0])
def union(ms):return trimesh.boolean.union(ms,engine='manifold')
def cub(x0,x1,y0,y1,z0,z1):return box([(x0+x1)/2,(y0+y1)/2,(z0+z1)/2],[x1-x0,y1-y0,z1-z0])
# Frame front is +X; the converter's two large faces remain predominantly open.
# An insulating edge liner and removable narrow ties retain the received board.
bits=[cub(-29.5,-28.3,-15.5,15.5,-35,26)]
# Remove central region to leave a 3 mm rim with two existing-band slots.
frame=trimesh.boolean.difference([bits[0],cub(-30,-28,-12,12,-26,1)],engine='manifold')
for z in [-30.821742128,5.877257872]:
    frame=trimesh.boolean.difference([frame,cub(-30,-28,-11,11,z-2.7,z+2.7)],engine='manifold')
# Shallow open pocket: board thickness X=8, width Y=26, length Z=30.
bits=[frame,cub(-40.7,-28.3,-14.5,14.5,-31,-29.6)]
for y0,y1 in [(-14.5,-13.3),(13.3,14.5)]:
    bits.append(cub(-40.7,-28.3,y0,y1,-31,3))
# Rear lip only at PCB edge, leaving main component and thermal-pad areas open.
for y0,y1 in [(-14.5,-11.5),(11.5,14.5)]:
    bits.append(cub(-40.7,-39.8,y0,y1,-31,3))
carrier=union(bits)
board=box([-35.5,0,-14],[8,26,30])
# New board/carrier sit inside the original 22 x 34 x 63 mm battery envelope.
carrier.export(O/'regulator-open-insert-body.stl');board.export(O/'dfr1202-envelope-body.stl')
pr=carrier.copy();pr.apply_transform(np.array([[0,-1,0,0],[0,0,1,0],[-1,0,0,0],[0,0,0,1]]));pr.apply_translation(-pr.bounds[0]);pr.export(O/'regulator-open-insert-print.stl')
components={'regulator_insert':carrier,'dfr1202_envelope':board}
# Existing installed fixed parts plus original moving rigid geometry.
base=[]
geom=json.loads((PACK/'phase1/simulation/geometry-manifest.json').read_text());removed=set(geom['remove_meshes'])
for g in fk()[1]:
    if g['mesh'] in removed:continue
    base.append((g['body']+'/'+g['mesh'],g['body'],raw(g['mesh']).apply_transform(g['local'])))
for row in geom['parts']:
    if row['body']=='trunk_base' or 'motor-support-coaxial' in row['mesh']:base.append((Path(row['mesh']).stem,row['body'],trimesh.load(row['mesh'],force='mesh')))
# Include restored camera/audio and revised cap in the same moving-head check.
HF=OLD/'electrical/head-layout/final'
for hp in json.loads((HF/'head-mesh-mass-manifest.json').read_text())['pieces']:
    if hp['id']=='pi_retained':continue
    q=Path(hp['mesh_file'])
    if hp['id']=='head_cap':q=O/'head-cap-usb-service-body.stl'
    hm=trimesh.load(q,force='mesh');HT=np.eye(4);HT[:3,:3]=hp['rotation_matrix'];HT[:3,3]=hp['position_mm'];hm.apply_transform(HT)
    base.append(('restored_head/'+hp['id'],hp['body'],hm))
base.append(('gpio_2x20_housing_and_exit_7x52x15','jaw_soft',box([3.935,-.011,-51.71],[7,52,15])))
for extra in ['camera_ribbon_keepout_assembly.stl']:
    q=HF/extra
    if q.exists():base.append((extra,'jaw_soft',trimesh.load(q,force='mesh')))
# Include actual clamp holder, omitted from old phase1 visual manifest but printed/installed.
p=OLD/'assembly/trunk-imu/imu_clamp_holder_body.stl'
base.append((p.stem,'trunk_base',trimesh.load(p,force='mesh')))
fixed=[]
for n,m in components.items():
    for name,body,ob in base:
        if body=='trunk_base' and over(m.bounds,ob.bounds):
            v=max(0.,float((solid(m)^solid(ob)).volume()))
            if v>.005:fixed.append({'new':n,'existing':name,'intersection_mm3':v})
board_v_carrier=max(0.,float((solid(board)^solid(carrier)).volume()))
traj=PACK/'phase1/simulation/candidate-kp300/phase1-candidate-old60-baseline.json'
if not traj.exists():traj=PACK/'phase1/simulation/phase1-candidate-old60-baseline.json'
data=json.loads(traj.read_text());rows=data['rows'];model=mujoco.MjModel.from_xml_path(str(XML));state=mujoco.MjData(model);rid=model.body('trunk_base').id
moving=[(name,body,m,solid(m),np.array(list(itertools.product(*zip(m.bounds[0],m.bounds[1]))))) for name,body,m in base if body!='trunk_base']
collisions=[];checks=0;boolean_count=0;frame_indices=np.unique(np.linspace(0,len(rows)-1,250,dtype=int));start=time.time()
for fi in frame_indices:
    row=rows[int(fi)];state.qpos[:]=row['qpos'];mujoco.mj_forward(model,state);R=state.xmat[rid].reshape(3,3);p=state.xpos[rid]*1000
    for name,body,m,sm,corners in moving:
        bi=model.body(body).id;T=np.eye(4);T[:3,:3]=R.T@state.xmat[bi].reshape(3,3);T[:3,3]=R.T@(state.xpos[bi]*1000-p)
        ps=corners@T[:3,:3].T+T[:3,3];bounds=np.array([ps.min(0),ps.max(0)])
        for n,new in components.items():
            checks+=1
            if not over(new.bounds,bounds):continue
            boolean_count+=1;v=max(0.,float((solid(new)^sm.transform(T[:3])).volume()))
            if v>.005:collisions.append({'time':row['time'],'new':n,'existing':name,'intersection_mm3':v})
# Live mesh readback for named reused parts.
read_paths=[C/'power-support-integrated-body.stl',C/'battery-max-envelope-body.stl',PACK/'assembly/print-parts/current/camera_pitch_foot.stl',PACK/'assembly/print-parts/current/camera_cradle.stl',PACK/'assembly/print-parts/current/audio_carrier_print.stl']
readbacks=[]
for p in read_paths:
    m=trimesh.load(p,force='mesh');readbacks.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'extents_mm':m.extents.tolist(),'watertight':bool(m.is_watertight),'solid_count':len(m.split())})
# Tether copper-only lower bound: insulation and data cables add weight.
copper_density=8.96;area_mm2=.823;drop_m=.35
wire_g=2*area_mm2*drop_m*1000*copper_density/1000
# Static sensitivity only; a specified payload does not establish balance.
base_mass_range=[.5,.7,.9];payload_mass_range=[.05,.15,.2,.25]
com_cases=[{'base_mass_kg':m,'payload_mass_kg':p,'payload_x_from_original_com_mm':-60,'new_com_shift_mm':-60*p/(m+p)} for m in base_mass_range for p in payload_mass_range]
battery=trimesh.load(C/'battery-max-envelope-body.stl',force='mesh')
result={'verified_at':'2026-09-13','problem_ids':['P5','P6'],'source_scope':'New DFR1202 supplier-box insertion and reused mesh readback; no physical acceptance','reused_meshes':readbacks,'regulator_position_trunk_mm':[-35.5,0,-14],'regulator_orientation_dimensions_xyz_mm':[8,26,30],'regulator_insert':{'body_file':str(O/'regulator-open-insert-body.stl'),'print_file':str(O/'regulator-open-insert-print.stl'),'extents_mm':carrier.extents.tolist(),'solid_pla_mass_upper_g':carrier.volume*.00124,'watertight':bool(carrier.is_watertight),'solid_count':len(carrier.split()),'board_inside_old_battery_envelope':bool(np.all(board.bounds[0]>=battery.bounds[0]) and np.all(board.bounds[1]<=battery.bounds[1])),'insert_inside_old_battery_envelope':bool(np.all(carrier.bounds[0]>=battery.bounds[0]) and np.all(carrier.bounds[1]<=battery.bounds[1])),'board_clearance_intersection_mm3':board_v_carrier},'fixed_collisions':fixed,'trajectory':str(traj),'trajectory_sha256':hashlib.sha256(traj.read_bytes()).hexdigest(),'sampled_frames':len(frame_indices),'pair_checks':checks,'exact_boolean_checks':boolean_count,'motion_collisions':collisions,'copper_only_35cm_18awg_pair_mass_g':wire_g,'copper_only_weight_N':wire_g/1000*9.80665,'hypothetical_payload_static_com_sensitivity':com_cases,'physical_tests':0,'limits':['Module weight and installed harness weight not published/measured','No component-detail CAD: final tie placement must avoid components and exposed pads','No measured converter thermal performance or heating of printed carrier','Sampled existing motion checks rigid fit only; newly added mass is not dynamically rerun','Future larger power bank dock is an interface extension, no selected pack has proven onboard fit'],'passed':not fixed and not collisions and board_v_carrier<.005 and carrier.is_watertight and len(carrier.split())==1}
(O/'mechanical-geometry-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['regulator_insert','fixed_collisions','sampled_frames','pair_checks','motion_collisions','copper_only_35cm_18awg_pair_mass_g','passed']},indent=2))

sys.exit(0 if result["passed"] else 1)
