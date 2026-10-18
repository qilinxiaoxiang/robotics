"""Apply reviewed operation changes after selecting the current stock geometry."""
from pathlib import Path
import copy, hashlib, json

def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def apply_motion_overlay(data, service, path):
    path=Path(path)
    overlay=json.loads(path.read_text())
    verification=json.loads(path.with_name('overlay-verification.json').read_text())
    if verification.get('passed') is not True or verification.get('overlaySha256')!=hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError('Assembly motion overlay differs from its accepted content')
    if overlay.get('integrationReady') is not True:
        raise ValueError('Assembly motion overlay is not ready')
    if not overlay.get('sourceHashes'): raise ValueError('Assembly motion source bindings are missing')
    for source, expected in overlay['sourceHashes'].items():
        target=Path(source)
        if not target.is_absolute(): target=path.parent/target
        if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
            raise ValueError('Assembly motion source changed: '+source)
    result=copy.deepcopy(data); current_service=copy.deepcopy(service)
    modules={m['id']:m for m in result['modules']}
    if current_service is not None: modules['torso']=current_service['module']
    touched=set()
    for patch in overlay['operationPatches']:
        key=(patch['moduleId'], patch['operationId'])
        if key in touched: raise ValueError('Duplicate operation patch: '+str(key))
        touched.add(key)
        module=modules[key[0]]
        op=next(o for o in module['operations'] if o['id']==key[1])
        if canonical_sha(op)!=patch['expectedOperationSha256']:
            raise ValueError('Assembly operation changed: '+str(key))
        op.update(copy.deepcopy(patch['set']))
    for module_id, ordered_ids in overlay.get('moduleOrders', {}).items():
        module=modules[module_id]; ops={o['id']:o for o in module['operations']}
        if len(ordered_ids)!=len(ops) or set(ordered_ids)!=set(ops):
            raise ValueError('Assembly reordering must preserve every operation: '+module_id)
        module['operations']=[ops[op_id] for op_id in ordered_ids]
    result['assemblyMotionRevision']={
        'id':overlay.get('id',path.stem),
        'overlaySha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'operationCount':len(touched),
        'physicalFitVerified':False,
    }
    return result,current_service
