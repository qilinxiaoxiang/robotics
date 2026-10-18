#!/usr/bin/env python3
"""Independent ankle redesign verification; never changes candidate CAD.

Requires the current-check CAD environment. Baseline-only cannot emit the final
acceptance marker. Every motion result is finite sampled digital evidence.
"""
from pathlib import Path
import argparse,base64,hashlib,json,sys,math
import numpy as np
import trimesh
import manifold3d as mf
from scipy.spatial.transform import Rotation
from scipy.spatial import cKDTree

HERE=Path(__file__).resolve().parent
R=HERE.parent
G=R/'leg-guide-20261006'
SIM=R.parents[1]
FKDIR=SIM/'hardware-design-20260912/whole-robot-20260912/assembly'
sys.path.insert(0,str(FKDIR))
from assembly_fk import fk,XML
THRESHOLD=.02

def require(ok,message):
    if not ok: raise AssertionError(message)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text())
def matrix(value):
    t=np.asarray(value,float)
    require(t.shape==(4,4) and np.allclose(t[3],[0,0,0,1]),'invalid rigid frame')
    require(np.allclose(t[:3,:3].T@t[:3,:3],np.eye(3),atol=1e-6) and abs(np.linalg.det(t[:3,:3])-1)<1e-6,'frame must be proper rigid rotation')
    return t

def solid(mesh):
    m=mesh.copy();m.merge_vertices();m.remove_unreferenced_vertices()
    s=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
    require(s.status()==mf.Error.NoError,'non-manifold input')
    require(s.volume()>0,'non-positive-volume input')
    return s

def native_parts():
    data=load(G/'full-build-data.json');meshes={}
    keys=['lower','ankle','smallring','foot','motor6','right_lower','right_ankle','right_smallring','right_foot','motor1']
    for row in data['parts']:
        if row['key'] not in keys: continue
        v=np.frombuffer(base64.b64decode(row['positionB64']),dtype='<f4').reshape(-1,3)
        f=np.frombuffer(base64.b64decode(row['indexB64']),dtype='<u4').reshape(-1,3)
        meshes[row['key']]=trimesh.Trimesh(v,f,process=True)
    return data,meshes,{k:solid(v) for k,v in meshes.items()}

def overlap(a,b): return max(0,float((a^b).volume()))
def rotation_about(pivot,axis,angle):
    r=Rotation.from_rotvec(np.asarray(axis)*angle).as_matrix(); t=np.eye(4)
    t[:3,:3]=r;t[:3,3]=np.asarray(pivot)-r@pivot
    return t

def baseline_check(solids):
    b,_=fk();out={}
    report=load(G/'closure-approach-investigation.json')
    for side,moving,ankle,ring,motor in [('left-leg','lower','ankle','smallring','motor6'),('right-leg','right_lower','right_ankle','right_smallring','motor1')]:
        p=report['paths'][side]
        contact=solids[moving].translate(p['contactTranslation'])
        blocked=overlap(contact,solids[ankle]);ring_overlap=overlap(solids[moving],solids[ring])
        require(blocked>THRESHOLD and ring_overlap>14,'original failure was not reproduced')
        out[side]={'straightRouteContactTranslationMm':p['contactTranslation'],'lowerToBracketOverlapMm3':blocked,'nominalBossToRingOverlapMm3':ring_overlap,'jointPivotMm':b['ankle_left' if side=='left-leg' else 'ankle_right'][:3,3].tolist(),'jointAxis':b['ankle_left' if side=='left-leg' else 'ankle_right'][:3,2].tolist(),'sourceJointRangeDegrees':[-90,90]}
    return out

def candidate_inputs():
    manifest=load(HERE/'preview-data.json')
    require(manifest['prototypeOnly'] is True and manifest['sourceOverwrite'] is False,'prototype/original-source boundary changed')
    require(set(manifest['sides'])=={'left','right'},'both candidate sides required')
    snapshots={};out={};b,_=fk()
    for side,s in manifest['sides'].items():
        t=matrix(s['frameWorld']);sign=1 if side=='left' else -1
        expected=np.array([[sign,0,0],[0,0,-sign],[0,1,0]])
        require(np.allclose(t[:3,:3],expected,atol=1e-8),'wrong shaft-oriented candidate frame')
        pivot=b['ankle_left' if side=='left' else 'ankle_right'][:3,3]
        require(abs(t[0,3]-pivot[0])<1e-5 and abs(t[2,3]-pivot[2])<1e-5,'candidate joint axis moved')
        printed=[p for p in s['parts'] if p.get('localStl')]
        require(len(printed)==3,'base/cheek/sleeve coverage')
        pieces={}
        for p in printed:
            require(p['coordinateFrame']=='guide-world-mm','undeclared STL coordinate convention')
            local=trimesh.load(p['localStl'],force='mesh',process=True)
            world=trimesh.load(p['stl'],force='mesh',process=True)
            native_world=local.copy().apply_transform(t)
            error=max(cKDTree(native_world.vertices).query(world.vertices)[0].max(),cKDTree(world.vertices).query(native_world.vertices)[0].max())
            require(error<2e-5,'local/world export disagreement '+p['key'])
            a=solid(local)
            require(len(a.decompose())==1,'disconnected islands in printed '+p['key'])
            require(abs(a.volume()-p['volumeMm3'])<.05,'part volume metadata does not bind STL '+p['key'])
            require(len(local.faces)==p['triangles'],'part triangle metadata stale '+p['key'])
            for path in [p['localStl'],p['stl']]:snapshots[path]=sha(path)
            name=p['key'].split('_')[-1]
            require(name in {'base','cheek','sleeve'},'unknown replacement part')
            pieces[name]={'mesh':local,'solid':a,'row':p,'worldMesh':world,'frameErrorMm':float(error)}
        out[side]={'frame':t,'parts':pieces,'manifest':s}
    return manifest,out,snapshots

def cylinder(radius,z0,z1,xy=(0,0)):
    return mf.Manifold.cylinder(z1-z0,radius,radius,96).translate([*xy,z0])
def slab(z0,z1):
    return mf.Manifold.cube([200,200,z1-z0]).translate([-100,-100,z0])
def axis_cylinder(radius,a,b):
    a=np.asarray(a,float);b=np.asarray(b,float);d=b-a;length=np.linalg.norm(d)
    require(length>0,'zero-length hardware envelope')
    z=d/length;helper=np.array([1.,0,0]) if abs(z[0])<.8 else np.array([0.,1,0])
    x=np.cross(helper,z);x/=np.linalg.norm(x);y=np.cross(z,x)
    rotation=np.stack([x,y,z],axis=1)
    return mf.Manifold.cylinder(length,radius,radius,96).transform(np.c_[rotation,a])

def hardware_envelopes(side_data,frame):
    out={}
    for f in side_data['fasteners']:
        h=np.asarray(f['headSeatLocal'],float);tip=np.asarray(f['tipLocal'],float)
        axis=np.linalg.inv(frame)[:3,:3]@np.asarray(f['axis'],float)
        require(np.allclose(np.linalg.norm(axis),1) and np.allclose(tip,h-axis*f['length'],atol=1e-6),'fastener insertion axis/length mismatch')
        require(np.allclose((frame@np.r_[h,1])[:3],f['headSeatWorld'],atol=1e-6),'hardware head frame mismatch')
        require(np.allclose((frame@np.r_[tip,1])[:3],f['tipWorld'],atol=1e-6),'hardware tip frame mismatch')
        diameter=float(__import__('re').search(r'M([0-9.]+)',f['spec']).group(1))
        out[f['key']]={'row':f,'axis':axis,'headPoint':h,'tipPoint':tip,'shaft':axis_cylinder(diameter/2,tip,h),'head':axis_cylinder(f['headDiameter']/2,h,h+axis*f['headHeight']),'tool':axis_cylinder(f['driverDiameter']/2,h+axis*f['headHeight'],h+axis*(f['headHeight']+f['driverReach']))}
    return out

def hardware_check(side_data,parts,fixed,frame):
    hardware=hardware_envelopes(side_data,frame);rows=[]
    require(len(hardware)==2,'exactly two removable-side retainers per ankle')
    for key,h in hardware.items():
        f=h['row'];require(f['spec']=='M2 x 8 TAP' and f['quantity']==1,'new screw type/quantity changed')
        for kind in ['head','tool']:
            hits={name:overlap(h[kind],a) for name,a in {**{n:p['solid'] for n,p in parts.items()},**fixed}.items()}
            require(max(hits.values())<.005,'head/driver obstructed '+key+' '+kind+' '+str(hits))
        for name,a in fixed.items():require(overlap(h['shaft'],a)<.005,'new screw shaft obstructs '+name+' '+key)
        require(overlap(h['shaft'],parts['cheek']['solid'])<.005,'clearance bore missing '+key)
        axis=h['axis'];head=h['headPoint'];entry=head-axis*f['clearanceLength'];end=entry-axis*f['pilotDepth'];tip=h['tipPoint']
        require(abs(np.linalg.norm(entry-tip)-f['engagement'])<1e-6 and abs(np.linalg.norm(tip-end)-f['blindPilotReserve'])<1e-6,'declared thread engagement/reserve inconsistent '+key)
        require(f['engagement']>=3.4 and f['blindPilotReserve']>=.49,'insufficient designed engagement/reserve '+key)
        core=axis_cylinder(.78,end+axis*.02,entry-axis*.02)
        require(overlap(core,parts['base']['solid'])<.005,'base pilot core not open '+key)
        annulus=axis_cylinder(1.95,end+axis*.03,entry-axis*.03)-axis_cylinder(.83,end+axis*.03,entry-axis*.03)
        missing=(annulus-parts['base']['solid']).volume()
        require(missing<.005,'pilot annulus lacks continuous surrounding wall '+key+' '+str(missing))
        floor=axis_cylinder(.70,end-axis*.35,end-axis*.05)
        require((floor-parts['base']['solid']).volume()<.005,'blind pilot floor missing '+key)
        bearing=axis_cylinder(1.90,head-axis*.08,head-axis*.02)-axis_cylinder(1.22,head-axis*.08,head-axis*.02)
        require((bearing-parts['cheek']['solid']).volume()<.005,'head bearing annulus missing '+key)
        stl_row=next(p for p in side_data['parts'] if p['key']==key)
        require(sha(stl_row['stl'])==stl_row['stlSha256'],'screw envelope source stale '+key)
        actual=in_frame(trimesh.load(stl_row['stl'],force='mesh',process=True),frame)
        require((actual-(h['head']+h['shaft'])).volume()<.005,'delivered hardware differs from conservative tested envelope '+key)
        rows.append({'id':key,'spec':f['spec'],'engagementMm':f['engagement'],'blindReserveMm':f['blindPilotReserve'],'continuousCheckedAnnulusOuterRadiusMm':1.95,'pilotAnnulusMissingMm3':missing,'headAndToolClear':True,'threadsExplicitlyModeled':False})
    return hardware,rows

def assembly_check(side,s,native_meshes,hardware):
    prefix='' if side=='left' else 'right_';t=s['frame'];p=s['parts']
    lower=in_frame(native_meshes[prefix+'lower'],t);motor=in_frame(native_meshes['motor6' if side=='left' else 'motor1'],t)
    moving={'lower':lower,'motor':motor,'sleeve':p['sleeve']['solid']}
    package=translation_samples(moving,{'base':p['base']['solid']},[0,30,0],[0,0,0])
    for row in package:
        require(row['pairs']['lower--base']<.005 and row['pairs']['sleeve--base']<.005,'new open-base package route obstructed '+side)
        # Right manufacturer/source face already has sub-micron registration
        # contact. Do not widen a global collision threshold to hide it.
        if row['pairs']['motor--base']>.02:
            original=in_frame(native_meshes[prefix+'ankle'],t)
            hit=motor.translate(row['translationMm'])^p['base']['solid']
            bounds=hit.bounding_box();extent=np.array(bounds[3:])-bounds[:3]
            require(side=='right' and hit.volume()<.14 and min(extent)<.0011 and (hit-original).volume()<.005,'new motor collision hidden as source contact '+side)
    fixed={'base':p['base']['solid'],'lower':lower,'motor':motor,'sleeve':p['sleeve']['solid']}
    cap=translation_samples({'cheek':p['cheek']['solid']},fixed,[0,0,12],[0,0,0])
    require(max(v for row in cap for v in row['pairs'].values())<.005,'removable cheek/register route obstructed '+side)
    # Verify the source straight foot route specifically against added matter.
    old=in_frame(native_meshes[prefix+'ankle'],t);added=(p['base']['solid']+p['cheek']['solid'])-old
    foot=in_frame(native_meshes[prefix+'foot'],t)
    foot_fixed={'newBody':added}
    for k,h in hardware.items():foot_fixed[k]=h['head']+h['shaft']
    foot_path=translation_samples({'foot':foot},foot_fixed,[0,-32,0],[0,0,0])
    require(max(v for row in foot_path for v in row['pairs'].values())<.005,'new structure obstructs original foot approach '+side)
    return {'packagePoseCount':len(package),'packagePairs':package,'capPoseCount':len(cap),'capPairs':cap,'retainedFootPoseCount':len(foot_path),'retainedFootAddedObstaclePairs':foot_path,'rightSourceContactRetained':side=='right','scope':'Finite native-solid samples; exact clear split/guide and axial separation constrain added parts. Original case fitting and foot mating tolerances remain source/physical checkpoints.'}

def rotation_check(side,s,native_meshes,data,hardware):
    prefix='' if side=='left' else 'right_';t=s['frame'];p=s['parts'];old=in_frame(native_meshes[prefix+'ankle'],t)
    lower=in_frame(native_meshes[prefix+'lower'],t);case=motor_case(data,'motor6' if side=='left' else 'motor1',t);foot=in_frame(native_meshes[prefix+'foot'],t)
    candidate=p['base']['solid']+p['cheek']['solid'];added=candidate-old
    significant_added=added^slab(1.6,100)
    require((added-significant_added).volume()<.005,'unreviewed added material enters fixed-member axial slab '+side)
    min_added_z=significant_added.bounding_box()[2]
    fixed_max_z=max(lower.bounding_box()[5],case.bounding_box()[5])
    require(min_added_z-fixed_max_z>.30,'new support lacks all-angle axial separation '+side)
    for k,h in hardware.items():
        require(min((h['head']+h['shaft']).bounding_box()[2],h['tool'].bounding_box()[2])-fixed_max_z>1,'new hardware enters rotating/fixed axial slab '+k)
    rows=[]
    for angle in range(-90,91,5):
        q=np.c_[Rotation.from_euler('z',angle,degrees=True).as_matrix(),[0,0,0]]
        original={mk+'--'+fk:overlap(a.transform(q),b) for mk,a in {'ankle':old,'foot':foot}.items() for fk,b in {'lower':lower,'case':case}.items()}
        current={mk+'--'+fk:overlap(a.transform(q),b) for mk,a in {'ankle':candidate,'foot':foot}.items() for fk,b in {'lower':lower,'case':case}.items()}
        free=max(original.values())<=THRESHOLD
        require(not free or max(current.values())<=THRESHOLD,'candidate loses source-clear sampled angle '+side+' '+str(angle))
        rows.append({'angleDegrees':angle,'originalPairsMm3':original,'candidatePairsMm3':current,'originalClear':free,'candidateClear':max(current.values())<=THRESHOLD})
    return {'sourceXmlRangeDegrees':[-90,90],'stepDegrees':5,'sourceClearSampleAngles':[r['angleDegrees'] for r in rows if r['originalClear']],'addedMaterialContinuousAxialGapMm':min_added_z-fixed_max_z,'addedHardwareAxialGapCertified':True,'properCaseExcludedMovingHornSolids':[3,9],'samples':rows,'scope':'All-angle axial separation for newly added body/hardware. Original complete ankle/foot source-range comparison is finite5-degree sampling; no full ±90-degree physical-clear or loaded-strength claim.'}

def mesh_from_row(row):
    v=np.frombuffer(base64.b64decode(row['positionB64']),dtype='<f4').reshape(-1,3)
    f=np.frombuffer(base64.b64decode(row['indexB64']),dtype='<u4').reshape(-1,3)
    return trimesh.Trimesh(v,f,process=True)

def static_full_guide_check(side,s,data,hardware,native_meshes):
    prefix='' if side=='left' else 'right_';t=s['frame'];parts=s['parts']
    old=in_frame(native_meshes[prefix+'ankle'],t)
    added=(parts['base']['solid']+parts['cheek']['solid'])-old
    candidates={'addedPrintedBody':added.transform(t[:3,:])}
    candidates.update({k:(h['head']+h['shaft']).transform(t[:3,:]) for k,h in hardware.items()})
    excluded={prefix+'ankle',prefix+'smallring',prefix+'lower',prefix+'foot','motor6' if side=='left' else 'motor1'}
    checks=[]
    for row in data['parts']:
        if row['key'] in excluded:continue
        box=np.array(row['bounds'])
        targets=[]
        for key,a in candidates.items():
            bounds=np.array(a.bounding_box());ab=np.array([bounds[:3],bounds[3:]])
            if np.any(ab[0]>box[1]) or np.any(ab[1]<box[0]):continue
            targets.append((key,a))
        if not targets:continue
        other=solid(mesh_from_row(row))
        for key,a in targets:
            hit=overlap(a,other)
            require(hit<.005,'candidate clashes with other installed '+row['key']+' '+side+' '+str(hit))
            checks.append({'candidate':key,'installedPart':row['key'],'overlapMm3':hit})
    return {'allOtherInstalledMeshesScreened':len(data['parts'])-len(excluded),'nativeBooleanBroadPhasePairs':checks,'pose':'source zero/reference pose, not calibrated hardware zero','otherLegIncluded':True}

def print_review_binding():
    r=load(HERE/'print-review.json')
    rows=r['candidate_reviews']
    require(len(rows)==6,'six replacement print-geometry reviews required')
    for p in rows:
        require(sha(p['file'])==p['sha256'] and sha(p['world_file'])==p['world_sha256'],'print review uses superseded candidate STL '+p['key'])
        require(p['watertight'] is True and p['components']==1,'print geometry not one closed part '+p['key'])
        require(p.get('print_orientation_candidates') and p.get('functional_surfaces') is not None,'print-facing/functional surfaces not assessed '+p['key'])
    require(r['native_slice_verified'] is False and r['printed_sample_verified'] is False and r['strength_verified'] is False and r['printing_performed'] is False,'unperformed physical/native work marked accepted')
    return {'file':str(HERE/'print-review.json'),'sha256':sha(HERE/'print-review.json'),'state':r['review_state'],'scope':r['scope'],'nativeSliceVerified':False,'printedSampleVerified':False,'strengthVerified':False,'printReady':r.get('print_ready',False),'note':'Print-facing geometry and source/STL identity reviewed. Trial orientations/support/functional-finish holds remain exactly as recorded; this mechanical PASS does not accept a native print job.'}

def verify():
    data,meshes,solids=native_parts();baseline=baseline_check(solids)
    manifest,inputs,snapshot=candidate_inputs()
    require(manifest==load(HERE/'candidate-manifest.json'),'preview/candidate manifest differ')
    for path,digest in manifest['sourceHashes'].items():require(sha(path)==digest,'native source changed '+path)
    require(sha(HERE/'generate_candidate.py')==manifest['generatorSha256'],'CAD generator changed after export')
    require(sha(HERE/'finalize_manifest.py')==manifest['manifestBuilderSha256'],'manifest builder changed after export')
    structure=candidate_structure_check(inputs,meshes);result={}
    print('Checked actual native baseline and replacement single solids/axes/foot interfaces.',flush=True)
    for side,s in inputs.items():
        prefix='' if side=='left' else 'right_';t=s['frame']
        fixed={'lower':in_frame(meshes[prefix+'lower'],t),'motor':in_frame(meshes['motor6' if side=='left' else 'motor1'],t),'foot':in_frame(meshes[prefix+'foot'],t)}
        hardware,hchecks=hardware_check(s['manifest'],s['parts'],fixed,t)
        paths=assembly_check(side,s,meshes,hardware)
        static=static_full_guide_check(side,s,data,hardware,meshes)
        rotation=rotation_check(side,s,meshes,data,hardware)
        result[side]={'structure':structure[side],'hardware':hchecks,'assembly':paths,'fullGuideStatic':static,'rotation':rotation}
        print(side+' native paths, retained foot, per-hole engagement, actual head/tool envelopes and motion comparison checked.',flush=True)
    printing=print_review_binding()
    for path,digest in snapshot.items():require(sha(path)==digest,'candidate changed during independent check')
    require(sha(HERE/'preview-data.json')==sha(HERE/'candidate-manifest.json'),'manifest changed during independent check')
    report={'passed':True,'scope':'Independent digital prototype mechanical checks; not physical assembly, native print-job, loaded strength, live motor or visual pickup acceptance.','problemIds':['P5','P6'],'baseline':baseline,'candidate':result,'sourceHashes':{str(G/'full-build-data.json'):sha(G/'full-build-data.json'),str(XML):sha(XML),str(SIM/'PROJECT-CONTEXT.json'):sha(SIM/'PROJECT-CONTEXT.json')},'candidateFileHashes':snapshot,'candidateManifestSha256':sha(HERE/'candidate-manifest.json'),'verifierSha256':sha(__file__),'printGeometryReview':printing,'physicalFitVerified':False,'physicalStrengthVerified':False,'printingOrPoweringPerformed':False}
    (HERE/'mechanical-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'sides':2,'printedParts':6,'newFasteners':4,'sourceInterferenceRemoved':True,'retainedFootChecked':True,'fullGuideStaticChecked':True,'printedFitVerified':False,'nativePrintReady':False,'candidateManifestSha256':report['candidateManifestSha256']}))
    print('ANKLE_REDESIGN_CHECK_PASS')
    return report
def in_frame(mesh,t):return solid(mesh.copy().apply_transform(np.linalg.inv(t)))
def symmetric_difference_volume(a,b):return max(0,(a-b).volume())+max(0,(b-a).volume())
def translation_samples(moving,fixed,start,stop,step=.20):
    length=np.linalg.norm(np.asarray(start)-stop);count=math.ceil(length/step)+1;rows=[]
    for f in np.linspace(0,1,count):
        v=np.asarray(start)*(1-f)+np.asarray(stop)*f
        row={'fraction':float(f),'translationMm':v.tolist(),'pairs':{}}
        for mk,a in moving.items():
            translated=a.translate(v)
            for fk,b in fixed.items():row['pairs'][mk+'--'+fk]=overlap(translated,b)
        rows.append(row)
    return rows

def motor_case(data,motor_key,frame):
    # Actual manufacturer movable horn3/center bolt9 rotate with output;
    # optional rear horn/cap/screw10..12 are absent in the current leg.
    import cadquery as cq
    source=R/'fastener-audit/sources/X330_3d.stp'
    shape=cq.importers.importStep(str(source)).val()
    require(len(shape.Solids())==15,'manufacturer CAD decomposition changed')
    row=next(p for p in data['parts'] if p['key']==motor_key)
    source_to_reference=np.array([[0,0,-1,-8],[-1,0,0,0],[0,1,0,0],[0,0,0,1]],float)
    transform=np.linalg.inv(frame)@np.array(row['sourceTransformWorld'])@source_to_reference
    pieces=[]
    for index,s in enumerate(shape.Solids()):
        if index in [3,9,10,11,12]:continue
        v,f=s.tessellate(.08)
        m=trimesh.Trimesh([[q.x,q.y,q.z] for q in v],f,process=True).apply_transform(transform)
        pieces.append(solid(m))
    return mf.Manifold.batch_boolean(pieces,mf.OpType.Add)

def sleeve_check(s,lower,old_ring):
    mesh=s['mesh'];r=np.linalg.norm(mesh.vertices[:,:2],axis=1)
    require(abs(r.max()-7.3)<.003 and abs(r.min()-5.2)<.003,'actual sleeve OD/ID not14.6/10.4')
    require(np.allclose(mesh.bounds[:,2],[-1.4,1.4],atol=.003),'actual sleeve width not2.8')
    require(overlap(s['solid'],lower)<1e-5,'new sleeve still interferes with actual post')
    require(overlap(old_ring,lower)>14,'old sleeve interference baseline missing')
    slide=translation_samples({'sleeve':s['solid']},{'lower':lower},[0,0,8],[0,0,0])
    require(max(v for row in slide for v in row['pairs'].values())<1e-5,'sleeve cannot slide onto actual boss')
    return {'outerDiameterMm':float(r.max()*2),'innerDiameterMm':float(r.min()*2),'widthMm':float(np.ptp(mesh.vertices[:,2])),'newBossOverlapMm3':overlap(s['solid'],lower),'slidePoses':len(slide),'scope':'Nominal clearance; physical printed tolerance and passive bearing play remain unverified.'}

def candidate_structure_check(inputs,native_meshes):
    out={}
    for side,s in inputs.items():
        t=s['frame'];p=s['parts'];prefix='' if side=='left' else 'right_'
        old=in_frame(native_meshes[prefix+'ankle'],t);lower=in_frame(native_meshes[prefix+'lower'],t)
        ring=in_frame(native_meshes[prefix+'smallring'],t)
        combined=p['base']['solid']+p['cheek']['solid']
        # Motor/output and foot interfaces are all deeper than local z−10.
        # This checks the actual solid subset, not an authored preservation flag.
        protected=slab(-100,-10)
        change=symmetric_difference_volume(combined^protected,old^protected)
        require(change<.005,'original deep motor/foot interface material changed '+side)
        bbox=np.array([np.min([native_meshes[k].bounds[0] for k in [prefix+'lower',prefix+'ankle',prefix+'foot','motor6' if side=='left' else 'motor1']],axis=0),np.max([native_meshes[k].bounds[1] for k in [prefix+'lower',prefix+'ankle',prefix+'foot','motor6' if side=='left' else 'motor1']],axis=0)])
        new_bounds=np.array([np.min([piece['worldMesh'].bounds[0] for piece in p.values()],axis=0),np.max([piece['worldMesh'].bounds[1] for piece in p.values()],axis=0)])
        growth=np.maximum(0,bbox[0]-new_bounds[0])+np.maximum(0,new_bounds[1]-bbox[1])
        require(overlap(p['base']['solid'],p['cheek']['solid'])<.005,'base and closed cheek overlap '+side)
        for a,b in [('base','sleeve'),('cheek','sleeve')]:require(overlap(p[a]['solid'],p[b]['solid'])<.005,'ring clamped/intersected by '+a+' '+side)
        foot=in_frame(native_meshes[prefix+'foot'],t)
        added=(combined-old)
        added_foot=overlap(added,foot)
        require(added_foot<.02,'new candidate material obstructs retained foot '+side+' '+str(added_foot)+' mm3')
        lower_stops=[];cap_stops=[]
        lm=native_meshes[prefix+'lower'].copy().apply_transform(np.linalg.inv(t))
        for angle in np.linspace(0,2*math.pi,32,endpoint=False):
            for mesh,radius,direction,stops in [(lm,5.6,[0,0,-1],lower_stops),(p['cheek']['mesh'],7.05,[0,0,1],cap_stops)]:
                origin=[radius*math.cos(angle),radius*math.sin(angle),0]
                hits,_,_=mesh.ray.intersects_location([origin],[direction],multiple_hits=True)
                require(len(hits)>0,'missing ring axial retaining shoulder '+side)
                closest=hits[np.argmin(np.linalg.norm(hits-np.array(origin),axis=1))]
                stops.append(float(closest[2]))
        lower_gap=-1.4-max(lower_stops);cap_gap=min(cap_stops)-1.4
        require(lower_gap>.25 and cap_gap>.08,'ring is clamped by lower/cap '+side)
        require(lower_gap+cap_gap<.45,'excess or absent ring axial capture '+side)
        out[side]={'sourceInterfaceSymmetricDifferenceMm3':change,'originalAnkleFootLinkEnvelopeMm':bbox.tolist(),'replacementPrintedEnvelopeMm':new_bounds.tolist(),'outsideEnvelopeGrowthMmByAxis':growth.tolist(),'partsConnected':3,'sleeve':sleeve_check(p['sleeve'],lower,ring),'ringAxialCapture':{'nativeRayCountPerSide':32,'lowerGapMm':lower_gap,'capGapMm':cap_gap,'totalNominalAxialEndplayMm':lower_gap+cap_gap,'physicalToleranceVerified':False}}
    return out

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--baseline-only',action='store_true');args=a.parse_args()
    if args.baseline_only:
        data,meshes,solids=native_parts();baseline=baseline_check(solids)
        print(json.dumps({'baseline':baseline,'fullSourceSha256':sha(G/'full-build-data.json'),'sourceXmlSha256':sha(XML)},indent=2))
        print('ANKLE_BASELINE_FAILURE_REPRODUCED')
    else:
        verify()
