"""Sim only. Stand (open-loop STAND, then stand61 at zero command) with extra head mass, plus the neck servo's gravity load."""
import json, os, sys
HERE = '/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac/stand-pose-study-20261020'
sys.path.insert(0, HERE)
import stand_sim as S
import mujoco, numpy as np

out = {}
# neck load from the model with the robot's STAND pose, feet flat: head subtree mass and its lever about the neck pitch joint
m, d, c, names, bam = S._load(400, S.REAL_VOLT, None, 0.0, False)
mujoco.mj_forward(m, d)
bodies = [m.body(i).name for i in range(m.nbody)]
joints = [m.joint(i).name for i in range(m.njnt)]
out['bodies'] = bodies; out['joints'] = joints
masses = {b: float(m.body_mass[m.body(b).id]) for b in bodies}
out['mass_total_kg'] = float(m.body_subtreemass[0])
info = {}
for jn in joints:
    if any(k in jn.lower() for k in ('neck', 'head')):
        j = m.joint(jn); b = m.body(m.jnt_bodyid[j.id])
        sub = float(m.body_subtreemass[b.id]); com = d.subtree_com[b.id]; anchor = d.xanchor[j.id]; axis = d.xaxis[j.id]
        r = com - anchor; lever = np.cross(axis, r)   # torque = m g * |component of r perpendicular to axis and to gravity|
        tau = sub * 9.81 * float(np.linalg.norm(np.cross(axis, np.cross(r, [0, 0, 1.0]))))
        info[jn] = dict(child_body=b.name, subtree_mass_kg=round(sub, 4), com_minus_anchor_m=[round(float(x), 4) for x in r],
                        axis=[round(float(x), 3) for x in axis], gravity_torque_Nm=round(tau, 4))
out['neck_joints'] = info
out['head_part_masses_g'] = {b: round(masses[b] * 1000, 1) for b in bodies if any(k in b.lower() for k in ('head', 'jaw', 'neck', 'cap', 'cam', 'pi'))}
pi_world = d.xpos[m.body('jaw_soft').id] + d.xmat[m.body('jaw_soft').id].reshape(3, 3) @ np.array(S.PI_POS)
out['pi_pos_world_m'] = [round(float(x), 4) for x in pi_world]
for jn, v in info.items():
    j = m.joint(jn); anchor = d.xanchor[j.id]; axis = d.xaxis[j.id]; r = pi_world - anchor
    v['added_50g_torque_Nm'] = round(0.05 * 9.81 * float(np.linalg.norm(np.cross(axis, np.cross(r, [0, 0, 1.0])))), 4)
    v['pi_minus_anchor_m'] = [round(float(x), 4) for x in r]
print(json.dumps({k: out[k] for k in ('mass_total_kg', 'neck_joints', 'head_part_masses_g', 'pi_pos_world_m')}, indent=1), flush=True)

runs = []
for head_g in (0, 50, 60):
    for seed in (0, 1):
        r = S.run_case(dict(S.STAND_OBJ), head_g=head_g, T=30.0, walk_at=12.0, walk_s=15.0, seed=seed)
        rec = dict(head_g=head_g, seed=seed, fell_at=r.get('fell_at'), max_tilt=r.get('max_tilt'), max_tilt_after=r.get('max_tilt_after'),
                   keys=[k for k in r if k not in ('trace',)])
        print(json.dumps(rec), flush=True); runs.append(rec)
out['runs'] = runs
json.dump(out, open('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/af2b4ebd-4f58-4a8c-aad9-7f6bf8357bec/scratchpad/head_mass_sim.json', 'w'), indent=1)
