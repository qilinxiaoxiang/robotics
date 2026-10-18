import sys, numpy as np, mujoco, trimesh, pickle; sys.path.insert(0,'.')
from common import *
import legsweep as L
s=scene(); print('scene keys', len(s)); 
for k in sorted(s): 
    v=s[k]['v']; print(f'{k:22s}', np.round(v.min(0),1).tolist(), np.round(v.max(0),1).tolist())
M=L.M; D=L.D; D.qpos[:]=M.qpos0; mujoco.mj_kinematics(M,D)
tb=M.body('trunk_base').id; R0=D.xmat[tb].reshape(3,3); p0=D.xpos[tb]
print('--- MJCF mesh geoms at qpos0 in trunk frame (mm)')
for g in range(M.ngeom):
    b=M.body(M.geom_bodyid[g]).name
    if M.geom_type[g]!=mujoco.mjtGeom.mjGEOM_MESH: continue
    if M.geom_contype[g]==0 and M.geom_conaffinity[g]==0: tag='vis'
    else: tag='col'
    mid=M.geom_dataid[g]; va,vn=M.mesh_vertadr[mid],M.mesh_vertnum[mid]; v=M.mesh_vert[va:va+vn]
    W=v@D.geom_xmat[g].reshape(3,3).T+D.geom_xpos[g]; X=(W-p0)@R0*1000
    if b in ('trunk_base','yaw2roll','hip_l','upper_leg_left','leg','ankle_left','foot_left'):
        print(f'{b:16s} {M.mesh(mid).name:24s} {tag}', np.round(X.min(0),1).tolist(), np.round(X.max(0),1).tolist())
print('qpos0 leg', {M.joint(j).name: float(M.qpos0[M.jnt_qposadr[j]]) for j in range(M.njnt) if 'left' in M.joint(j).name})
