"""P5/P6: source-solid screwdriver access and closure-order regression.

Runs on current guide geometry; distinct bench stations are explicitly declared
by operation.isolatedPartKeys. Other operations include ALL earlier introduced
physical parts, not merely the viewer's selected context. A shaft envelope is
not proof of a particular real tool's tip shape, grip, torque or availability.
"""
from pathlib import Path
import argparse, base64, hashlib, json
import numpy as np
import trimesh
import manifold3d as mf
D=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,default=D/'full-build-data.json');ap.add_argument('--output',type=Path,default=D/'nonleg-access-audit.json');args=ap.parse_args()
    data=json.loads(args.data.read_text());parts={p['key']:p for p in data['parts']};screws={s['id']:s for s in data['screws']};solids={};bounds={}
    def solid(k):
        if k not in solids:
            p=parts[k];m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
            so=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
            assert so.status()==mf.Error.NoError,(k,str(so.status()));solids[k]=so;bounds[k]=m.bounds
        return solids[k]
    def cylinder(start,end,r):
        delta=np.array(end)-start;t=trimesh.geometry.align_vectors([0,0,1],delta);t[:3,3]=(np.array(start)+end)/2
        m=trimesh.creation.cylinder(radius=r,height=np.linalg.norm(delta),sections=48).apply_transform(t)
        return mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
    def tool(s,bent=False):
        a=np.array(s['world_axis']);o=np.array(s['world_center_mm'])
        if not bent:return cylinder(o+a*2,o+a*40,1.5)
        # 3 mm bit, 6 mm perpendicular handle; exits -Y through the open cavity.
        return cylinder(o+a*2,o+a*18,1.5)+cylinder(o+a*17,o+a*17+np.array([0,-50,0]),3)
    def posed_solid(k,poses):
        body=solid(k)
        for pose in poses:
            if k in pose['keys']:
                transform=trimesh.transformations.rotation_matrix(np.deg2rad(pose['degrees']),pose['axis'],point=pose['pivot'])
                body=body.transform(transform[:3,:])
        return body
    def hits(t,keys,poses=()):
        rows=[]
        for k in sorted(keys):
            if k not in parts or parts[k].get('partKind')=='fastener':continue
            v=max(0.,float((t^posed_solid(k,poses)).volume()))
            if v>.02:rows.append(dict(part=k,volumeMm3=v))
        return rows
    prior=set();rows=[];bad=[];order={};seq=0;closure_ops=[]
    for mod in data['modules']:
        for op in mod['operations']:
            seq+=1
            for k in op['add']:order[k]=seq
            prior.update(op['add'])
            if 'leg' in mod['id']:continue
            scene=set(op.get('isolatedPartKeys',prior))&prior
            poses=op.get('fixedPoses',[])
            if any(s.startswith('E-head_cap_closure-') for s in op['screwIds']):closure_ops.append((op,scene))
            for sid in op['screwIds']:
                order[sid]=seq
                s=screws[sid];bent=sid.startswith('S14-horn-');blocks=hits(tool(s,bent),scene,poses)
                row=dict(operation=op['id'],screw=sid,tool='right-angle-side-exit' if bent else '3mm-diameter-straight-2to40mm',scene=sorted(scene),fixedPoses=poses,intersections=blocks,conditionalOnPhysicalFit=op.get('conditionalOnPreviousPhysicalFit',False))
                rows.append(row)
                if blocks:bad.append(row)
    # Reproduce known failures directly from immutable source keys, independent
    # of the new step numbering. These blockers must be absent at fasten time.
    cases=[('S12-rear_center-117',['shell_right']),('S13-horn-041',['motor11']),('S13-horn-042',['motor11']),('S13-horn-043',['motor11']),('S13-horn-044',['motor11']),('S14-horn-049',['motor13']),('E-pi-01',['jaw_support']),('E-pi-02',['motor15']),('E-openrb-02',['motor14']),('E-head_cap_closure-01',['upper_pad','lower_pad','jaw_frame']),('E-head_cap_closure-02',['upper_pad','lower_pad','jaw_frame'])]
    regressions=[dict(screw=sid,oldBlockers=hits(tool(screws[sid]),keys)) for sid,keys in cases]
    assert all(r['oldBlockers'] for r in regressions),'An original blocked-access regression no longer reproduces; review source changes.'
    def open_jaw_pose(op):
        return any(set(['jaw_frame','lower_pad'])<=set(pose['keys']) and np.allclose(pose['axis'],[0,1,0]) and np.allclose(pose['pivot'],[26.1,0,118.6146],atol=1e-5) and np.isclose(pose['degrees'],30) for pose in op.get('fixedPoses',[]))
    expected_screws={s['id'] for s in data['screws'] if 'leg' not in s['moduleId']}
    invariants={
      'neck_rear_before_shells': order['S12-rear_center-117']<order['shell_right'],
      'head_yaw_before_pitch_join':order['S13-horn-041']<order['S11-horn-033'],
      'roll_before_yaw_case':order['S14-horn-049']<order['S13-case-095'],
      'cap_with_jaw_open_30_degrees':bool(closure_ops) and all(open_jaw_pose(op) and {'jaw_frame','lower_pad'}<=scene for op,scene in closure_ops),
      'cap_before_fixed_upper_pad':max(order[s] for s in order if s.startswith('E-head_cap_closure-'))<order['upper_pad'] and all('upper_pad' not in scene for _,scene in closure_ops),
      'camera_mount_before_controller':max(order[s] for s in order if s.startswith('E-camera_foot-'))<order['openrb'],
      'all_nonleg_screws_checked_once':len(rows)==len(expected_screws) and {r['screw'] for r in rows}==expected_screws}
    jaw_access=[]
    for op,scene in closure_ops:
        for sid in [s for s in op['screwIds'] if s.startswith('E-head_cap_closure-')]:
            closed=hits(tool(screws[sid]),['jaw_frame','lower_pad'])
            opened=hits(tool(screws[sid]),['jaw_frame','lower_pad'],op.get('fixedPoses',[]))
            jaw_access.append(dict(screw=sid,closedJawBlockers=closed,openJawIntersections=opened))
    invariants['closed_jaw_front_access_failure_reproduced']=all(row['closedJawBlockers'] and not row['openJawIntersections'] for row in jaw_access if row['screw'] in ['E-head_cap_closure-01','E-head_cap_closure-02']) and len(jaw_access)==3
    # Explicitly retain the same-fork long-driver failure: changing the sequence
    # does not make a 40 mm straight screwdriver fit a 24.5 mm cavity.
    fork_check=[]
    for sid in [s for s in screws if s.startswith('S14-horn-')]:
        scene=['head_yaw_link','motor14','head_roll_ring_a','head_roll_ring_b']
        straight=hits(tool(screws[sid]),scene);bent=hits(tool(screws[sid],True),scene)
        fork_check.append(dict(screw=sid,longStraightBlocked=straight,rightAngleIntersections=bent))
        assert straight and not bent,(sid,straight,bent)
    result=dict(problemIds=['P5','P6'],checked='2026-10-08',dataSha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),passed=not bad and all(invariants.values()),toolPaths=rows,failures=bad,sourceFailureRegressions=regressions,dependencyChecks=invariants,headRollToolRequirement=fork_check,headClosureJawAccess=jaw_access,physicalToolFitVerified=False,physicalAssemblyVerified=False,scope='Solid intersection of specified tool working envelopes at each actual assembly station; all previous physical parts retained except explicitly detached bench subassemblies. Explicit fixedPoses are applied to actual obstacle solids. Excludes hand/grip, screw-head drive shape and wrench/nut-side access, which require separate validation.')
    args.output.write_text(json.dumps(result,indent=2)+'\n');print('NONLEG_ACCESS_PASS' if result['passed'] else 'NONLEG_ACCESS_FAIL',json.dumps({'paths':len(rows),'failedPaths':len(bad),'dependencyChecks':invariants}));
    for r in bad:print(r['operation'],r['screw'],r['intersections'])
    if not result['passed']:raise SystemExit(1)
if __name__=='__main__':main()
