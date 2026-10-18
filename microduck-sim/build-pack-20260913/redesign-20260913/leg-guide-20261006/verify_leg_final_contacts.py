#!/usr/bin/env python3
"""Bound the six specific source contacts; never waive arbitrary endpoint overlap."""
from pathlib import Path
import base64,hashlib,json
import numpy as np
import trimesh
import manifold3d as mf
D=Path(__file__).resolve().parent
# Limits reviewed from the unmodified source mesh registration on 2026-10-08.
# They are world-space interface slabs, not a global collision-volume tolerance.
CONTRACTS=[
 dict(module='left-leg',operation='left-leg-15',moving='motor9',fixed='yaw',vector=[45,0,0],axis=2,slab=[-8.00101,-7.99999],depthCap=.00102,volumeCap=.341,stage='parallel slide beneath nominal top mating face',negativeVector=[-45,0,0]),
 dict(module='left-leg',operation='left-leg-15',moving='passive',fixed='motor9',vector=[45,0,0],axis=0,slab=[17.49899,17.50001],depthCap=.00102,volumeCap=.254,terminalDistanceCap=.00102,stage='last 0.00102 mm of passive-plate seating',negativeVector=[-45,0,0]),
 dict(module='right-leg',operation='right-leg-05',moving='motor1',fixed='right_ankle',vector=[0,0,30],axis=1,slab=[-64.50001,-64.49906],depthCap=.00095,volumeCap=.139,stage='vertical motor slide beside nominal rear mating face',negativeVector=[0,30,0]),
 dict(module='right-leg',operation='right-leg-09',moving='right_lower',fixed='ring2',vector=[0,28,0],axis=1,slab=[-38.50201,-38.49999],depthCap=.00202,volumeCap=.173,terminalDistanceCap=.00202,stage='last 0.00202 mm of registered ring seating',negativeVector=[0,-28,0]),
 dict(module='right-leg',operation='right-leg-15',moving='motor4',fixed='right_yaw',vector=[45,0,0],axis=2,slab=[-8.00101,-7.99999],depthCap=.00102,volumeCap=.341,stage='parallel slide beneath nominal top mating face',negativeVector=[-45,0,0]),
 dict(module='right-leg',operation='right-leg-15',moving='right_passive',fixed='motor4',vector=[45,0,0],axis=0,slab=[17.49899,17.50001],depthCap=.00102,volumeCap=.254,terminalDistanceCap=.00102,stage='last 0.00102 mm of passive-plate seating',negativeVector=[-45,0,0]),
]

def verify():
    source=D/'full-build-data.json';input_bytes=source.read_bytes();data=json.loads(input_bytes);parts={p['key']:p for p in data['parts']};mods={m['id']:m for m in data['modules']}
    solids={};identities={};results=[];errors=[]
    def solid(key):
        if key not in solids:
            p=parts[key];vb=base64.b64decode(p['positionB64']);ib=base64.b64decode(p['indexB64'])
            mesh=trimesh.Trimesh(np.frombuffer(vb,'<f4').reshape(-1,3),np.frombuffer(ib,'<u4').reshape(-1,3),process=True)
            solids[key]=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,np.float32),np.asarray(mesh.faces,np.uint32)))
            assert solids[key].status()==mf.Error.NoError,key
            identities[key]={'positionPayloadSha256':hashlib.sha256(vb).hexdigest(),'indexPayloadSha256':hashlib.sha256(ib).hexdigest(),'sourceTransformWorld':p['sourceTransformWorld'],'sourceId':p['sourceId']}
        return solids[key]
    def measure(c,translation):
        intersection=solid(c['moving']).translate(translation)^solid(c['fixed']);volume=max(0.,float(intersection.volume()))
        box=list(intersection.bounding_box()) if volume>1e-9 else None
        return {'translation':np.asarray(translation).tolist(),'volumeMm3':volume,'intersectionBoundsMm':box,'depthMm':box[c['axis']+3]-box[c['axis']] if box else 0.}
    def accepted(c,r):
        if r['volumeMm3']<1e-9:return True
        b=r['intersectionBoundsMm'];a=c['axis']
        return (r['volumeMm3']<=c['volumeCap'] and r['depthMm']<=c['depthCap'] and b[a]>=c['slab'][0] and b[a+3]<=c['slab'][1] and ('terminalDistanceCap' not in c or np.linalg.norm(r['translation'])<=c['terminalDistanceCap']))
    for c in CONTRACTS:
        op=next(o for o in mods[c['module']]['operations'] if o['id']==c['operation'])
        v=np.array(op.get('approachVector') if c['moving'] in op.get('moveKeys',[]) else op.get('partApproachVectors',{}).get(c['moving']),float)
        if not np.array_equal(v,c['vector']):errors.append(c['moving']+': operation vector differs from scoped source-contact contract')
        # 0.25mm across the whole path, plus 0.0001mm at the source contact
        # thickness for parts whose exception is confined to final seating.
        distances=list(np.linspace(float(np.linalg.norm(v)),0,int(np.ceil(np.linalg.norm(v)/.25))+1))
        if 'terminalDistanceCap' in c:distances=sorted(set(distances+list(np.linspace(.003,0,31))),reverse=True)
        direction=v/np.linalg.norm(v)
        samples=[measure(c,direction*d) for d in distances]
        failed=[r for r in samples if not accepted(c,r)]
        if failed:errors.append(c['moving']+'--'+c['fixed']+': contact exceeds its fixed slab, depth, stage or volume limit')
        negative=[measure(c,np.array(c['negativeVector'])*f) for f in np.linspace(1,0,46)]
        bad=next((r for r in negative if not accepted(c,r)),None)
        if bad is None:errors.append(c['moving']+': wrong-direction negative control did not fail')
        positive=[r for r in samples if r['volumeMm3']>1e-9]
        results.append(dict(module=c['module'],operation=c['operation'],moving=c['moving'],fixed=c['fixed'],pathVector=c['vector'],
            operationContractSha256=hashlib.sha256(json.dumps(op,sort_keys=True).encode()).hexdigest(),
            decision='bounded-source-registration-contact; NOT zero-overlap insertion or physical fit',
            allowedContact={'axis':'XYZ'[c['axis']],'worldSlabMm':c['slab'],'depthCapMm':c['depthCap'],'volumeCapMm3':c['volumeCap'],'terminalDistanceCapMm':c.get('terminalDistanceCap'),'stage':c['stage']},
            samples=samples,sampleStepMmMaximum=.25,terminalRefinementStepMm=.0001 if 'terminalDistanceCap' in c else None,
            measuredMaximumVolumeMm3=max(r['volumeMm3'] for r in samples),measuredMaximumDepthMm=max(r['depthMm'] for r in samples),
            firstPositiveOffsetMm=float(np.linalg.norm(positive[0]['translation'])) if positive else None,finalContact=samples[-1],
            negativeControl={'vector':c['negativeVector'],'rejected':bad is not None,'firstRejectedSample':bad},passedScopedContactCheck=not failed and bad is not None,
            physicalFitVerified=False))
        print(c['moving'],c['fixed'],'depth',max(r['depthMm'] for r in samples),'volume',max(r['volumeMm3'] for r in samples),'negative_rejected',bad is not None,flush=True)
    report={'problemIds':['P5','P6'],'checked':'2026-10-08','passedScopedContactReview':not errors,'errors':errors,'sourceDataSha256':hashlib.sha256(input_bytes).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'meshIdentities':identities,'contacts':results,
      'integrationRule':'Match exact module/operation/moving/fixed/vector, source mesh identities and operation hash. Every positive sample must stay in its fixed world slab, depth, volume and terminal-distance limit. Reject unknown pairs or any change beyond these explicit limits. Do not use max<=final as acceptance.',
      'evidenceBoundary':'These six deviations already occur in untouched nominal mating surfaces and are 0.00093–0.00200mm thick. Reporting them as bounded source-registration contact separates them from the millimetre-scale wrong-side traversal. This is not zero intersection, a print tolerance measurement, proof of flexible seating, continuous collision freedom, or physical assembly acceptance.'}
    out=D/'audit-20261008/leg-final-contacts.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    if errors:raise AssertionError('\n'.join(errors))
    print('LEG_FINAL_CONTACTS_SCOPED_PASS')
    return report
if __name__=='__main__':verify()
