"""Audit functional surfaces of all 89 MicroDuck print instances without altering geometry.

Outputs are geometry evidence and candidate rigid transforms, never print readiness.
Run with /tmp/microduck-current-check-venv/bin/python audit_surfaces.py.
"""
from pathlib import Path
import argparse, collections, hashlib, json, sys, zipfile, xml.etree.ElementTree as ET
import numpy as np
import trimesh
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
PRINTING = HERE.parents[1]
DESIGN = PRINTING.parent
ASSEMBLY = DESIGN.parent / 'assembly'
SIM = DESIGN.parents[1]
PREVIOUS = PRINTING / '09-REPRINT-READY-20260930'
sys.path.insert(0, str(PRINTING / '08-ORANGE-BOTTOM-AUDIT-20260930'))
from analyze_bottom import section_shape, matrix, N, PN
namespace = {'__file__': str(ASSEMBLY / 'prepare_geometry.py')}
exec((ASSEMBLY / 'prepare_geometry.py').read_text().split('rows=[]')[0], namespace)
inventory = {r['id']: r for r in json.loads((ASSEMBLY / 'community-print-inventory.json').read_text())['objects']}
refinement = {r['id']: r for r in json.loads((ASSEMBLY / 'source-surface-refinement.json').read_text())}
_, assembly_geoms = namespace['fk']()
fasteners = json.loads((DESIGN / 'assembly-fasteners.json').read_text())['connections']
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

# This catalogue identifies actual uses; "risk" is a check target, not a defect claim.
USES = {
 '3.obj': ('Lower head shell', ['cap rim and three screw pilots', 'jaw support seats', 'neck clearance'], 'Head cavity is open; check long support branches around neck and jaw pilots before closure.'),
 '4.obj': ('Moving jaw frame', ['rotating shaft and jaw pad mating surfaces', 'motor output screw seats'], 'Inside curved jaw may retain support fragments; preserve the moving gap.'),
 '7.obj': ('Left torso shell', ['hip case screw seats and shell seam', 'power support mating lip'], 'Remove only supports from vent/slot exits; flat bed contact has already been corrected.'),
 '8.obj': ('Right torso shell', ['hip case screw seats and shell seam', 'power support mating lip'], 'Keep supported vent and seam edges dimensionally intact.'),
 'b.obj': ('Hip bracket', ['four-hole output seats', 'opposed pitch/roll shaft seats'], 'Open bracket; inspect both output screw recesses, not just the broad bottom.'),
 'd.obj': ('Neck link A', ['output screw annuli', 'paired-axis support seats'], 'Short holes are accessible from both sides; horizontal hole roundness needs readback if rotated.'),
 'e.obj': ('Neck link B', ['output screw annuli', 'paired-axis support seats'], 'Short holes are accessible from both sides; horizontal hole roundness needs readback if rotated.'),
 'f.obj': ('Thigh reinforcing plate', ['case screw bearing annuli', 'flat thigh mating face'], 'Thin planar part: keep broad-plane orientation unless a functional defect is demonstrated.'),
 'g.obj': ('Thigh reinforcing plate', ['case screw bearing annuli', 'flat thigh mating face'], 'Thin planar part: keep broad-plane orientation unless a functional defect is demonstrated.'),
 'i.obj': ('Retaining strip', ['flat clamping face', 'pilot clearances'], 'Thin strip: avoid support in its small locating gaps.'),
 'j.obj': ('Neck U bracket', ['output screw seats', 'rear idler/cap access'], 'U-shaped interior can shelter support; inspect rear-center access before assembly.'),
 'k.obj': ('Lower-leg link', ['knee output screw annuli', 'ankle case fixation', 'integrated passive rear center'], 'Rear center pocket is a functional surface; do not mistake a locating peg for removable support.'),
 'l.obj': ('Lower-leg link', ['knee output screw annuli', 'ankle case fixation', 'integrated passive rear center'], 'Rear center pocket is a functional surface; do not mistake a locating peg for removable support.'),
 'm.obj': ('Torso base', ['hip-yaw motor fixation', '22 mm ring support', 'power-support locating features'], 'Inside corners and integrated pegs require support-access review.'),
 'n.obj': ('Yaw-to-roll link', ['yaw output seats', 'roll case screws', 'integrated rear retainer'], 'Compact perpendicular joint: verify support removal around both orthogonal axes.'),
 'o.obj': ('Yaw-to-roll link', ['yaw output seats', 'roll case screws', 'integrated rear retainer'], 'Compact perpendicular joint: verify support removal around both orthogonal axes.'),
 'p.obj': ('Fixed lip pad', ['jaw contact surface', 'shell attachment'], 'Preserve pad thickness and attachment; no extra screw or bonding across the moving gap.'),
 'q.obj': ('Moving lip pad', ['jaw contact surface', 'moving-pad attachment'], 'Preserve pad thickness and attachment; no extra screw or bonding across the moving gap.'),
 '111.obj': ('Left combined foot', ['ankle seating slot', 'single Ø1.6 blind pilot', 'ground-contact sole'], 'Slot is open from above. Blind pilot must remain open; underside traction is separate from mating acceptance.'),
 '222.obj': ('Right combined foot', ['ankle seating slot', 'single Ø1.6 blind pilot', 'ground-contact sole'], 'Slot is open from above. Blind pilot must remain open; underside traction is separate from mating acceptance.'),
 '333.obj': ('Eye trim', ['cosmetic shell rim'], 'Non-load-bearing; no rotation solely to reduce a cosmetic support count.'),
 'dfvdfb.obj': ('Passive roll support', ['case screw annuli', 'ring/passive support alignment'], 'Thin support: retain its locating faces and free ring axis.'),
 'ersgtbgertgestrg.obj': ('22 mm sliding ring', ['16 mm sliding bore', 'parallel end faces'], 'Open through bore. Ring ends can touch the bed; a support-filled bore would require a failed access check.'),
 'idle_horn.stl': ('Printed passive idler', ['sliding circumference', 'rear center bore'], 'Only two neck stations install these; the other prints are spares. Inspect the narrow center from both ends.'),
 'idle_cap.stl': ('Printed idler cap', ['rear screw bearing face', 'idler retention lip'], 'Only two neck stations install these; the other prints are spares. Preserve the retaining lip.'),
 'rgbn.obj': ('14.6 mm ankle sliding ring', ['9.64 mm sliding bore', 'parallel 3 mm end faces'], 'Open through bore; keep the outer edge circular and remove elephant-foot only if physically measured.'),
 'grbrgn.obj': ('Right ankle bracket', ['four countersunk output screw seats', '15 mm sliding pocket', 'single foot attachment clearance'], 'Two opposed flanges prevent putting both internal planar seats on the bed. Output recesses are support-sensitive.'),
 'thngthm.obj': ('Left ankle bracket', ['four countersunk output screw seats', '15 mm sliding pocket', 'single foot attachment clearance'], 'Two opposed flanges prevent putting both internal planar seats on the bed. Output recesses are support-sensitive.'),
 'dfbdfbbbbb1.obj': ('Head yaw/roll link', ['output screw seats', 'orthogonal roll/output alignment'], 'Perpendicular joint; inspect supported counterbores and ring seat for remaining support.'),
 'fgb.obj': ('Right thigh', ['two motor bays', 'integrated passive centers', 'reinforcing plate mating'], 'Deep motor bays may shelter tree branches. Check passive centers before enclosing motors.'),
 'gbgb.obj': ('Left thigh', ['two motor bays', 'integrated passive centers', 'reinforcing plate mating'], 'Deep motor bays may shelter tree branches. Check passive centers before enclosing motors.'),
 'ghmghmghmghm.obj': ('Face/Pi mounting panel', ['four Pi pilot bosses', 'shell rim', 'eye trim seating'], 'Pilots are blind; use the open head-side cavity for cleanup and never drill through them.'),
 'power-support-integrated-print.stl': ('Integrated power support', ['hip case screws', 'converter insert retention', 'cable exits'], 'Open battery/converter cavity has overhangs; support access must stay available before motor installation.'),
 'head-cap-usb-service-print.stl': ('Head cap', ['three shell pilot bosses', 'OpenRB and audio posts', 'USB service opening'], 'Large cavity and hanging posts: normal support is expected, but blind pilots and cable slots must not be sealed.'),
 'imu_clamp_holder_print.stl': ('IMU clamp', ['fixed torso rail jaws', 'board clamp pilots'], 'Clear supports through open rail jaws; preserve spring/jaw wall thickness.'),
 'imu_rear_cover_print.stl': ('IMU rear cover', ['four screw seats', 'flat closure rim'], 'Thin cover: retain broad-plane orientation and do not use longer cover-plus-alarm stack screws.'),
 'small-regulator-cover-print.stl': ('Retained small-regulator cover', ['flat closure plane', 'screw clearance holes'], 'Printed legacy cover is stock, not proof it is installed; preserve it without unnecessary reorientation.'),
 'motor-support-coaxial-print.stl': ('Coaxial jaw motor support', ['10.4 mm coaxial sliding seat', 'four shell attachment holes', 'jaw motor screw seats'], 'Clean the integral sliding seat without enlarging it. Keep supports accessible through the open bracket.'),
 'fuse-bank-print.stl': ('Fuse carrier', ['eleven axial fuse channels', 'four mounting posts', 'four tie paths'], 'Lower channels are only 6.5 mm high: tree support can become trapped. Native slice must inspect open-end extraction.'),
 'audio_carrier_print.stl': ('Audio carrier', ['two mounting posts', 'amp/speaker retention', '1.2 mm tie slots'], 'Narrow slots must remain open; support removal must not split carrier arms.'),
 'regulator-open-insert-print.stl': ('Converter insert', ['DFR1202 edge retention', 'tie paths', 'mount retention'], 'Open thermal side is required; inspect support removal at tie paths and retaining corners.'),
 'camera_pitch_foot.stl': ('Camera pitch foot', ['two cap screw seats', 'pitch hinge holes'], 'Horizontal hinge holes need bridge/roundness inspection; supported hinge annuli must seat washers.'),
 'camera_cradle.stl': ('Camera cradle', ['four PCB screw seats', 'pitch hinge', 'lens aperture'], 'Clean hinge and lens opening. Support must not remain under camera PCB standoffs.'),
}

def load_project(path):
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read('3D/3dmodel.model'))
        resources = {e.get('id'): e for e in root.find(N+'resources')}
        settings = ET.fromstring(z.read('Metadata/model_settings.config'))
        names = {e.get('id'): e.find("metadata[@key='name']").get('value') for e in settings.findall('object')}
        result = []
        for item in root.find(N+'build'):
            oid = item.get('objectid'); parts = []; components = []
            for comp in resources[oid].find(N+'components'):
                member = comp.get(PN+'path').lstrip('/')
                child = ET.fromstring(z.read(member))
                obj = next(e for e in child.find(N+'resources') if e.get('id') == comp.get('objectid'))
                me = obj.find(N+'mesh')
                vertices = np.array([[float(e.get(k)) for k in ('x','y','z')] for e in me.find(N+'vertices')])
                faces = np.array([[int(e.get(k)) for k in ('v1','v2','v3')] for e in me.find(N+'triangles')])
                local = trimesh.Trimesh(vertices, faces, process=True)
                transform = matrix(item.get('transform')) @ matrix(comp.get('transform'))
                parts.append(local.copy().apply_transform(transform))
                components.append((local, transform, member, hashlib.sha256(z.read(member)).hexdigest()))
            result.append(dict(object_id=oid, name=names[oid], mesh=trimesh.util.concatenate(parts), components=components,
                               build_transform=matrix(item.get('transform')).tolist()))
    return result

def ray_first(mesh, origin, direction):
    tri=mesh.triangles; e1=tri[:,1]-tri[:,0]; e2=tri[:,2]-tri[:,0]
    h=np.cross(direction,e2); det=np.einsum('ij,ij->i',e1,h)
    ok=np.abs(det)>1e-9; f=np.zeros_like(det); f[ok]=1/det[ok]
    s=origin-tri[:,0]; u=f*np.einsum('ij,ij->i',s,h); q=np.cross(s,e1)
    v=f*np.einsum('j,ij->i',direction,q); t=f*np.einsum('ij,ij->i',e2,q)
    ok &= (u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)&(t>1e-7)
    hits=np.flatnonzero(ok)
    if not len(hits): return None
    index=int(hits[np.argmin(t[hits])]); return origin+t[index]*direction, mesh.face_normals[index]

def source_info(name, local):
    if name.startswith('community-'):
        sid=int(name.split('-')[1].split('.')[0]); row=inventory[sid]
        raw=namespace['mesh']('3D/3dmodel.model',str(sid))
        r=np.array(row['original_plate_rotation']); t=local.bounds.mean(0)-r@raw.bounds.mean(0)
        # Bounds center is calculated after rotation, not by rotating a box center.
        rotated=raw.vertices@r.T; t=local.bounds.mean(0)-(rotated.min(0)+rotated.max(0))/2
        aligned=raw.vertices@r.T+t
        d=cKDTree(local.vertices).query(aligned)[0]
        return dict(source_id=sid, source_name=row['source_name'], family_key=row['source_sha256'], raw=raw,
                    raw_to_child=(r,t), alignment_vertex_max_mm=float(d.max()), source_file=ASSEMBLY/'print-parts'/name)
    candidates=list((ASSEMBLY/'print-parts/current').glob(name))+list(DESIGN.glob(name))
    if not candidates: raise RuntimeError('No owning STL found for '+name)
    source=candidates[0]; raw=trimesh.load(source,force='mesh')
    t=local.bounds.mean(0)-raw.bounds.mean(0); d=cKDTree(local.vertices).query(raw.vertices+t)[0]
    return dict(source_id=None,source_name=name,family_key=sha(source),raw=raw,raw_to_child=(np.eye(3),t),
                alignment_vertex_max_mm=float(d.max()),source_file=source)

def raw_seats(info):
    sid=info['source_id']
    if sid is None:return []
    row=inventory[sid]; ref=row.get('reference_mesh')
    if not ref:return []
    same={r['id'] for r in inventory.values() if r['source_sha256']==row['source_sha256']}
    # k/l were exported with tiny tessellation changes; the same reference fit supplies both.
    if row['source_name'] in ['k.obj','l.obj']:same|={30,32}
    seats=[]; raw=info['raw']; rr=refinement.get(sid)
    source_to_ref=np.eye(4);source_to_ref[:3,:3]=rr['rotation'] if rr else row['source_to_reference_rotation']
    source_to_ref[:3,3]=rr['translation'] if rr else row['source_to_reference_translation_mm']
    occurrences=[g for g in assembly_geoms if g['mesh']==ref]
    for connection in fasteners:
        if not (same & set(connection.get('source_ids',[]))) or 'world_center_mm' not in connection:continue
        world=np.array(connection['world_center_mm']); axis=np.array(connection['world_axis'])
        options=[]
        for g in occurrences:
            inv=np.linalg.inv(g['world']@source_to_ref); point=(inv@np.r_[world,1])[:3]; direction=inv[:3,:3]@axis
            # Head center must be at this part, not the identical mirrored occurrence.
            outside=np.maximum(raw.bounds[0]-point,0)+np.maximum(point-raw.bounds[1],0)
            options.append((float(np.linalg.norm(outside)),point,direction))
        if not options:continue
        dist,point,direction=min(options,key=lambda q:q[0])
        if dist>3:continue
        direction/=np.linalg.norm(direction)
        radius=1.6 if connection['spec'].startswith('M2 x') else 2.0
        basis=trimesh.geometry.align_vectors([0,0,1],direction)[:3,:3]
        samples=[]
        for angle in np.linspace(0,2*np.pi,8,endpoint=False):
            at=point+basis@np.array([radius*np.cos(angle),radius*np.sin(angle),0])
            hit=ray_first(raw,at+direction*.35,-direction)
            if hit is not None and abs(np.dot(hit[0]-at,direction))<.15:
                samples.append((hit[0],hit[1]))
        seats.append(dict(id=connection['id'],spec=connection['spec'],category=connection['category'],servo_ids=connection['servo_ids'],
                          source_point_mm=point.tolist(),source_outward_axis=direction.tolist(),samples=samples,
                          captured_samples=len(samples),sampled_annular_radius_mm=radius))
    return seats

def sliding_features(info):
    """Exact native rays on named sliding bores and ankle ring pocket floor.

    These are additional actual mating surfaces, not inferred from total downward area.
    A negative normal-dot-ray distinguishes cavity walls from exterior silhouettes.
    """
    name=info['source_name'];raw=info['raw'];features=[]
    if name in ['ersgtbgertgestrg.obj','rgbn.obj','idle_horn.stl','idle_cap.stl']:
        axis_index=int(np.argmin(raw.extents));axis=np.eye(3)[axis_index];center=raw.bounds.mean(0)
        other=[i for i in range(3) if i!=axis_index];samples=[]
        for fraction in [.25,.5,.75]:
            at=center.copy();at[axis_index]=raw.bounds[0,axis_index]+fraction*raw.extents[axis_index]
            for angle in np.linspace(0,2*np.pi,16,endpoint=False):
                direction=np.zeros(3);direction[other]=[np.cos(angle),np.sin(angle)]
                hit=ray_first(raw,at,direction)
                if hit is not None and np.dot(hit[1],direction)<-.5:samples.append(hit)
        features.append(dict(id='native-sliding-bore',spec='Actual printed cylindrical mating wall',category='sliding_bore',
                             servo_ids=[],source_point_mm=center.tolist(),source_outward_axis=axis.tolist(),samples=samples,
                             captured_samples=len(samples),sampled_annular_radius_mm=None))
    if name in ['thngthm.obj','grbrgn.obj']:
        sign=1 if name=='thngthm.obj' else -1
        # Exact original mesh circular feature center, retained source coordinate system.
        center=np.array([-3.5896687,3.5512071,16*sign]);axis=np.array([0,0,sign]);wall=[];floor=[]
        for z in [15.4,16.1,17.0]:
            at=center.copy();at[2]=z*sign
            for angle in np.linspace(0,2*np.pi,16,endpoint=False):
                d=np.array([np.cos(angle),np.sin(angle),0]);hit=ray_first(raw,at,d)
                if hit is not None and np.dot(hit[1],d)<-.5:wall.append(hit)
        # Native pocket is through-open to radius ~7.0; the narrow shoulder that
        # actually locates the 14.6 mm ring lies at r7.1..7.3, not r5.5..6.5.
        for radius in [7.1,7.3]:
            for angle in np.linspace(0,2*np.pi,16,endpoint=False):
                at=center+np.array([radius*np.cos(angle),radius*np.sin(angle),0]);hit=ray_first(raw,at,axis)
                if hit is not None and np.dot(hit[1],axis)<-.5 and np.linalg.norm(hit[0]-at)<3:floor.append(hit)
        for label,samples in [('ankle-15mm-pocket-wall',wall),('ankle-ring-axial-seating-floor',floor)]:
            features.append(dict(id=label,spec='Actual mating surface for 14.6 x 3 mm ring',category='sliding_pocket',
                                 servo_ids=[6] if sign==1 else [1],source_point_mm=center.tolist(),source_outward_axis=axis.tolist(),samples=samples,
                                 captured_samples=len(samples),sampled_annular_radius_mm=None))
    return features

def community_mount_features(info):
    """Community head/Pi mounts and the newly checked foot pilot, omitted by joint-only source IDs."""
    name=info['source_name'];raw=info['raw'];out=[]
    if name in ['111.obj','222.obj']:
        samples=[];center=np.array([10.5,5.453,0.]);axis=np.array([0.,1.,0.])
        for angle in np.linspace(0,2*np.pi,8,endpoint=False):
            at=center+np.array([1.2*np.cos(angle),.4,1.2*np.sin(angle)]);h=ray_first(raw,at,-axis)
            if h is not None and abs(h[0][1]-center[1])<.1:samples.append(h)
        out.append(dict(id='foot-ankle-blind-pilot-mouth',spec='Ø1.6 x 5 mm blind pilot; paired ankle clearance',category='blind_pilot_mouth',
                        servo_ids=[],source_point_mm=center.tolist(),source_outward_axis=axis.tolist(),samples=samples,
                        captured_samples=len(samples),sampled_annular_radius_mm=1.2))
    if name not in ['3.obj','ghmghmghmghm.obj']:return out
    selected=['pi'] if name=='ghmghmghmghm.obj' else ['head_cap_closure','motor_support_frame']
    row=inventory[info['source_id']];rr=refinement.get(info['source_id']);T=np.eye(4)
    T[:3,:3]=rr['rotation'] if rr else row['source_to_reference_rotation'];T[:3,3]=rr['translation'] if rr else row['source_to_reference_translation_mm']
    geom=next(g for g in assembly_geoms if g['mesh']==row['reference_mesh'])
    body_to_raw=np.linalg.inv(geom['local']@T)
    for c in fasteners:
        if c['id'] not in selected:continue
        axis=body_to_raw[:3,:3]@np.array(c['axis'],float);axis/=np.linalg.norm(axis)
        for index,point in enumerate(c['hole_centers_mm']):
            point=(body_to_raw@np.r_[point,1])[:3];basis=trimesh.geometry.align_vectors([0,0,1],axis)[:3,:3];samples=[]
            for angle in np.linspace(0,2*np.pi,8,endpoint=False):
                at=point+basis@np.array([1.6*np.cos(angle),1.6*np.sin(angle),0]);options=[]
                for sign in [1,-1]:
                    h=ray_first(raw,at+sign*axis*25,-sign*axis)
                    if h is not None and abs(np.dot(h[0]-at,axis))<20:options.append(h)
                if options:samples.append(min(options,key=lambda h:abs(np.dot(h[0]-at,axis))))
            out.append(dict(id=c['id']+'-community-interface-'+str(index),spec=c['spec'],category='electronics_printed_mount',servo_ids=[],
                            source_point_mm=point.tolist(),source_outward_axis=axis.tolist(),samples=samples,captured_samples=len(samples),
                            sampled_annular_radius_mm=1.6,interface_location_method='Nearest actual printed surface on documented body-frame mounting axis'))
    return out

def custom_features(info):
    """Trace electronics/shell mounting axes against their real assembly meshes.

    Electronics schedules specify board through-hole centers rather than printed
    bearing planes. Rays locate the printed interface along each documented axis.
    """
    if info['source_id'] is not None:return []
    old=SIM/'hardware-design-20260912/whole-robot-20260912'
    head=old/'electrical/head-layout/final'
    catalogue={
      'head-cap-usb-service-print.stl':(DESIGN/'head-cap-usb-service-body.stl','jaw_soft',['openrb','audio_carrier','camera_foot','head_cap_closure']),
      'audio_carrier_print.stl':(head/'audio_carrier_assembly.stl','jaw_soft',['audio_carrier']),
      'camera_cradle.stl':(head/'camera_cradle_assembly.stl','jaw_soft',['camera_pcb_10','camera_hinge']),
      'camera_pitch_foot.stl':(head/'camera_pitch_foot_assembly.stl','jaw_soft',['camera_foot','camera_hinge']),
      'fuse-bank-print.stl':(ASSEMBLY/'service-mounts/fuse-bank-body.stl','trunk_base',['fuse_carrier']),
      'imu_clamp_holder_print.stl':(old/'assembly/trunk-imu/imu_clamp_holder_body.stl','trunk_base',['imu_clamp']),
      'imu_rear_cover_print.stl':(old/'assembly/trunk-imu/imu_rear_cover_body.stl','trunk_base',['imu_rear_cover']),
      'motor-support-coaxial-print.stl':(ASSEMBLY/'mouth-support/motor-support-coaxial-assembly.stl','jaw_soft',['motor_support_frame']),
    }
    if info['source_name'] not in catalogue:return []
    bodyfile,frame,ids=catalogue[info['source_name']]
    body=trimesh.load(bodyfile,force='mesh');native=info['raw'];options=[]
    tree=cKDTree(native.vertices)
    for R in namespace['rot']:
        v=body.vertices@R.T;t=native.bounds.mean(0)-(v.min(0)+v.max(0))/2;d=tree.query(v+t)[0]
        options.append((float(np.percentile(d,95)),float(d.max()),R,t))
    score,maxdist,R,t=min(options,key=lambda q:q[0])
    if score>.025:raise RuntimeError('Assembly-to-print rigid fit failed: '+str(bodyfile)+' '+str(score))
    info['custom_assembly_fit']=dict(file=str(bodyfile),sha256=sha(bodyfile),surface_vertex_p95_mm=score,vertex_max_mm=maxdist,
                                      assembly_to_print_rotation=R.tolist(),assembly_to_print_translation_mm=t.tolist())
    features=[]
    for c in fasteners:
        if c['id'] not in ids:continue
        axis=np.array(c['axis'],float);axis/=np.linalg.norm(axis)
        for index,center in enumerate(c['hole_centers_mm']):
            center=np.array(center,float);samples=[]
            diameter=3 if c['spec'].startswith('M3') else 2.5 if c['spec'].startswith('M2.5') else 2
            radius=diameter/2+.3;basis=trimesh.geometry.align_vectors([0,0,1],axis)[:3,:3]
            for angle in np.linspace(0,2*np.pi,8,endpoint=False):
                at=center+basis@np.array([radius*np.cos(angle),radius*np.sin(angle),0])
                candidates=[]
                for sign in [1,-1]:
                    h=ray_first(body,at+sign*axis*35,-sign*axis)
                    if h is not None and abs(np.dot(h[0]-at,axis))<30:candidates.append(h)
                if candidates:
                    h=min(candidates,key=lambda h:abs(np.dot(h[0]-at,axis)))
                    samples.append((R@h[0]+t,R@h[1]))
            features.append(dict(id=c['id']+'-printed-interface-'+str(index),spec=c['spec'],category='electronics_printed_mount',
                                 servo_ids=[],source_point_mm=(R@center+t).tolist(),source_outward_axis=(R@axis).tolist(),
                                 samples=samples,captured_samples=len(samples),sampled_annular_radius_mm=radius,
                                 interface_location_method='Actual nearest printed interface on documented mounting axis; not a board screw-head plane'))
    if info['source_name']=='motor-support-coaxial-print.stl':
        samples=[];axis=np.array([0.,1.,0.]);center=np.array([3.,-38.35,-18.])
        for y in [-39.1,-38.35,-37.4]:
            for angle in np.linspace(0,2*np.pi,16,endpoint=False):
                d=np.array([np.cos(angle),0,np.sin(angle)]);at=np.array([3.,y,-18.]);h=ray_first(body,at,d)
                if h is not None and np.dot(h[1],d)<-.5 and np.linalg.norm(h[0]-at)<5.5:
                    samples.append((R@h[0]+t,R@h[1]))
        features.append(dict(id='jaw-10.4mm-coaxial-sliding-bore',spec='Actual 10.4 mm sliding bearing wall',category='sliding_bore',
                             servo_ids=[15],source_point_mm=(R@center+t).tolist(),source_outward_axis=(R@axis).tolist(),
                             samples=samples,captured_samples=len(samples),sampled_annular_radius_mm=None))
    if info['source_name']=='fuse-bank-print.stl':
        layout=json.loads((ASSEMBLY/'service-mounts/design.json').read_text());access=[]
        for fuse in layout['fuses']:
            center=np.array(fuse['center_mm'],float);samples=[]
            for xoffset in [-8,0,8]:
                at=center+np.array([xoffset,0,0])
                for d in [np.array(v,float) for v in [[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]]]:
                    h=ray_first(body,at,d)
                    if h is not None and np.dot(h[1],d)<-.5 and np.linalg.norm(h[0]-at)<4:
                        samples.append((R@h[0]+t,R@h[1]))
            for sign in [-1,1]:
                h=ray_first(body,center,np.array([sign,0,0],float))
                access.append(dict(fuse_id=fuse['id'],direction=sign,clear_to_envelope_end_12mm=h is None or np.linalg.norm(h[0]-center)>12,
                                   first_solid_distance_mm=None if h is None else float(np.linalg.norm(h[0]-center))))
            features.append(dict(id='fuse-channel-'+str(fuse['id'])+'-inner-walls',spec='Actual 24 x 5 x 5 mm retained envelope channel',
                                 category='open_channel_inner_surface',servo_ids=[],source_point_mm=(R@center+t).tolist(),
                                 source_outward_axis=(R@np.array([1,0,0])).tolist(),samples=samples,captured_samples=len(samples),
                                 sampled_annular_radius_mm=None,axial_access=[r for r in access if r['fuse_id']==fuse['id']]))
        info['channel_access']=dict(method='Exact native rays from each fuse centre along both X directions; finite 12 mm envelope end',
                                   all_22_paths_open=all(p['clear_to_envelope_end_12mm'] for p in access),paths=access,
                                   limitation='Open centreline is a necessary extraction route, not proof a branched slicer support can be extracted intact.')
    return features

def measure(mesh, features):
    floor=mesh.bounds[0,2]; normal=mesh.face_normals; area=mesh.area_faces
    over=(normal[:,2]<-np.cos(np.pi/4))&(mesh.triangles[:,:,2].max(1)>floor+.4)
    contact=section_shape(mesh,floor+.1)
    results=[]
    for feature in features:
        points=np.array(feature['points']); normals=np.array(feature['normals'])
        if len(points):
            risk=(normals[:,2]<-.70710678)&(points[:,2]>floor+.4)
            height=points[:,2]-floor
            results.append({k:v for k,v in feature.items() if k not in ['points','normals']}|dict(
                support_exposed_samples=int(risk.sum()),valid_samples=len(points),support_exposed_fraction=float(risk.mean()),
                bed_height_range_mm=[float(height.min()),float(height.max())],
                axis_to_vertical_degrees=float(np.degrees(np.arccos(np.clip(abs(np.array(feature['axis'])[2]),0,1))))) )
        else:results.append({k:v for k,v in feature.items() if k not in ['points','normals']}|dict(valid_samples=0,requires_native_feature_review=True))
    return dict(bounds_mm=mesh.bounds.tolist(),height_mm=float(mesh.extents[2]),volume_mm3=float(abs(mesh.volume)),
                first_layer_01_section_mm2=float(contact.area),first_layer_02_section_mm2=float(section_shape(mesh,floor+.2).area),
                suspended_downward_45_surface_mm2=float(area[over].sum()),functional_seats=results,
                support_exposed_seat_count=sum(r.get('support_exposed_samples',0)>0 for r in results),
                captured_seat_count=sum(r.get('valid_samples',0)>0 for r in results),
                unsupported_sampling_count=sum(r.get('valid_samples',0)==0 for r in results))

def transformed_features(features,T):
    out=[]
    for f in features:
        q=dict(f);q['points']=(np.array(f['points'])@T[:3,:3].T+T[:3,3]).tolist() if len(f['points']) else []
        q['normals']=(np.array(f['normals'])@T[:3,:3].T).tolist() if len(f['normals']) else []
        q['axis']=(T[:3,:3]@np.array(f['axis'])).tolist();out.append(q)
    return out

def alternatives(mesh,features,baseline):
    candidates=[]; directions=[]
    for inds in mesh.facets:
        area=mesh.area_faces[inds].sum()
        if area<20:continue
        normal=np.average(mesh.face_normals[inds],axis=0,weights=mesh.area_faces[inds]);normal/=np.linalg.norm(normal)
        if any(np.linalg.norm(normal-n)<.002 for n in directions):continue
        directions.append(normal)
        T=trimesh.geometry.align_vectors(normal,[0,0,-1]);center=mesh.bounds.mean(0);T[:3,3]=center-T[:3,:3]@center
        q=mesh.copy().apply_transform(T);T[2,3]-=q.bounds[0,2];q=mesh.copy().apply_transform(T)
        if q.triangles[inds].reshape(-1,3)[:,2].max()>.05:continue
        contact=section_shape(q,.1).area
        if contact<30:continue
        metrics=measure(q,transformed_features(features,T))
        improvement=baseline['suspended_downward_45_surface_mm2']-metrics['suspended_downward_45_surface_mm2']
        seat_improvement=baseline['support_exposed_seat_count']-metrics['support_exposed_seat_count']
        if improvement<max(20,baseline['suspended_downward_45_surface_mm2']*.1) and seat_improvement<=0:continue
        original=baseline['first_layer_01_section_mm2']
        penalties=[]
        if contact<original*.6:penalties.append('Smaller bed contact: verify native brim and adhesion footprint.')
        if any(r.get('axis_to_vertical_degrees',0)>60 for r in metrics['functional_seats']):penalties.append('Some fastener axes become horizontal: compare bridge sag and circular clearance.')
        if metrics['support_exposed_seat_count']:penalties.append('Some sampled functional seats still require supported-surface acceptance.')
        if baseline['unsupported_sampling_count']:penalties.append('Unsampled features remain subject to native support/access inspection.')
        penalties.append('Layer directions change: verify shaft, retaining lip and clamped wall strength; geometry preserves thickness but does not prove anisotropic print strength.')
        candidates.append(dict(delta4x4=T.tolist(),selected_contact_normal_current=normal.tolist(),selected_facet_area_mm2=float(area),
                               metrics=metrics,tradeoffs=penalties,native_slice_required=True,physical_fit_unverified=True))
    # Functional seats outrank cosmetic/global support area; do not lower a functional seat count by hiding unsampled features.
    candidates.sort(key=lambda c:(c['metrics']['support_exposed_seat_count'],c['metrics']['suspended_downward_45_surface_mm2']))
    return candidates[:3]

def run():
    handoff=json.loads((PREVIOUS/'handoff-index.json').read_text())['primary_files']
    instances={(r['group'],r['object_id']):r for r in json.loads((PREVIOUS/'orientation-audit.json').read_text())['parts']}
    source_hashes={str(p):sha(p) for p in [Path(__file__),PREVIOUS/'handoff-index.json',PREVIOUS/'orientation-audit.json',
                    DESIGN/'assembly-fasteners.json',ASSEMBLY/'community-print-inventory.json',ASSEMBLY/'source-surface-refinement.json',
                    ASSEMBLY/'prepare_geometry.py',namespace['SOURCE'],namespace['XML'],PRINTING/'WORKFLOW.md']}
    records=[]; families={}; cache={}
    for job in handoff:
        path=Path(job['project']);source_hashes[str(path)]=sha(path)
        for item in load_project(path):
            local,world,member,member_hash=item['components'][0]
            info=source_info(item['name'],local); source_hashes[str(info['source_file'])]=sha(info['source_file'])
            use=USES[info['source_name']]
            key=info['family_key']; families.setdefault(key,dict(title=use[0],source_names=set(),instances=[]))
            family=families[key];family['source_names'].add(info['source_name'])
            if key not in cache:cache[key]=raw_seats(info)+sliding_features(info)+community_mount_features(info)+custom_features(info)
            if 'custom_assembly_fit' in info:source_hashes[info['custom_assembly_fit']['file']]=info['custom_assembly_fit']['sha256']
            raw_to_child=np.eye(4);raw_to_child[:3,:3],raw_to_child[:3,3]=info['raw_to_child'];raw_to_world=world@raw_to_child
            seats=[]
            for seat in cache[key]:
                p=np.array([h[0] for h in seat['samples']]);n=np.array([h[1] for h in seat['samples']]);R=raw_to_world[:3,:3]
                seats.append({k:v for k,v in seat.items() if k!='samples'}|dict(points=(p@R.T+raw_to_world[:3,3]).tolist() if len(p) else [],
                            normals=(n@R.T).tolist() if len(n) else [],axis=(R@np.array(seat['source_outward_axis'])).tolist()))
            baseline=measure(item['mesh'],seats)
            index=instances[(job['group'],item['object_id'])]['manifest_instance_index']
            is_ankle=info['source_name'] in ['grbrgn.obj','thngthm.obj']
            exposed=baseline['support_exposed_seat_count']
            native_focus=exposed>0 or info['source_name'] in ['fuse-bank-print.stl','motor-support-coaxial-print.stl', 'head-cap-usb-service-print.stl','camera_cradle.stl','camera_pitch_foot.stl','fgb.obj','gbgb.obj']
            # All parts are inspected. Only evidenced affected seats or known traps generate orientation comparisons.
            alts=alternatives(item['mesh'],seats,baseline) if (is_ankle or exposed>0) else []
            record=dict(group=job['group'],printer=job['printer'],project=str(path),project_sha256=source_hashes[str(path)],
                        object_id=item['object_id'],manifest_instance_index=index,name=item['name'],source_name=info['source_name'],
                        source_id=info['source_id'],family_key=key,source_stl=str(info['source_file']),source_sha256=source_hashes[str(info['source_file'])],
                        source_geometry_member=member,source_geometry_member_sha256=member_hash,source_alignment_vertex_max_mm=info['alignment_vertex_max_mm'],
                        custom_assembly_fit=info.get('custom_assembly_fit'),
                        channel_access=info.get('channel_access'),
                        build_transform=item['build_transform'],raw_source_to_bed4x4=raw_to_world.tolist(),functional_surfaces=use[1],
                        support_access_check=use[2],current=baseline,alternatives=alts,
                        critical_surface_probes_bed_mm=seats,
                        decision='native-functional-surface-comparison-required' if native_focus else 'retain-current-orientation',
                        confirmed_physical_issue=info['source_name']=='thngthm.obj',
                        physical_issue_scope='User photo establishes the supported four-counterbore failure mechanism. Current source66 exposes these seats; source64 is evaluated independently because its opposite-end-down orientation keeps its four seats upward.' if is_ankle else None,
                        apply_without_native_acceptance=False,
                        acceptance_required=['Native toolpath support-contact coverage at listed functional surfaces', 'First-layer model versus support inspection',
                                             'Accessible support extraction through real open ends; no buried branches', 'Screw-seat, sliding bore and hole fit readback'])
            records.append(record);family['instances'].append(index)
            print(index,item['name'],'seat',exposed,'alts',len(alts),record['decision'],flush=True)
    for f in families.values():f['source_names']=sorted(f['source_names'])
    coverage=dict(expected=89,actual=len(records),unique_manifest_indices=len({r['manifest_instance_index'] for r in records}),
                  unique_geometry_families=len(families),all_functional_roles_annotated=all(r['functional_surfaces'] for r in records))
    report=dict(problem_ids=['P5','P6'],verified_date='2026-10-06',coverage=coverage,source_hashes=source_hashes,
                method='Exact final native 3MF transformed meshes; source-hash family dedup with per-instance orientation; source-world screw head annuli sampled by exact ray/triangle intersection; >45-degree suspended surface and native geometry first-layer sections; bounded viable facet rotations.',
                interpretation='Normal/area is a support-demand proxy, not proof a slicer actually supported a region or a physical quality guarantee. Head annuli are sampled; sliding bores, seams, blind pilots and access traps remain explicitly named native/physical checks. Preserve all geometry and all source instances.',
                old_ankle_surface_failure_reproduced=all(
                    sum(f.get('support_exposed_samples',0) for f in r['current']['functional_seats'] if f['category']=='horn')>=32
                    for r in records if r['confirmed_physical_issue']),
                candidate_scope='Up to three rigid rotations per affected instance; no geometry removal, new supports, spacing, profile changes or slice acceptance performed here.',
                families=families,instances=records)
    (HERE/'surface-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    focused=[]
    for r in records:
        if r['decision']=='native-functional-surface-comparison-required':
            focused.append({k:r[k] for k in ['group','object_id','manifest_instance_index','name','source_name','family_key',
                                           'current','alternatives','critical_surface_probes_bed_mm','support_access_check']})
    (HERE/'native-review-queue.json').write_text(json.dumps(focused,indent=2)+'\n')
    return report

def verify(report):
    errors=[]
    cov=report['coverage']
    if cov['actual']!=89 or cov['unique_manifest_indices']!=89:errors.append('Incomplete 89-instance coverage')
    if not cov['all_functional_roles_annotated']:errors.append('Missing functional role')
    if any(r['source_alignment_vertex_max_mm']>.025 for r in report['instances']):errors.append('Source-to-native mesh alignment exceeded 0.025 mm')
    for r in report['instances']:
        for candidate in r['alternatives']:
            R=np.array(candidate['delta4x4'])[:3,:3]
            if not np.allclose(R.T@R,np.eye(3),atol=1e-8) or np.linalg.det(R)<.99999:errors.append('Non-rigid candidate')
            if abs(candidate['metrics']['volume_mm3']-r['current']['volume_mm3'])>.001:errors.append('Candidate changed volume')
    if not report['old_ankle_surface_failure_reproduced']:errors.append('Old ankle regression no longer fails')
    for p,expected in report['source_hashes'].items():
        if sha(p)!=expected:errors.append('Source changed: '+p)
    result=dict(passed=not errors,errors=errors,scope='Geometry audit integrity, not surface-quality or print readiness',
                old_ankle_quality_accepted=False,new_print_quality_accepted=False,coverage=cov,
                regression='The old ankle file remains rejected for user-observed supported output surface even though first-layer contact passes; no candidate can pass physical quality without native supported-seat/contact and fit evidence.')
    (HERE/'geometry-regression.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
    report=json.loads((HERE/'surface-audit.json').read_text()) if args.verify_only else run()
    result=verify(report);print(json.dumps(result,indent=2));sys.exit(0 if result['passed'] else 1)
