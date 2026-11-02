import json,sys,os,glob,numpy as np
T=json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires/active-topology.json'))['ports']
MAC=os.path.expanduser('~/code/robotics/microduck-sim/guide/firmware/mac');sys.path.insert(0,MAC);os.chdir(MAC)
import mujoco,trimesh,target_ground as tg
from scipy.spatial import cKDTree
# logged ankle range, folded so + is the bend direction
lo,hi=9,-9;n=0
for f in glob.glob(MAC+'/robot-runs-20261030-t1/*.jsonl')+glob.glob(MAC+'/**/robot-runs*/*.jsonl',recursive=True):
    for i,l in enumerate(open(f,errors='ignore')):
        if i%5: continue
        try: q=json.loads(l).get('q')
        except ValueError: continue
        if q and len(q)>=6:
            a,b=-q[0],q[5];lo=min(lo,a,b);hi=max(hi,a,b);n+=1
print('logged folded ankle range',round(lo,3),round(hi,3),'rows',n)
G=tg.DuckGeometry();m,d=G.m,G.d
j=m.joint('left_ankle').id;sb=m.body('leg').id
print('model joint range',m.jnt_range[j])
Fg=[]
for g in range(m.ngeom):
    if m.body(m.geom_bodyid[g]).name=='ankle_left' and m.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH and m.geom_group[g]<=2:
        mid=m.geom_dataid[g];va,na=m.mesh_vertadr[mid],m.mesh_vertnum[mid];fa,nf=m.mesh_faceadr[mid],m.mesh_facenum[mid]
        Fg.append((g,trimesh.sample.sample_surface(trimesh.Trimesh(m.mesh_vert[va:va+na],m.mesh_face[fa:fa+nf],process=False),15000,seed=3)[0]))
d.qpos[:]=m.qpos0;mujoco.mj_kinematics(m,d);R0,p0=d.xmat[sb].reshape(3,3).copy(),d.xpos[sb].copy();off=np.array([0,14.5,120])
B={}
for name in ('motor-6-socket-14','motor-6-socket-13'):
    P=T[name];Tm=np.array(P['transform']);l,h=np.array(P['housingLocalBounds'])
    g=np.stack(np.meshgrid(*[np.linspace(l[i],h[i],9) for i in range(3)],indexing='ij'),-1).reshape(-1,3)
    B[name]=((g@Tm[:3,:3].T+Tm[:3,3]+off)/1000-p0)@R0
for q in (-1.2,-1.0,-0.8,-0.6,-0.4,-0.2,0,0.2,0.44,0.8):
    d.qpos[:]=m.qpos0;d.qpos[m.jnt_qposadr[j]]=q;mujoco.mj_kinematics(m,d)
    Pf=np.vstack([p@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g] for g,p in Fg]);t=cKDTree(Pf);Rs,ps=d.xmat[sb].reshape(3,3),d.xpos[sb]
    print(f'q {q:+.2f} rear plug {t.query(B["motor-6-socket-14"]@Rs.T+ps)[0].min()*1000:4.1f}  front plug {t.query(B["motor-6-socket-13"]@Rs.T+ps)[0].min()*1000:4.1f}')
