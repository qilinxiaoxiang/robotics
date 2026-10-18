#!/usr/bin/env python3
"""Retain cap nut straight-entry failures and check displayed stopped approaches.

A stopped preview is not a validated nut fitting sequence. It leaves manual
hand-tilting/captive-nut fit and physical driver holding access unverified.
"""
from pathlib import Path
import argparse,base64,hashlib,json
import numpy as np
import trimesh
import manifold3d as mf
HERE=Path(__file__).resolve().parent
GROUPS={
 'openrb': {'keys':[f'nut_E-openrb-0{i}' for i in range(1,5)],'start':[0,0,12],'stop':[0,0,2.7]},
 'camera_foot': {'keys':[f'nut_E-camera_foot-0{i}' for i in range(1,3)],'start':[0,0,-12],'stop':[0,0,-2.8]},
}

def verify(data_path,output,geometry_only=False):
    input_bytes=data_path.read_bytes()
    data=json.loads(input_bytes);parts={p['key']:p for p in data['parts']}
    solids={};bounds={};identity={};errors=[];result={}
    def check(ok,why):
        if not ok:errors.append(why)
    def solid(key):
        if key not in solids:
            p=parts[key];vb=base64.b64decode(p['positionB64']);ib=base64.b64decode(p['indexB64'])
            mesh=trimesh.Trimesh(np.frombuffer(vb,dtype='<f4').reshape(-1,3),np.frombuffer(ib,dtype='<u4').reshape(-1,3),process=True)
            solids[key]=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
            assert solids[key].status()==mf.Error.NoError,key
            bounds[key]=mesh.bounds
            identity[key]={'sourceId':p['sourceId'],'verticesSha256':hashlib.sha256(vb).hexdigest(),'trianglesSha256':hashlib.sha256(ib).hexdigest(),'sourceTransformWorld':p.get('sourceTransformWorld')}
        return solids[key]
    def overlap(moving,fixed,offset):
        a=solid(moving);b=solid(fixed);box=bounds[moving]+offset
        if np.any(box[1]<bounds[fixed][0]) or np.any(bounds[fixed][1]<box[0]):return 0.
        return max(0.,float((a.translate(offset)^b).volume()))
    for group,contract in GROUPS.items():
        keys=contract['keys'];start=np.array(contract['start'],float);stop=np.array(contract['stop'],float)
        operation=None;obstacles={'head_cap'};module_id=None
        if not geometry_only:
            found=[]
            for mod in data['modules']:
                installed=set(mod['partKeys'])-set(mod.get('ownedPartKeys',[]))
                for op in mod['operations']:
                    installed.update(op['add'])
                    if set(op.get('motionStop',{}).get('movingKeys',[]))==set(keys):
                        found.append((mod['id'],op,installed & set(op.get('isolatedPartKeys',installed))))
            check(len(found)==1,group+': expected exactly one displayed measured-stop operation')
            if len(found)==1:
                module_id,operation,visible=found[0];shown=operation['motionStop']
                check(np.allclose(shown.get('start',[999]*3),start) and np.allclose(shown.get('stop',[999]*3),stop),group+': displayed stop differs from measured contract')
                check(set(keys)<=visible,group+': stopped nuts are not introduced in the visible operation')
                check('head_cap' in visible,group+': cap obstruction is hidden from stopped preview')
                check(bool(shown.get('reason')),group+': missing physical fitting limitation')
                obstacles=visible-set(keys)
                if group=='camera_foot':check('openrb' not in visible,group+': board blocks underside nut fitting; camera foot must precede OpenRB')
        rows=[]
        for key in keys:
            full=[]
            for f in np.linspace(1,0,121):
                full.append({'offset':(start*f).tolist(),'capOverlapMm3':overlap(key,'head_cap',start*f)})
            blocked_control=group=='camera_foot' or key.endswith(('01','03'))
            full_peak=max(r['capOverlapMm3'] for r in full)
            check(full_peak>.5 if blocked_control else full_peak<1e-8,key+': original straight-entry negative/control classification changed')
            check(full[-1]['capOverlapMm3']<1e-8,key+': final nut pose itself overlaps the cap')
            # Every translation interval is at most0.1mm; endpoint has an
            # independently measured positive gap against all visible solids.
            n=int(np.ceil(np.linalg.norm(start-stop)/.1))+1
            partial=[]
            for f in np.linspace(0,1,n):
                offset=start+(stop-start)*f
                values={q:overlap(key,q,offset) for q in sorted(obstacles)}
                partial.append({'offset':offset.tolist(),'maxOverlapMm3':max(values.values(),default=0.)})
                check(max(values.values(),default=0.)<1e-8,key+': stopped route intersects '+str({q:v for q,v in values.items() if v>=1e-8}))
            gap=min(float(solid(key).translate(stop).min_gap(solid(q),1.)) for q in obstacles)
            check(gap>0,key+': stopped endpoint needs a positive gap')
            rows.append({'key':key,'fullStraightRouteMaxOverlapMm3':max(r['capOverlapMm3'] for r in full),'finalCapOverlapMm3':full[-1]['capOverlapMm3'],'stopGapMm':gap,'stoppedSamples':partial,'rejectedFullRoute':full})
        result[group]={'moduleId':module_id,'operationId':operation['id'] if operation else None,'operationContractSha256':hashlib.sha256(json.dumps(operation,sort_keys=True).encode()).hexdigest() if operation else None,'movingKeys':keys,'fixedKeys':sorted(obstacles),'start':start.tolist(),'stop':stop.tolist(),'nuts':rows}
        print(group,'full route max',max(r['fullStraightRouteMaxOverlapMm3'] for r in rows),'stopped gap min',min(r['stopGapMm'] for r in rows),flush=True)
    report={'problemIds':['P5','P6'],'checked':'2026-10-08','passed':not errors and not geometry_only,'passedGeometry':not errors,'integrationChecked':not geometry_only,'errors':errors,'dataPath':str(data_path),'dataSha256':hashlib.sha256(input_bytes).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'meshIdentity':identity,'groups':result,'scope':'Six specified nut envelopes against native cap and, in integrated mode, every visible installed part. 0.1 mm samples and positive stopped-endpoint gap. The rejected straight route is retained; these stopped previews do not validate hand-tilting, a continuous/rotating route, print compliance, captive retention, tool/finger access or physical fit. No universal impossibility claim is made.'}
    output.write_text(json.dumps(report,indent=2)+'\n')
    if errors:raise AssertionError('\n'.join(errors))
    print('NUT_APPROACH_GEOMETRY_ONLY_INTEGRATION_PENDING' if geometry_only else 'NUT_APPROACHES_PASS')
    return report
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=HERE/'full-build-data.json');parser.add_argument('--output',type=Path,default=HERE/'nut-approach-verification.json');parser.add_argument('--geometry-only',action='store_true',help='Investigation only: output passed=false until actual viewer metadata and installed obstacles are checked.')
    args=parser.parse_args();verify(args.data,args.output,args.geometry_only)
