import json,sys,os,numpy as np
D='/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/motor-wires/active-topology.json'
A=json.load(open(D));T=A['ports']
print('top keys',list(A.keys()))
print('port keys',list(T['motor-6-socket-14'].keys()))
print('outward',T['motor-6-socket-14'].get('outward'),T['motor-1-socket-13'].get('outward'))
R=A.get('routes');rs=R if isinstance(R,list) else list(R.values())
for r in rs:
    s=json.dumps(r)
    if 'motor-6-socket' in s or 'motor-1-socket' in s:
        print({k:(v if not isinstance(v,(list,dict)) else f'<{type(v).__name__} {len(v)}>') for k,v in r.items()})
        for k in ('points','waypoints','path','polyline','centerline'):
            if k in r: print(k,np.round(np.array(r[k]),1).tolist()[-8:])
MAC=os.path.expanduser('~/code/robotics/microduck-sim/guide/firmware/mac');sys.path.insert(0,MAC);os.chdir(MAC)
import mujoco,trimesh,target_ground as tg
from scipy.spatial import cKDTree
G=tg.DuckGeometry();m,d=G.m,G.d
def surf(body):
    out=[]
    for g in range(m.ngeom):
        if m.body(m.geom_bodyid[g]).name==body and m.geom_type[g]==mujoco.mjtGeom.mjGEOM_MESH and m.geom_group[g]<=2:
            mid=m.geom_dataid[g];va,na=m.mesh_vertadr[mid],m.mesh_vertnum[mid];fa,nf=m.mesh_faceadr[mid],m.mesh_facenum[mid]
            pts=trimesh.sample.sample_surface(trimesh.Trimesh(m.mesh_vert[va:va+na],m.mesh_face[fa:fa+nf],process=False),15000,seed=3)[0]
            out.append((g,pts,m.geom(g).name))
    return out
for side,body,shin,jn,sg,used,free,off in (('left','ankle_left','leg','left_ankle',1,'motor-6-socket-14','motor-6-socket-13',[0,14.5,120]),('right','ankle_right','leg_2','right_ankle',-1,'motor-1-socket-13','motor-1-socket-14',[0,-14.5,120])):
    off=np.array(off);d.qpos[:]=m.qpos0;mujoco.mj_kinematics(m,d)
    j=m.joint(jn).id;sb=m.body(shin).id;anc=d.xanchor[j].copy()
    Rs0,ps0=d.xmat[sb].reshape(3,3).copy(),d.xpos[sb].copy()
    Fg=surf(body);Sv=[x for x in surf(shin) if 'servo' in x[2]]
    print(side,'shin geoms',[x[2] for x in surf(shin)])
    SvL=np.vstack([p@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g] for g,p,_ in Sv]);SvL=(SvL-ps0)@Rs0
    stubs={}
    for name in (used,free):
        P=T[name];Tm=np.array(P['transform']);lo,hi=np.array(P['housingLocalBounds'])
        g=np.stack(np.meshgrid(*[np.linspace(lo[i],hi[i],9) for i in range(3)],indexing='ij'),-1).reshape(-1,3)
        B=(g@Tm[:3,:3].T+Tm[:3,3]+off)
        # wire: 3 mm bundle leaving the plug's far end toward the robot centre, 20 mm straight
        M=np.array(P['mouth'])+off;yout=-np.sign(M[1])
        y0=B[:,1].min() if yout<0 else B[:,1].max()
        W=[]
        for s in np.linspace(0,20,41):
            for a in np.linspace(0,2*np.pi,12,endpoint=False):
                W.append([M[0]+1.5*np.cos(a),y0+yout*s,M[2]+1.5*np.sin(a)])
        stubs[name]=((B/1000-ps0)@Rs0,(np.array(W)/1000-ps0)@Rs0)
    for q in (1.0,1.2,1.25,1.3,1.35,1.4,1.45,1.5,1.571):
        d.qpos[:]=m.qpos0;d.qpos[m.jnt_qposadr[j]]=q*sg;mujoco.mj_kinematics(m,d)
        Pf=np.vstack([p@d.geom_xmat[g].reshape(3,3).T+d.geom_xpos[g] for g,p,_ in Fg]);Nm=np.concatenate([[n]*len(p) for g,p,n in Fg])
        tree=cKDTree(Pf);Rs,ps=d.xmat[sb].reshape(3,3),d.xpos[sb]
        ax=np.array([0,1,0.]);anc_w=d.xanchor[j]
        rel=Pf-anc_w;rad=np.linalg.norm(rel-np.outer(rel@ax,ax),axis=1)
        far=Pf[rad>0.016];tf=cKDTree(far)
        sv=SvL@Rs.T+ps;ds,_=tf.query(sv)
        msg=[f'body {ds.min()*1000:4.1f}']
        for name in (used,free):
            Bb,Wb=stubs[name]
            db,_=tree.query(Bb@Rs.T+ps);dw,iw=tree.query(Wb@Rs.T+ps)
            msg.append(f"{name[-2:]}{'*' if name==used else ' '} plug {db.min()*1000:4.1f} wire {dw.min()*1000:4.1f} ({Nm[iw[dw.argmin()]].split('__')[-1]})")
        print(f'  q {q*sg:+.3f}',' | '.join(msg))
