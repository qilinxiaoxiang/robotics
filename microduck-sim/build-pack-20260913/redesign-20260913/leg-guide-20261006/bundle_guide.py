from pathlib import Path
import json,re,sys,gzip,base64,hashlib,copy,struct,math,io,os
OUT=Path(__file__).resolve().parent
SIM=OUT.parents[2]
def validate_torso_service(data, service, service_path):
    """Bind a ready service overlay to the exact geometry and reviewed content."""
    def require(condition, message):
        if not condition:
            raise ValueError('Torso service verification: '+message)
    def digest(path):
        require(path.is_file(), 'missing input '+str(path))
        return hashlib.sha256(path.read_bytes()).hexdigest()
    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'))
    require(service.get('integrationReady') is True, 'overlay is not ready for integration')
    require(service.get('module', {}).get('id') == 'torso', 'unexpected module')
    source_path=OUT/'full-build-data.json'
    source_hash=digest(source_path)
    require(service.get('sourceDataSha256') == source_hash, 'source geometry changed')
    require(data == json.loads(source_path.read_text()), 'bundle data differs from reviewed full-build source')
    require(isinstance(service.get('serviceVerification'), str), 'verification report path missing')
    report_path=OUT/service['serviceVerification']
    require(service.get('verificationSha256') == digest(report_path), 'verification report changed')
    report=json.loads(report_path.read_text())
    require(report.get('passed') is True, 'verification did not pass')
    require(report.get('sourceDataSha256') == source_hash, 'verification uses another source')
    content={key:value for key,value in service.items() if key not in {'integrationReady', 'verificationSha256'}}
    require(report.get('payloadContentSha256') == hashlib.sha256(canonical(content).encode()).hexdigest(), 'service steps changed after verification')
    review_dir=service_path.parent
    require(report.get('scriptSha256') == digest(review_dir/'verify_torso_service.py'), 'verification script changed')
    require(isinstance(report.get('inputHashes'), dict) and report['inputHashes'], 'verification input bindings missing')
    for relative, expected in report['inputHashes'].items():
        require(digest(review_dir/relative) == expected, 'verification input changed: '+relative)

def validate_fastener_revision(data, revision, revision_path):
    """Reject stale geometry, screw choices, or a draft replacement proposal."""
    def require(ok, reason):
        if not ok:
            raise ValueError('Fastener revision: '+reason)
    def digest(path):
        require(path.is_file(), 'missing input '+str(path))
        return hashlib.sha256(path.read_bytes()).hexdigest()
    root=revision_path.parent
    require(revision.get('integrationReady') is True, 'proposal is not ready')
    source_path=OUT/'full-build-data.json'
    require(revision.get('sourceDataSha256') == digest(source_path), 'base source changed')
    require(data == json.loads(source_path.read_text()), 'data argument differs from reviewed base')
    require(isinstance(revision.get('sourceHashes'), dict) and revision['sourceHashes'], 'source bindings missing')
    for name, expected in revision['sourceHashes'].items():
        if digest(root/name) != expected:
            import importlib.util
            spec=importlib.util.spec_from_file_location('ledger_projection',OUT/'non-head-review/current_ledger_projection.py')
            proof=importlib.util.module_from_spec(spec);spec.loader.exec_module(proof)
            try:proof.accept(root/name,expected)
            except AssertionError:require(False,'source changed: '+name)
    require(isinstance(revision.get('reportFile'), str), 'report path missing')
    report_path=root/revision['reportFile']
    require(digest(report_path) == revision.get('reportSha256'), 'report changed')
    report=json.loads(report_path.read_text())
    require(report.get('passed') is True and not report.get('errors'), 'verification did not pass')
    require(report.get('sourceDataSha256') == revision['sourceDataSha256'], 'report uses another source')
    content={k:v for k,v in revision.items() if k not in {'integrationReady','reportSha256'}}
    content_hash=hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(report.get('proposalContentSha256') == content_hash, 'proposal changed after verification')
    require(isinstance(revision.get('contextReportFile'), str), 'assembly-context report missing')
    context_path=root/revision['contextReportFile']
    require(digest(context_path) == revision.get('contextReportSha256'), 'assembly-context report changed')
    context=json.loads(context_path.read_text())
    require(context.get('passed') is True and not context.get('errors'), 'assembly-context verification did not pass')
    require(context.get('sourceDataSha256') == revision['sourceDataSha256'], 'assembly-context source changed')
    for name, expected in context.get('sourceHashes', {}).items():
        require(digest(root/name) == expected, 'assembly-context input changed: '+name)
    require(set(revision.get('geometryCandidates',{})) == {'lower','right_lower','neck_pitch'}, 'unexpected revised parts')
    for part, candidate in revision['geometryCandidates'].items():
        for name in ('worldMesh','sourceFrameMesh'):
            require(digest(root/candidate[name]) == candidate[name+'Sha256'], 'mesh changed: '+part+' '+name)
    return report

def stl_world_geometry(path):
    """Encode verified binary STL triangles without changing their world pose."""
    raw=path.read_bytes()
    if len(raw)<84:
        raise ValueError('Fastener revision: truncated STL '+str(path))
    count=struct.unpack_from('<I',raw,80)[0]
    if len(raw)!=84+50*count or not count:
        raise ValueError('Fastener revision: expected complete binary STL '+str(path))
    coordinates=[]
    for i in range(count):
        coordinates.extend(struct.unpack_from('<9f',raw,84+50*i+12))
    if not all(math.isfinite(v) for v in coordinates):
        raise ValueError('Fastener revision: nonfinite mesh '+str(path))
    bounds=[[fn(coordinates[axis::3]) for axis in range(3)] for fn in (min,max)]
    return {'positionB64':base64.b64encode(struct.pack('<'+'f'*len(coordinates),*coordinates)).decode(),
            'indexB64':base64.b64encode(struct.pack('<'+'I'*(count*3),*range(count*3))).decode(),
            'triangles':count,'bounds':bounds,'center':[(a+b)/2 for a,b in zip(*bounds)],
            'dimensions':sorted([b-a for a,b in zip(*bounds)],reverse=True)}

def apply_integral_seat_revision(data, revision, revision_path):
    """Derive viewer data; never change the historical source JSON or caller."""
    validate_fastener_revision(data, revision, revision_path)
    result=copy.deepcopy(data);parts={p['key']:p for p in result['parts']};screws={c['id']:c for c in result['screws']}
    rows=revision['replacements']+revision['guideOnlyReplacements']
    actual_ids=[r['id'] for r in rows]
    expected_ids={c['id'] for c in data['screws'] if c.get('length_mm')==5 and re.match(r'^M2\s*[x×]',c['spec'])}
    if len(actual_ids)!=14 or len(set(actual_ids))!=14 or set(actual_ids)!=expected_ids:
        raise ValueError('Fastener revision: exact 14-position replacement set required')
    revision_id='integral-seat-m2x6-20261008'
    notices={
      'lower':'New-build alternative: M2 × 6 TAP at the left knee requires the revised lower-leg link with four integral 1 mm head seats. The existing knees already use M2 × 6, as you confirmed. With the original 2.8 mm seat, nominal insertion is 3.2 mm against the 3 mm maximum. This does not establish actual damage. Do not dismantle force-fitted completed legs to follow this new-build sequence. A repair sequence that preserves the assembled ankle and foot has not yet been validated.',
      'right_lower':'New-build alternative: M2 × 6 TAP at the right knee requires the revised lower-leg link with four integral 1 mm head seats. The existing knees already use M2 × 6, as you confirmed. With the original 2.8 mm seat, nominal insertion is 3.2 mm against the 3 mm maximum. This does not establish actual damage. Do not dismantle force-fitted completed legs to follow this new-build sequence. A repair sequence that preserves the assembled ankle and foot has not yet been validated.',
      'neck_pitch':'M2 × 6 TAP at ID13 requires the revised head-pitch bracket with four integral 1 mm head seats. Use that revised part before fastening this joint.',
      'imu_clamp':'Use two M2 × 6 TAP pressure screws in the unchanged IMU holder. Stop at rail contact with each head 1.8 mm above the holder; do not tighten the head down. No washer or nut is added.'}
    for key,candidate in revision['geometryCandidates'].items():
        part=parts[key];part.update(stl_world_geometry(revision_path.parent/candidate['worldMesh']))
        part['baseStockFile']=part.get('stockFile');part['stockFile']=candidate['sourceFrameMesh'];part['stockFileName']=candidate['sourceFrameMesh']
        part['geometryKind']='verified-fastener-seat-revision'
        part['name']={'lower':'Replacement left lower-leg link · 1 mm seats','right_lower':'Replacement right lower-leg link · 1 mm seats','neck_pitch':'Replacement head-pitch bracket · 1 mm seats'}[key]
        part['description']=notices[key];part['aliases']='Revised part · '+candidate['sourceFrameMesh']
        part['fastenerRevision']={'id':revision_id,'notice':notices[key],'worldMesh':candidate['worldMesh'],'worldMeshSha256':candidate['worldMeshSha256'],'sourceFrameMesh':candidate['sourceFrameMesh'],'sourceFrameMeshSha256':candidate['sourceFrameMeshSha256'],'optionalForAlreadyAssembledLeg':candidate['optionalForAlreadyAssembledLeg']}
    for row in rows:
        c=screws[row['id']];new_center=row['newHeadSeatWorldMm'];axis=c['world_axis'];old_center=c['world_center_mm']
        if any(abs(new_center[i]-old_center[i]-axis[i])>1e-6 for i in range(3)):
            raise ValueError('Fastener revision: screw tip would move for '+c['id'])
        c['world_center_mm']=new_center;c['length_mm']=6
        if 'selectedNewBuildSpec' in row:
            if row['newSeatAdditionMm']!=1 or row['selectedNewBuildSpec']!='M2 x 6 TAP':
                raise ValueError('Fastener revision: unexpected integral-seat dimensions')
            key=row['reprintPart'];c['spec']=row['selectedNewBuildSpec']
            if row['newLengthMm']!=6 or row['newStackMm']!=[n+1 for n in c['stack_mm']] or row['newWasherMm']!=0:
                raise ValueError('Fastener revision: inconsistent verified stack')
            c['stack_mm']=row['newStackMm'];c['washer_mm']=row['newWasherMm']
            c['engagement_mm']=row['entryMm'];c['penetration_mm']=row['newPenetrationMm'];c['integralSeatAdditionMm']=1
            c['fastenerRevision']={'id':revision_id,'requiresRevisedPart':key,'notice':notices[key],'tipMarginMm':row['tipMarginMm']}
        else:
            if row['newLengthMm']!=6 or row['reprintRequired'] is not False:
                raise ValueError('Fastener revision: unexpected IMU replacement')
            c['spec']=row['newSpec'];depth=row['actualPilotMaterialDepthMm'];c['stack_mm']=row['newStackMm']
            c['engagement_mm']=row['newEngagementMm'];c['contact_plane_z_mm']=row['tipContactPlaneZMm']
            c['fastenerRevision']={'id':revision_id,'requiresRevisedPart':None,'notice':notices['imu_clamp'],'headStandOffAtContactMm':row['headStandOffAtContactMm']}
        c['evidence']='Verified 6 mm revision; original tip location retained. '+c['fastenerRevision']['notice']
        c['audit_file']='fastener-review-20261008/'+revision['reportFile']
    texts={
      'left-leg-10':'New assembly only: use four M2 × 6 TAP with the revised left lower-leg link and its integral 1 mm head seats; entry remains 2.2 mm. The existing knees already have 6 mm screws. Original 2.8 mm seats give 3.2 mm nominal insertion, above the 3 mm maximum. This is not a repair sequence for a completed force-fitted leg; preserving the assembled ankle and foot during replacement has not yet been validated.',
      'right-leg-10':'New assembly only: use four M2 × 6 TAP with the revised right lower-leg link and its integral 1 mm head seats; entry remains 2.2 mm. The existing knees already have 6 mm screws. Original 2.8 mm seats give 3.2 mm nominal insertion, above the 3 mm maximum. This is not a repair sequence for a completed force-fitted leg; preserving the assembled ankle and foot during replacement has not yet been validated.',
      'neck-04':'Use four M2 × 6 TAP with the revised head-pitch bracket and its integral 1 mm head seats; entry remains about 2.10 mm. Fasten them on the detached bracket before mounting it on ID11.',
      'imu-02':notices['imu_clamp']}
    changed_operations=[]
    for module in result['modules']:
        for op in module['operations']:
            if op['id'] in texts:
                op['text']=texts[op['id']];changed_operations.append(op['id'])
                if op['id']=='imu-02':op['motionLabels']={'end':'Rail contact · heads raised'}
    if set(changed_operations)!=set(texts):
        raise ValueError('Fastener revision: expected fastening operations missing')
    result['fastenerRevision']={'id':revision_id,'sourceDataSha256':revision['sourceDataSha256'],'proposalSha256':hashlib.sha256(revision_path.read_bytes()).hexdigest(),'reportSha256':revision['reportSha256'],'partKeys':sorted(revision['geometryCandidates']),'screwIds':actual_ids,'operationIds':changed_operations,'physicalFitVerified':False}
    return result

def apply_fastener_revision(data, revision, revision_path):
    # The verified proposal selects integral seats. Rejected washer candidates
    # remain investigation artifacts and are never a default or fallback.
    from current_stock_fasteners import apply_current_stock_fasteners
    verified=apply_integral_seat_revision(data,revision,revision_path)
    return apply_current_stock_fasteners(data,verified)

def apply_effective_torso_service(base, service, effective):
    """Return the service workflow for the selected, context-verified revision."""
    service_path=OUT/'non-head-review/torso-service-steps.json'
    validate_torso_service(base,service,service_path)
    if effective.get('kneeWasherRepair'):
        raise ValueError('Fastener revision: no verified washer service overlay selected')
    if effective.get('fastenerRevision',{}).get('id')!='v1.4-integral-neck-existing-legs-m2x6':
        raise ValueError('Fastener revision: unexpected effective geometry')
    return copy.deepcopy(service)

def bundle(data, destination='LEFT-LEG.html'):
    # Service instructions are a separate, reviewable overlay. Geometry and the
    # original DATA.modules remain byte-for-byte inputs to the existing bundle.
    service_path=OUT/'non-head-review/torso-service-steps.json'
    has_torso=any(module.get('id') == 'torso' for module in data.get('modules', []))
    if has_torso and not service_path.is_file():
        raise ValueError('Torso service verification: required service overlay is missing')
    service_bytes=service_path.read_bytes() if has_torso else None
    service=json.loads(service_bytes) if service_bytes else None
    if service is not None:
        validate_torso_service(data, service, service_path)
    base_hash=hashlib.sha256()
    for chunk in json.JSONEncoder(separators=(',',':')).iterencode(data): base_hash.update(chunk.encode())
    base_payload_sha256=base_hash.hexdigest()
    revision_path=OUT.parent/'fastener-review-20261008/fastener-patch-proposal.json'
    if has_torso and not revision_path.is_file():
        raise ValueError('Fastener revision: required proposal is missing')
    revision_bytes=revision_path.read_bytes() if has_torso else None
    if revision_bytes is not None:
        base_data=data
        data=apply_fastener_revision(base_data,json.loads(revision_bytes),revision_path)
        service=apply_effective_torso_service(base_data,service,data)
        del base_data
    motion_path=OUT.parent/'workflow-review-20261009/enclosed-wiring-repair/assembly-motion-completion/assembly-motion-overlay.json'
    if has_torso:
        if not motion_path.is_file(): raise ValueError('Current assembly motion overlay is missing')
        from assembly_motion_overlay import apply_motion_overlay
        data,service=apply_motion_overlay(data,service,motion_path)
    wiring=json.loads((OUT/'wiring-guide-data.json').read_text()) if (OUT/'wiring-guide-data.json').exists() else None
    spatial=json.loads((OUT/'wiring-spatial-data.json').read_text()) if (OUT/'wiring-spatial-data.json').exists() else None
    if has_torso:
        from build_body_wiring_adapter import apply_body_wiring_adapter
        data,wiring,spatial=apply_body_wiring_adapter(data,wiring,spatial)
        from build_imu_wiring_adapter import apply_imu_wiring_adapter
        data,wiring,spatial=apply_imu_wiring_adapter(data,wiring,spatial)
        from build_body_data_adapter import apply_body_data_adapter
        data,wiring,spatial=apply_body_data_adapter(data,wiring,spatial)
        from build_input_wiring_adapter import apply_input_wiring_adapter
        data,wiring,spatial=apply_input_wiring_adapter(data,wiring,spatial)
        from build_head_prototype_adapter import apply_head_prototype_adapter
        data,wiring,spatial=apply_head_prototype_adapter(data,wiring,spatial)
    # Bundle the existing MIT Three.js library and its orbit controls inline. No CDN, fetch, server or network.
    three_path=SIM/'microduck-simulator/app/node_modules/three'
    three=(three_path/'build/three.module.js').read_text()
    export=re.search(r'export \{([^}]+)\};?\s*$',three)
    members=[]
    for term in export.group(1).split(','):
        term=term.strip(); bits=term.split(' as ')
        members.append(bits[-1]+':'+bits[0])
    three=three[:export.start()]+'\nreturn {'+','.join(members)+'};'
    orbit=(three_path/'examples/jsm/controls/OrbitControls.js').read_text()
    orbit=re.sub(r"import\s*\{([^}]+)\}\s*from\s*'three';",r'const {\1} = THREE;',orbit,count=1)
    orbit=re.sub(r'export \{ OrbitControls \};?\s*$', 'return OrbitControls;', orbit)
    app=(OUT/'viewer.js').read_text()+'\n'+(OUT/'wiring3d.js').read_text()+'\n'+(OUT/'closure3d.js').read_text()
    template=(OUT/'template.html').read_text()
    # Stream large payloads and HTML; do not hold several UTF-32 copies of the model.
    def pack_json(value, output=None):
        digest=hashlib.sha256(); length=0; compressed=io.BytesIO()
        target=open(output,'wb') if output else None
        try:
            with gzip.GzipFile(fileobj=compressed,mode='wb',compresslevel=6,mtime=0) as gz:
                for chunk in json.JSONEncoder(separators=(',',':')).iterencode(value):
                    raw=chunk.encode(); digest.update(raw); length+=len(raw); gz.write(raw)
                    if target: target.write(raw)
        finally:
            if target: target.close()
        raw_compressed=compressed.getvalue()
        check=hashlib.sha256()
        with gzip.GzipFile(fileobj=io.BytesIO(raw_compressed)) as gz:
            while block:=gz.read(1024*1024): check.update(block)
        if check.digest()!=digest.digest(): raise ValueError('Payload compression readback differs')
        return base64.b64encode(raw_compressed).decode(),digest.hexdigest(),length
    packed,data_sha,payload_length=pack_json(data,OUT/'full-build-data-current.json' if has_torso else None)
    spatial_packed,spatial_sha,spatial_length=pack_json(spatial,OUT/'wiring-spatial-data-current.json' if has_torso else None)
    _,wiring_sha,wiring_length=pack_json(wiring,OUT/'wiring-guide-data-current.json' if has_torso else None)
    paths=json.loads((OUT/'assembly-path-investigation.json').read_text()) if (OUT/'assembly-path-investigation.json').exists() else None
    closure=json.loads((OUT/'closure-approach-investigation.json').read_text())
    manifest={'data_sha256':data_sha,'base_data_sha256':base_payload_sha256,'base_source_file_sha256':service['sourceDataSha256'] if service else None,'effective_data_sha256':data_sha,'spatial_sha256':spatial_sha,'assembly_motion_revision':data.get('assemblyMotionRevision'),'body_wiring_adapter':data.get('bodyWiringAdapter'),'imu_wiring_adapter':data.get('imuWiringAdapter'),'body_data_adapter':data.get('bodyDataAdapter'),'input_wiring_adapter':data.get('inputWiringAdapter'),'head_prototype_revision':data.get('headPrototypeRevision'),'fastener_revision_sha256':hashlib.sha256(revision_bytes).hexdigest() if revision_bytes else None,'compressed_bytes':len(packed),'uncompressed_bytes':payload_length,'lossless':True,'parts':len(data['parts']),'screws':len(data['screws']),'torso_service_sha256':hashlib.sha256(service_bytes).hexdigest() if service_bytes else None,'effective_torso_service_sha256':hashlib.sha256(json.dumps(service,separators=(',',':')).encode()).hexdigest() if service else None}
    manifest.update(wiring_sha256=wiring_sha,wiring_uncompressed_bytes=wiring_length,spatial_uncompressed_bytes=spatial_length)
    before,after=template.split('/*__APP__*/')
    temporary=OUT/(destination+'.tmp')
    with temporary.open('w') as f:
        f.write(before);f.write('const THREE = (()=>{');f.write(three);f.write('})();\nconst OrbitControls = (()=>{');f.write(orbit);f.write('})();\n')
        f.write('(async()=>{const packed="');f.write(packed);f.write('";const raw=Uint8Array.from(atob(packed),c=>c.charCodeAt(0));const DATA=JSON.parse(await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"))).text());\n')
        for name,obj in [('CLOSURE',closure),('PATHS',paths)]:
            f.write('const '+name+'=');json.dump(obj,f,separators=(',',':'));f.write(';\n')
        f.write('const spatialPacked="');f.write(spatial_packed);f.write('";const spatialRaw=Uint8Array.from(atob(spatialPacked),c=>c.charCodeAt(0));const SPATIAL=JSON.parse(await new Response(new Blob([spatialRaw]).stream().pipeThrough(new DecompressionStream("gzip"))).text());\n')
        for name,obj in [('TORSO_SERVICE',service),('WIRING',wiring)]:
            f.write('const '+name+'=');json.dump(obj,f,separators=(',',':'));f.write(';\n')
        f.write(app);f.write('\n})().catch(e=>{const box=document.getElementById("error");box.style.display="block";box.textContent="Guide could not load: "+e.message;console.error(e);});');f.write(after)
    os.replace(temporary,OUT/destination)
    (OUT/'bundle-manifest.json').write_text(json.dumps(manifest,indent=2))

if __name__=='__main__':
    bundle(json.loads((OUT/('full-build-data.json' if '--full' in sys.argv else 'leg-data.json')).read_text()))
    print('GUIDE_UI_BUNDLE_PASS')
