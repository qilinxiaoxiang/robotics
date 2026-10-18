#!/usr/bin/env python3
"""Check actual derived viewer geometry, specs, invariants and stale-input gates."""
from pathlib import Path
import base64,copy,hashlib,json,re,struct,sys
D=Path(__file__).resolve().parent;G=D.parent/'leg-guide-20261006';sys.path.insert(0,str(G))
from bundle_guide import apply_fastener_revision,apply_effective_torso_service,validate_torso_service
source=(G/'full-build-data.json').read_bytes();base=json.loads(source);before=copy.deepcopy(base)
proposal=D/'fastener-patch-proposal.json';revision=json.loads(proposal.read_text())
service_path=G/'non-head-review/torso-service-steps.json';service=json.loads(service_path.read_text())
validate_torso_service(base,service,service_path)
effective=apply_fastener_revision(base,revision,proposal)
effective_service=apply_effective_torso_service(base,service,effective)
assert effective_service==service,'Integral seats must preserve service workflow'
(D/'viewer-integration-effective-torso-service.json').write_text(json.dumps(effective_service,separators=(',',':')))
assert base==before,'Caller/source data mutated'
assert hashlib.sha256((G/'full-build-data.json').read_bytes()).hexdigest()==revision['sourceDataSha256']
parts={p['key']:p for p in effective['parts']};oldparts={p['key']:p for p in base['parts']};screws={c['id']:c for c in effective['screws']};oldscrews={c['id']:c for c in base['screws']}
changed_parts={k for k in parts if parts[k]!=oldparts[k]};assert changed_parts=={'lower','right_lower','neck_pitch'}
changed_screws={k for k in screws if screws[k]!=oldscrews[k]};assert changed_screws==set(effective['fastenerRevision']['screwIds']) and len(changed_screws)==14
assert not any(c.get('length_mm')==5 and re.match(r'^M2\s*[x×]',c['spec']) for c in screws.values())
mesh_rows=[]
for key in changed_parts:
    p=parts[key];file=D/revision['geometryCandidates'][key]['worldMesh'];raw=file.read_bytes();count=struct.unpack_from('<I',raw,80)[0]
    expected=[]
    for i in range(count):expected.extend(struct.unpack_from('<9f',raw,84+i*50+12))
    decoded=struct.unpack('<'+'f'*(len(base64.b64decode(p['positionB64']))//4),base64.b64decode(p['positionB64']))
    assert tuple(expected)==decoded and p['triangles']==count
    indices=struct.unpack('<'+'I'*(len(base64.b64decode(p['indexB64']))//4),base64.b64decode(p['indexB64']))
    assert indices==tuple(range(count*3))
    assert p['positionB64']!=oldparts[key]['positionB64']
    mesh_rows.append({'key':key,'triangles':count,'exactWorldStlVertices':True,'sha256':hashlib.sha256(raw).hexdigest()})
for key in changed_screws:
    a,b=oldscrews[key],screws[key];assert b['length_mm']==6
    oldtip=[a['world_center_mm'][i]-a['world_axis'][i]*a['length_mm'] for i in range(3)]
    newtip=[b['world_center_mm'][i]-b['world_axis'][i]*b['length_mm'] for i in range(3)]
    assert max(abs(x-y) for x,y in zip(oldtip,newtip))<1e-6
    if key.startswith('E-imu'):
        assert b['engagement_mm']==4.0 and b['stack_mm']['head_standoff_at_contact']==1.8
        assert abs(newtip[2]-29.5)<1e-6
    else:
        assert b['engagement_mm']==a['engagement_mm']
        assert b['stack_mm']==[v+1 for v in a['stack_mm']]
oldops={o['id']:o for m in base['modules'] for o in m['operations']};ops={o['id']:o for m in effective['modules'] for o in m['operations']}
changed_ops={k for k in ops if ops[k]!=oldops[k]};assert changed_ops=={'left-leg-10','right-leg-10','neck-04','imu-02'}
assert not re.search(r'M2\s*[x×]\s*5\b',json.dumps(effective['modules'],ensure_ascii=False))
negative=[]
for label,mutator in [('unready',lambda x:x.update(integrationReady=False)),('wrong-source',lambda x:x.update(sourceDataSha256='bad')),('wrong-report',lambda x:x.update(reportSha256='bad')),('changed-screw',lambda x:x['replacements'][0].update(newSeatAdditionMm=0)),('changed-mesh',lambda x:x['geometryCandidates']['lower'].update(worldMeshSha256='bad'))]:
    bad=copy.deepcopy(revision);mutator(bad)
    try:apply_fastener_revision(base,bad,proposal)
    except ValueError:negative.append(label)
    else:raise AssertionError('Accepted '+label)
result={'passed':True,'sourceSha256':hashlib.sha256(source).hexdigest(),'effectiveDataSha256':hashlib.sha256(json.dumps(effective,separators=(',',':')).encode()).hexdigest(),'sourceUnchanged':True,'callerUnchanged':True,'meshRows':mesh_rows,'exactChangedScrewIds':sorted(changed_screws),'changedOperationIds':sorted(changed_ops),'tipLocationsUnchanged':True,'unrelatedPartsAndScrewsUnchanged':True,'negativeControlsRejected':negative,'physicalFitVerified':False}
(D/'viewer-integration-results.json').write_text(json.dumps(result,indent=2)+'\n')
# Test artifact only: main bundle remains the owner's separate publication action.
(D/'viewer-integration-effective-data.json').write_text(json.dumps(effective,separators=(',',':')))
print(json.dumps({k:v for k,v in result.items() if k not in ('meshRows','exactChangedScrewIds')},indent=2))
