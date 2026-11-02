import sys,os,numpy as np
MAC=os.path.expanduser('~/code/robotics/microduck-sim/guide/firmware/mac');sys.path.insert(0,MAC);os.chdir(MAC)
import mujoco,trimesh,target_ground as tg
from scipy.spatial import cKDTree
G=tg.DuckGeometry();m,d=G.m,G.d
def geoms(b):
    return [g for g in range(m.ngeom) if m.body(m.geom_bodyid[g]).name==b and m.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH and m.geom_group[g]<=2]
def pts(g,n=30000):
    mid=m.geom_dataid[g];va,na=m.mesh_vertadr[mid],m.mesh_vertnum[mid];fa,nf=m.mesh_faceadr[mid],m.mesh_facenum[mid]
    return trimesh.sample.sample_surface(trimesh.Trimesh(m.mesh_vert[va:va+na],m.mesh_face[fa:fa+nf],process=False),n,seed=3)[0]
for side,body,shin,jn,sg in (('left','ankle_left','leg','left_ankle',1),('right','ankle_right','leg_2','right_ankle',-1)):
    F=[(g,pts(g),m.geom(g).name.split('__')[-1]) for g in geoms(body)];Sh=[(g,pts(g),m.geom(g).name.split('__')[-1]) for g in geoms(shin)]
    j=m.joint(jn).id;fb=m.body(body).id
    d.qpos[:]=m.qpos0;mujoco.mj_kinematics(m,d)
    Pw=np.vstack([p@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g] for g,p,_ in F]);anc=d.xanchor[j].copy()
    print(side,'foot at q=0: x',(Pw[:,0].min()*1000).round(1),(Pw[:,0].max()*1000).round(1),'z',(Pw[:,2].min()*1000).round(1),'ankle axis x z',(anc[[0,2]]*1000).round(1))
    # foot points as they sit at q=0 in world; find which are closest to the shin at each q
    for q in (1.25,1.3,1.32,1.34,1.36,1.38,1.4,1.45,1.5,1.571):
        d.qpos[:]=m.qpos0;d.qpos[m.jnt_qposadr[j]]=q*sg;mujoco.mj_kinematics(m,d)
        Pf=np.vstack([p@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g] for g,p,_ in F]);lab=np.concatenate([[n]*len(p) for _,p,n in F])
        an=d.xanchor[j];ax=d.xaxis[j];rel=Pf-an;rad=np.linalg.norm(rel-np.outer(rel@ax,ax),axis=1);k=rad>0.016
        Ps=np.vstack([p@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g] for g,p,n in Sh if n=='servo'])
        dd,ii=cKDTree(Ps).query(Pf[k]);i=dd.argmin()
        near=Pw[k][dd<dd.min()+0.0005]
        print(f'  q {q:.3f} servo-to-foot {dd.min()*1000:4.1f} mm  part {lab[k][i]:6s} that foot point at q=0: x {near[:,0].mean()*1000:6.1f} z {near[:,2].mean()*1000:6.1f} ({(near[:,0].mean()-anc[0])*1000:+.1f} from axis)')
