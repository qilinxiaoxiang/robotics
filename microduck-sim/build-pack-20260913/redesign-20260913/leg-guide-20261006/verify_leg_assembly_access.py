#!/usr/bin/env python3
"""Regression: move the complete lower module and keep yaw output tool access open."""
from pathlib import Path
import argparse, base64, hashlib, json
import numpy as np
import trimesh
import manifold3d as mf

HERE = Path(__file__).resolve().parent

def run(data_path=HERE/'full-build-data.json', output_path=HERE/'leg-assembly-access.json', foot_output_path=HERE/'foot-approach-stop.json'):
    input_bytes=data_path.read_bytes()
    data=json.loads(input_bytes)
    rows={p['key']:p for p in data['parts']}
    solids={}
    identity={}
    def solid(key):
        if key not in solids:
            p=rows[key];vb=base64.b64decode(p['positionB64']);ib=base64.b64decode(p['indexB64'])
            mesh=trimesh.Trimesh(np.frombuffer(vb,dtype='<f4').reshape(-1,3),np.frombuffer(ib,dtype='<u4').reshape(-1,3),process=True)
            solids[key]=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
            assert solids[key].status()==mf.Error.NoError,key
            identity[key]={'verticesSha256':hashlib.sha256(vb).hexdigest(),'trianglesSha256':hashlib.sha256(ib).hexdigest(),'sourceId':p['sourceId']}
        return solids[key]
    results={}
    stops={}
    errors=[]
    def check(ok,message):
        if not ok: errors.append(message)
    for right in (False,True):
        pre='right_' if right else '';a,knee,hp,roll,yaw=([1,2,3,4,5] if right else [6,7,8,9,10]);name='right-leg' if right else 'left-leg'
        moving=[pre+'lower',pre+'ankle',pre+'smallring',f'motor{a}',f'washer{a}']
        fixed=[pre+'thigh',pre+'plate',f'motor{knee}',f'motor{hp}',f'ring{knee}']
        paths={}
        for label,sign in [('old',-1 if right else 1),('corrected',1 if right else -1)]:
            samples=[]
            for d in np.linspace(28,0,113):
                overlaps={}
                for m in moving:
                    moved=solid(m).translate([0,sign*d,0])
                    for f in fixed:
                        v=max(0.,float((moved^solid(f)).volume()))
                        if v>1e-8:overlaps[m+'--'+f]=v
                samples.append({'distanceMm':float(d),'overlapMm3':overlaps})
            paths[label]={'startTranslation':[0,sign*28,0],'movingKeys':moving,'fixedKeys':fixed,'maxOverlapMm3':max([v for s in samples for v in s['overlapMm3'].values()] or [0]),'samples':samples}
        # Shaft-only conservative access corridor (3 mm diameter, 45 mm long),
        # beginning 0.5 mm outside the screw's head seat. Handle and fingers are
        # deliberately not certified. Tool axis is the audited screw normal.
        screws=[c for c in data['screws'] if c.get('servo_ids')==[yaw] and c['category']=='horn']
        tool=[]
        old_obstacles=[pre+'yaw',f'motor{yaw}',pre+'passive',f'motor{roll}',f'ring{roll}',pre+'hip',f'ring{hp}']
        new_obstacles=[pre+'yaw',f'motor{yaw}']
        for c in screws:
            axis=np.array(c['world_axis']);center=np.array(c['world_center_mm'])
            mesh=trimesh.creation.cylinder(radius=1.5,height=45,sections=48)
            t=trimesh.geometry.align_vectors([0,0,1],axis);t[:3,3]=center+axis*23
            mesh.apply_transform(t)
            shaft=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
            overlaps={key:max(0.,float((shaft^solid(key)).volume())) for key in old_obstacles}
            tool.append({'screwId':c['id'],'oldObstaclesOverlapMm3':overlaps,'correctedMaxOverlapMm3':max(overlaps[k] for k in new_obstacles)})
        # Bind the geometric candidate to the actual displayed operation contract.
        module=next(m for m in data['modules'] if m['id']==name)
        ops=module['operations']
        knee_join=next(o for o in ops if set(o.get('moveKeys',[]))==set(moving))
        check(knee_join.get('approachVector')==paths['corrected']['startTranslation'],name+': displayed knee vector regressed')
        check(paths['old']['maxOverlapMm3']>1000,name+': original knee crossing negative control missing')
        nominal=paths['corrected']['samples'][-1]['overlapMm3']
        check(all(not sample['overlapMm3'] for sample in paths['corrected']['samples'][:-1]),name+': corrected knee approach crosses before final seat')
        if right:
            inter=solid('right_lower')^solid('ring2');box=inter.bounding_box()
            check(set(nominal)=={'right_lower--ring2'},name+': unexpected final knee contact pair')
            check(paths['corrected']['maxOverlapMm3']<=.18 and box[4]-box[1]<=.0021 and -38.5021<=box[1]<=-38.5018 and -38.5001<=box[4]<=-38.4999,name+': right source contact exceeds specifically measured registration skin')
        else: check(paths['corrected']['maxOverlapMm3']<1e-8,name+': left corrected knee intersects')
        roll_place=next(o for o in ops if f'motor{roll}' in o['add'])
        check(roll_place.get('partApproachVectors',{}).get(f'motor{roll}')==[45,0,0],name+': roll case must enter from open +X side')
        check(roll_place.get('partApproachVectors',{}).get(pre+'passive')==[45,0,0],name+': passive plate must enter from open +X side')
        roll_join=next(o for o in ops if f'motor{roll}' in o.get('moveKeys',[]))
        check(roll_join.get('approachVector')==[-45,0,0],name+': completed yaw/roll unit must enter hip from -X')
        check(set(roll_join['moveKeys'])=={pre+'yaw',pre+'passive',f'motor{yaw}',f'motor{roll}',f'washer{roll}'},name+': joined rigid module missing mounted item')
        bridge=next(o for o in ops if pre+'hip' in o['add'])
        check(bridge['add']==[f'ring{hp}',pre+'hip',f'ring{roll}'],name+': hip assembly must seat pitch support, bridge, then roll support')
        check(bridge.get('partApproachVectors',{}).get(f'ring{roll}')==[-45,0,0],name+': roll ring entry side wrong')
        yawop=next(o for o in ops if set(o['screwIds'])=={c['id'] for c in screws})
        yaw_index=ops.index(yawop)
        present={k for o in ops[:yaw_index+1] for k in o['add']}
        check(f'motor{roll}' not in present,name+': yaw output trapped behind roll motor')
        check(set(yawop.get('isolatedPartKeys',[]))==set(new_obstacles),name+': yaw bench scene differs from access test')
        check(all(t['correctedMaxOverlapMm3']<1e-8 for t in tool),name+': new yaw shaft obstruction')
        check(all(max(t['oldObstaclesOverlapMm3'].values())>200 for t in tool),name+': original yaw obstruction negative control missing')
        # A measured stopped foot preview retains the failed full route; it is
        # not reclassified as a successfully seated rigid insertion.
        foot=pre+'foot';foot_fixed=[pre+'ankle',pre+'lower',f'motor{a}']
        def foot_overlap(distance):
            moved=solid(foot).translate([0,0,-distance])
            return {q:max(0.,float((moved^solid(q)).volume())) for q in foot_fixed}
        previous=32.
        first=None
        foot_full=[]
        for distance in np.linspace(32,0,129):
            vals=foot_overlap(distance);foot_full.append({'distanceMm':float(distance),'overlapMm3':vals})
            if max(vals.values())>.02 and first is None:first=(previous,float(distance))
            previous=float(distance)
        check(first is not None,name+': original foot obstruction negative control missing')
        if first is None: raise AssertionError(name+': expected foot obstruction disappeared; re-evaluate stop contract')
        safe,contact=first
        for _ in range(12):
            mid=(safe+contact)/2
            if max(foot_overlap(mid).values())>.02:contact=mid
            else:safe=mid
        stop=safe+.5
        foot_samples=[{'distanceMm':float(v),'overlapMm3':foot_overlap(v)} for v in np.linspace(32,stop,int(np.ceil((32-stop)/.25))+1)]
        check(max(v for r in foot_samples for v in r['overlapMm3'].values())<1e-9,name+': foot stop must have zero intersection')
        pair=max(foot_overlap(contact),key=foot_overlap(contact).get)
        gap=min(float(solid(foot).translate([0,0,-stop]).min_gap(solid(q),5)) for q in foot_fixed)
        check(gap>.05,name+': foot stopped endpoint gap is insufficient')
        stops[name]={'start':[0,0,-32],'stop':[0,0,-float(stop)],'movingKeys':[foot],
          'reason':'The printed foot retaining features obstruct straight vertical insertion. The preview stops clear; full physical fitting or a rotation path remains unverified. Do not pull it into place with the retaining screw.',
          'contactPair':foot+'--'+pair,'contactTranslation':[0,0,-contact],'stopGapMm':gap,
          'fixedKeys':foot_fixed,'samples':foot_samples,'rejectedFullRoute':foot_full}
        footop=next(o for o in ops if foot in o['add'])
        shown=footop.get('motionStop',{})
        check(shown.get('movingKeys')==[foot] and np.allclose(shown.get('stop',[999,999,999]),[0,0,-stop]),name+': displayed foot stop differs from checked path')
        installed=set()
        operation_tools=[]
        for op in ops:
            installed.update(op['add'])
            visible=installed & set(op.get('isolatedPartKeys',installed))
            for cid in op['screwIds']:
                c=next(c for c in data['screws'] if c['id']==cid)
                axis=np.array(c['world_axis']);center=np.array(c['world_center_mm'])
                mesh=trimesh.creation.cylinder(radius=1.5,height=45,sections=48)
                transform=trimesh.geometry.align_vectors([0,0,1],axis);transform[:3,3]=center+axis*23
                mesh.apply_transform(transform)
                shaft=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
                # Explicit washer/nut meshes are included: their clear holes
                # must also admit the checked shaft envelope.
                overlaps={key:max(0.,float((shaft^solid(key)).volume())) for key in sorted(visible)}
                worst=max(overlaps.values(),default=0)
                check(worst<=.02,name+': blocked driver at '+cid+' '+str({k:v for k,v in overlaps.items() if v>.02}))
                operation_tools.append({'operationId':op['id'],'screwId':cid,'obstacleKeys':sorted(visible),'maxOverlapMm3':worst})
        check(len(operation_tools)==35,name+': not all 35 scheduled screws received a tool corridor check')
        results[name]={'kneeApproach':paths,'yawToolAccess':tool,'allScheduledToolAccess':operation_tools,'operationContractSha256':hashlib.sha256(json.dumps(ops,sort_keys=True).encode()).hexdigest(),'shaftRadiusMm':1.5,'shaftLengthMm':45,'shaftHeadSeatOffsetMm':.5}
        print(name,{label:p['maxOverlapMm3'] for label,p in paths.items()},'tool',[(t['screwId'],t['correctedMaxOverlapMm3'],max(t['oldObstaclesOverlapMm3'].values())) for t in tool],flush=True)
    foot_output_path.write_text(json.dumps(stops,indent=2)+'\n')
    report={'passed':not errors,'errors':errors,'dataPath':str(data_path),'dataSha256':hashlib.sha256(input_bytes).hexdigest(),'problemIds':['P5','P6'],'checked':'2026-10-08','meshIdentity':identity,'legs':results,'scope':'Actual solid sampled translations at 0.25 mm; driver shaft envelope only. Does not certify continuous motion, printed tolerances, fingers, handle access or force. Internal contacts within rigid moving module are not re-tested here; existing ankle-fit checkpoint applies. Driver envelope excludes handle, fingers and previously installed screw heads; it is a shaft-access screen, not a complete tool/hardware clearance certificate.'}
    output_path.write_text(json.dumps(report,indent=2)+'\n')
    if errors: raise AssertionError('\n'.join(errors))
    print('LEG_ASSEMBLY_ACCESS_PASS')
    return report
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--data',type=Path,default=HERE/'full-build-data.json')
    parser.add_argument('--output',type=Path,default=HERE/'leg-assembly-access.json')
    parser.add_argument('--foot-output',type=Path,default=HERE/'foot-approach-stop.json')
    args=parser.parse_args()
    run(args.data,args.output,args.foot_output)
