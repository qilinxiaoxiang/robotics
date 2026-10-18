"""One USB span, one obstacle, neutral pose. Run via the bounded CAD launcher.

This is a diagnostic, not assembly or articulation acceptance. The 25 mm
SC0727 mould lengths and receiving cross sections remain engineering bounds.
"""
from pathlib import Path
import argparse,base64,hashlib,json,os,sys,itertools,types
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1', 'Use run_bounded_cad.py'
import numpy as np,trimesh,manifold3d as mf
from route_geometry import circular_arc,fillet_polyline,tube,unit

D=Path(__file__).resolve().parent;H=D.parent.parent
CACHE=D/'robot-source-cache' if (D/'robot-source-cache/index.json').exists() else H/'camera-ribbon-repair/head-source-cache'
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('span',type=int)
p.add_argument('obstacle',help='Source part key, self for all inter-component pairs, or export to save diagnostic meshes')
p.add_argument('--plan',type=Path,default=D/'vertical-usb-length-plan.json')
p.add_argument('--overrides',type=Path,help='JSON mapping part keys to absolute STL paths')
p.add_argument('--manifest',type=Path,action='append',default=[],help='Current candidate manifest; paths relative to head redesign. May be repeated in precedence order.')
p.add_argument('--domain',nargs=2,type=int,metavar=('START','COUNT'),help='Bounded contiguous joint samples; retain native-collision classifications')
p.add_argument('--pose-indices',nargs='+',type=int,help='At most80 unique explicit pose indices selected by a conservative broad phase')
p.add_argument('--stop-on-hit',action='store_true')
p.add_argument('--result-root',type=Path,default=D)
args=p.parse_args();hashes={}
assert not (args.domain and args.pose_indices),'Choose one pose selection mechanism'
selectionSuffix='-domain-%d-%d'%tuple(args.domain) if args.domain else ('-poses-'+hashlib.sha256(json.dumps(args.pose_indices).encode()).hexdigest()[:12] if args.pose_indices else '')
def read(path):
    path=Path(path);b=path.read_bytes();hashes[str(path.resolve())]=hashlib.sha256(b).hexdigest();return b
topologyChecks=[]
def solid(mesh):
    # Native shell boolean edges can collapse on forced float32 conversion.
    result=mf.Manifold(mf.Mesh64(np.asarray(mesh.vertices,np.float64),np.asarray(mesh.faces,np.uint64)))
    assert result.status()==mf.Error.NoError and result.volume()>0,'Invalid or empty solid'
    if not mesh.is_watertight:
        # Some vendor solids contain closed shells touching along an edge.
        # Trimesh merges their coincident vertices. Only separate topology if
        # every input triangle coordinate remains exactly unchanged.
        mm=result.to_mesh64()
        normalized=trimesh.Trimesh(mm.vert_properties[:,:3],mm.tri_verts,process=False)
        def digest(m):
            t=np.ascontiguousarray(m.vertices[m.faces],dtype=np.float64)
            vv=np.sort(t.view('V24').reshape(-1,3),axis=1)
            return hashlib.sha256(np.sort(vv.view('V72').reshape(-1)).tobytes()).hexdigest()
        sourceDigest=digest(mesh)
        assert sourceDigest==digest(normalized),'Normalization changed triangle geometry'
        assert normalized.is_watertight and normalized.is_volume,'Open mesh cannot establish a collision-free solid'
        assert np.array_equal(mesh.bounds,normalized.bounds),'Normalization moved geometry'
        topologyChecks.append({'triangleCoordinateMultisetSha256':sourceDigest,'triangleCount':len(mesh.faces),'readbackWatertight':True,'readbackPositiveVolume':True,'boundsUnchanged':True,'geometryChanged':False,'rule':'Split only coincident contact vertices; no facet added, removed or moved.'})
    return result
def box(start,axis,length,width,thickness,width_axis=None):
    z=unit(axis);x=unit(np.cross(z,[0,1,0])) if width_axis is None else unit(width_axis);y=np.cross(z,x)
    T=np.eye(4);T[:3,:3]=np.column_stack([x,y,z]);T[:3,3]=np.array(start)+z*length/2
    return mf.Manifold.cube([width,thickness,length],True).transform(T[:3])
plan=json.loads(read(args.plan));assert hashlib.sha256(read(plan['sourcePose'])).hexdigest()==plan['sourcePoseSha256'],'Stale Pi pose'
piPose=json.loads(read(plan['sourcePose']));piWidthAxis=np.array(piPose['worldTransform'])[:3,0]
for path,expected in plan['sourceHashes'].items():assert hashlib.sha256(read(path)).hexdigest()==expected,('Stale USB input',path)
row=next(r for r in plan['rows'] if r['scFlexibleMm']==args.span);assert row['possibleInThisFamily']
start=np.array(plan['piPlugTailMm']);axis=np.array(plan['piPlugOutwardAxis']);u=np.array(plan['scFinalDirection'])
arc,L=circular_arc(start,axis,u,10)
tail=np.array(row['usbAFemaleCableExitMm']);straight=np.linspace(arc[-1],tail,int(np.ceil(np.linalg.norm(tail-arc[-1])/.25))+1)
scPoints=np.vstack([arc,straight[1:]])
acPoints,acLength=fillet_polyline(row['acWaypointsMm'],10)
if 'cEndArc' in plan:
    end=plan['cEndArc'];endPoints,endLength=circular_arc(end['startMm'],end['incoming'],end['outgoing'],end['radiusMm'])
    assert np.linalg.norm(acPoints[-1]-endPoints[-1])<1e-6
    acPoints=np.vstack([acPoints,endPoints[-2::-1]]);acLength+=endLength
assert abs(acLength-102.5)<1e-6
assert abs(L+np.linalg.norm(tail-arc[-1])-args.span)<1e-6
c=json.loads(read(D.parent/'full-harness/published-usbc-verification.json'))
parts={
    'scMicroBReceiving':box(plan['piShoulderMm'],axis,25,8,18,piWidthAxis),
    'scFlexibleReceiving':solid(tube(scPoints,4.5,start_tangent=axis,end_tangent=u)),
    'scFemaleReceiving':box(tail,u,25,12,20),
    'acMaleReceiving':box(row['usbAMatingPointMm'],u,22.9,12,20),
    'acFlexibleReceiving':solid(tube(acPoints,4.5,start_tangent=u,end_tangent=-np.array(c['outwardAxis']))),
    'acUsbCReceiving':box(c['seatedShoulderWorldMm'],c['outwardAxis'],27,7,12),
}
assert all(s.status()==mf.Error.NoError and s.volume()>0 for s in parts.values())
outdir=args.result_root/('span-%d-diagnostic'%args.span);outdir.mkdir(exist_ok=True,parents=True)
checks=[]
cableSelfChecks={}
if args.obstacle=='export':
    sys.path.insert(0,str(H/'gpio-audio-repair'))
    from precision_mesh import export as preciseExport
    read(H/'gpio-audio-repair/precision_mesh.py')
    context=types.SimpleNamespace(np=np,tm=trimesh,mf=mf)
    for key,s in parts.items():
        preciseExport(context,s,outdir/(key+'.stl'))
elif args.obstacle=='self':
    assert not args.domain and not args.pose_indices,'Inter-component self checks are in the shared head frame'
    cases=[]
    for (ka,a),(kb,b) in itertools.combinations(parts.items(),2):
        intersection=a^b;vol=max(0.,float(intersection.volume()))
        assert intersection.status()==mf.Error.NoError,'Invalid component intersection'
        checks.append({'moving':ka,'obstacle':kb,'overlapMm3':vol,'intersectionBoundsMm':list(intersection.bounding_box()) if vol>1e-5 else None})
    from check_cable_self import check as checkCableSelf
    cableSelfChecks={name:checkCableSelf(points,4.5,10) for name,points in [('scFlexibleReceiving',scPoints),('acFlexibleReceiving',acPoints)]}
    read(D/'check_cable_self.py')
else:
    cfg=json.loads(read(H/'viewer-candidate.json'));files={k:str(H/v) for k,v in cfg['replacementMeshes'].items()}
    files.update({a['key']:str(H/a['mesh']) for a in cfg['additionalParts']})
    removed=set(cfg.get('removedParts',[]))
    for manifestPath in args.manifest:
        manifest=json.loads(read(manifestPath))
        if 'baseViewerCandidateSha256' in manifest:
            assert hashlib.sha256(read(H/'viewer-candidate.json')).hexdigest()==manifest['baseViewerCandidateSha256'],'Stale base viewer'
        for source,expected in manifest.get('sourceHashes',{}).items():
            assert hashlib.sha256(read(source)).hexdigest()==expected,('Stale manifest source',source)
        files.update({k:str(H/v) for k,v in manifest.get('replacementMeshes',{}).items()})
        files.update({a['key']:str(H/a['mesh']) for a in manifest.get('additionalParts',[])})
        if 'fullFFC' in manifest.get('diagnosticGeometry',{}):files['camera_ribbon_receiving']=str(H/manifest['diagnosticGeometry']['fullFFC'])
        removed.update(manifest.get('removedParts',[]))
    if args.overrides:files.update(json.loads(read(args.overrides)))
    key=args.obstacle
    assert key not in removed,('Obsolete candidate part requested',key)
    if key in files:
        read(files[key]);ob=solid(trimesh.load(files[key],force='mesh'))
    else:
        cache=CACHE;index=json.loads(read(cache/'index.json'))
        with open(index['sourceFile'],'rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==index['sourceDataSha256'],'Stale source cache'
        raw=json.loads(read(cache/index['parts'][key]));hashes[index['sourceFile']]=index['sourceDataSha256']
        ob=solid(trimesh.Trimesh(np.frombuffer(base64.b64decode(raw['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(raw['indexB64']),'<u4').reshape(-1,3),process=True))
    cases=[(-1,{'jointDegrees':{},'nativeShellOriginalBottomIntersectionsMm3':{}})]
    if args.domain or args.pose_indices:
        domain=json.loads(read(D/'rigid-domain.json'))
        if args.domain:
            first,count=args.domain;assert first>=0 and 0<count<=80
            assert first+count<=len(domain['samples']),'Domain slice exceeds inventory'
            cases=list(enumerate(domain['samples']))[first:first+count]
        else:
            assert 0<len(args.pose_indices)<=80 and len(set(args.pose_indices))==len(args.pose_indices)
            assert all(0<=i<len(domain['samples']) for i in args.pose_indices)
            cases=[(i,domain['samples'][i]) for i in args.pose_indices]
        assert cases
        fkpath=H.parent.parents[1]/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py'
        read(fkpath);sys.path.insert(0,str(fkpath.parent));from assembly_fk import fk,XML
        read(XML)
        baseline,_=fk();cache=CACHE;index=json.loads(read(cache/'index.json'))
        body=json.loads(read(cache/index['parts'][args.obstacle]))['body'] if args.obstacle in index['parts'] else 'jaw_soft'
        assert body in baseline,('Unknown source body',body)
    checkpoint=outdir/(args.obstacle+selectionSuffix+'.jsonl')
    with checkpoint.open('w') as stream:
        for poseIndex,case in cases:
            current=ob
            if args.domain or args.pose_indices:
                poses,_=fk({k:np.deg2rad(v) for k,v in case['jointDegrees'].items()})
                headDelta=poses['jaw_soft']@np.linalg.inv(baseline['jaw_soft']);partDelta=poses[body]@np.linalg.inv(baseline[body])
                relative=np.linalg.inv(headDelta)@partDelta;current=ob.transform(relative[:3])
            bb=np.array(current.bounding_box()).reshape(2,3);hit=False
            for key,s in parts.items():
                sb=np.array(s.bounding_box()).reshape(2,3);vol=0.;ib=None
                if np.all(sb[0]<bb[1]) and np.all(bb[0]<sb[1]):
                    intersection=s^current;vol=max(0.,float(intersection.volume()))
                    assert intersection.status()==mf.Error.NoError,'Invalid obstacle intersection'
                    if vol>1e-5:ib=list(intersection.bounding_box())
                item={'moving':key,'obstacle':args.obstacle,'overlapMm3':vol,'intersectionBoundsMm':ib,'poseIndex':poseIndex,'jointDegrees':case['jointDegrees'],'nativeRigidBlocked':bool(case['nativeShellOriginalBottomIntersectionsMm3'])}
                if key=='scMicroBReceiving' and args.obstacle=='pi' and vol>1e-5:
                    contactMesh=intersection.to_mesh64();depth=(np.asarray(contactMesh.vert_properties)[:,:3]-np.asarray(plan['piShoulderMm']))@axis
                    item['signedDistanceFromSeatedPlugPlaneMm']=[float(depth.min()),float(depth.max())]
                checks.append(item);stream.write(json.dumps(item)+'\n');stream.flush();os.fsync(stream.fileno());hit=hit or vol>1e-5
            if hit and args.stop_on_hit:break
for source in [Path(__file__),D/'route_geometry.py',H/'curved-head/board_envelopes.py',D.parent/'full-harness/build_harness.py']:read(source)
report={'status':'NEUTRAL_SINGLE_OBSTACLE_DIAGNOSTIC','spanMm':args.span,'sourceHashes':hashes,'checks':checks,'allClear':bool(checks) and all(r['overlapMm3']<=1e-5 for r in checks),'receivingDimensionsMm':{'piMicroB':[25,18,8],'scFemale':[25,20,12],'acMale':[22.9,20,12],'usbC':[27,12,7],'scCableOD':4.5,'acCableOD':4.5},'dimensionBoundary':'Preserves legacy full-harness connector receiving bounds; SC cable4.5mm is enlarged from previous3.5mm assumption. Exact SC0727 dimensions remain unverified.','assemblyAccepted':False,'dimensionsVerified':False,'physicalVerified':False}
report['requestedDomainSlice']=args.domain;report['nativeRigidBlockedIsWaiver']=False
report['requestedPoseIndices']=args.pose_indices
report['expectedPairs']=15 if args.obstacle=='self' else (len(cases)*len(parts) if args.obstacle!='export' else 0)
report['selfCheckBoundary']='self checks cover distinct USB components only; nonlocal overlap within each continuous cable and retaining features need separate checks'
report['coverageComplete']=bool(checks) and len(checks)==report['expectedPairs']
report['allClear']=report['allClear'] and report['coverageComplete']
report['continuousCableSelfChecks']=cableSelfChecks
report['componentBoundsMm']={k:list(s.bounding_box()) for k,s in parts.items()}
report['solidValidityChecked']=True
report['contactTopologyNormalizations']=topologyChecks
report['status']='SELF_COMPONENT_AND_CABLE_DIAGNOSTIC' if args.obstacle=='self' else ('SAMPLED_SINGLE_OBSTACLE_DIAGNOSTIC' if args.domain or args.pose_indices else 'NEUTRAL_SINGLE_OBSTACLE_DIAGNOSTIC')
if args.obstacle=='self':report['allClear']=report['allClear'] and all(x['allClear'] and x['coverageComplete'] for x in cableSelfChecks.values())
suffix=selectionSuffix
(outdir/(args.obstacle+suffix+'.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'span':args.span,'obstacle':args.obstacle,'hits':[r for r in checks if r['overlapMm3']>1e-5]}),flush=True)
