"""Export real community print geometry and the current left-leg screw schedule."""
from pathlib import Path
import sys, json, base64, hashlib, re
import numpy as np
import trimesh
import cadquery as cq

OUT = Path(__file__).resolve().parent
SIM = OUT.parents[2]
ASSEMBLY = SIM / 'build-pack-20260913/assembly'
sys.path.insert(0, str(SIM / 'hardware-design-20260912/whole-robot-20260912/assembly'))
from assembly_fk import fk, raw, XML

ns = {'__file__': str(ASSEMBLY / 'prepare_geometry.py')}
exec((ASSEMBLY / 'prepare_geometry.py').read_text().split('rows=[]')[0], ns)
inventory = {r['id']: r for r in json.loads((ASSEMBLY / 'community-print-inventory.json').read_text())['objects']}
refined = {r['id']: r for r in json.loads((ASSEMBLY / 'source-surface-refinement.json').read_text())}
gs = fk()[1]
colors = {'Orange': '#ff8000', 'Black': '#202020', 'Yellow': '#ffff00', 'Motor': '#40454b'}
items = []
motor_step=OUT.parent/'fastener-audit/sources/X330_3d.stp'
native_shape=cq.importers.importStep(str(motor_step)).val()
motor_solids=[]
for i,solid in enumerate(native_shape.Solids()):
    if i in (10,11,12):
        continue  # Optional rear idler horn, cap and retaining screw are not fitted to the legs.
    v,f=solid.tessellate(.08)
    motor_solids.append(trimesh.Trimesh([[q.x,q.y,q.z] for q in v],f,process=False))
native_motor=trimesh.util.concatenate(motor_solids).apply_transform(np.array([[0,0,-1,-8],[-1,0,0,0],[0,1,0,0],[0,0,0,1]],float))

def gfind(body, mesh, index=None):
    return next(g for g in gs if g['body'] == body and g['mesh'] == mesh and (index is None or g['index'] == index))

def add(key, name, color, body, ref, oid=None, stage=0, desc='', aliases='', index=None, transform=None, world_override=None):
    g = gfind(body, ref, index)
    if oid is None:
        m = native_motor.copy().apply_transform(g['world']) if ref=='xl330' else raw(ref).apply_transform(g['world'])
    else:
        m = ns['mesh']('3D/3dmodel.model', str(oid))
        if transform is None:
            r = refined.get(oid, inventory[oid])
            T = np.eye(4)
            T[:3, :3] = r.get('rotation', r.get('source_to_reference_rotation'))
            T[:3, 3] = r.get('translation', r.get('source_to_reference_translation_mm'))
        else:
            T = np.array(transform)
        m.apply_transform(world_override if world_override is not None else g['world'] @ T)
    pos = np.array(m.vertices, dtype='<f4')
    faces = np.array(m.faces, dtype='<u4')
    items.append(dict(key=key, name=name, color=colors[color], colorName=color, sourceId=oid,
                      sourceName=inventory[oid]['source_name'] if oid else 'XL330-M288-T',
                      body=body, referenceMesh=ref, index=g['index'], stage=stage, description=desc,
                      aliases=aliases, bounds=m.bounds.tolist(), center=m.bounds.mean(0).tolist(),
                      dimensions=np.sort(m.extents)[::-1].round(1).tolist(),
                      positionB64=base64.b64encode(pos.tobytes()).decode(),
                      indexB64=base64.b64encode(faces.tobytes()).decode(),
                      triangles=len(m.faces), sourceTransformWorld=(world_override if world_override is not None else g['world'] @ T).tolist() if oid else g['world'].tolist()))

add('thigh', 'Left thigh body', 'Orange', 'upper_leg_left', 'upper_leg_left', 74, 1,
    'Large open frame with two motor seats. The wide faces belong to the hip-pitch and knee motors. This is the LEFT version.', '74 · gbgb.obj')
add('plate', 'Thigh reinforcing plate', 'Black', 'upper_leg_left', 'upper_leg_rigidity_plate', 22, 1,
    'Very thin, flat, roughly triangular plate; only 1 mm thick. It spans the stationary case corners of both thigh motors.', '20 or 22 · f/g.obj; identical copies')
add('lower', 'Lower-leg link', 'Black', 'leg', 'leg', 30, 2,
    'Long narrow stepped link, about 58 mm long, with joint openings at both ends. One link per leg.', '30 or 32 · k/l.obj; equivalent shape')
add('ankle', 'Left ankle bracket', 'Orange', 'ankle_left', 'ankle_left', 66, 2,
    'Compact curved fork with a round motor-output opening and lower foot-pivot seats. Use the LEFT part, not the opposite ankle.', '66 · thngthm.obj')
footT = [[0,0,-1,49.9974714],[-1,0,0,15.0012071],[0,1,0,-21.7949115],[0,0,0,1]]
add('foot', 'Left foot', 'Yellow', 'ankle_left', 'foot_left', 44, 2,
    'One combined broad foot print with a raised pivot feature. The foot is a single part; do not look for a separate sole.', '44 · 111.obj; 46/222.obj is the opposite foot', transform=footT)
add('hip', 'Hip bracket', 'Orange', 'hip_l', 'hip_l', 14, 3,
    'Short bent bridge connecting the two perpendicular output faces: hip roll ID9 and hip pitch ID8.', '14 or 60 · b.obj; identical copies')
add('yaw', 'Yaw-to-roll link', 'Black', 'yaw2roll', 'yaw2roll', 36, 3,
    'Short angled block with perpendicular motor interfaces and an integrated rear retainer.', '36 or 38 · n/o.obj; identical copies')
add('passive', 'Roll support plate', 'Black', 'yaw2roll', 'bearing_roll', 50, 3,
    'Tall, narrow plate, about 40 mm long and 3 mm thick. It closes the opposite side of the hip-roll motor case.', '50 or 51 · dfvdfb.obj; identical copies')
for key,body,index,sid,stage in [('ring7','upper_leg_left',3,7,1),('ring8','hip_l',0,8,3),('ring9','yaw2roll',2,9,3)]:
    add(key, f'22 mm sliding ring · ID{sid}', 'Black', body, 'seeed_bearing__configuration__22x16x4', 53, stage,
        'Black printed annular support: 22 mm outside diameter, 4 mm wide. Three are used on this detached leg. Keep the molded sliding features; no extra metal bearing is required.', '53 and copied instances · Ø22 × 4 mm', index=index)
ankle_transform=np.array(next(p for p in items if p['key']=='ankle')['sourceTransformWorld'])
smallring_local=np.eye(4);smallring_local[:3,3]=[-3.5896687,3.5512071,16.1074]
add('smallring', '14.6 mm ankle ring', 'Black', 'ankle_left', 'seeed_bearing__configuration_default', 62, 2,
    'Single black printed sleeve: 14.6 mm outside diameter, about 9.65 mm bore, 3 mm wide. Its inner fit on the lower-link Ø10 boss is tight in CAD; its outside has nominal clearance inside the orange ankle Ø15 pocket. Relative motion must occur at the outer interface if the sleeve stays with the link.', '62 or 68 · rgbn.obj', world_override=ankle_transform@smallring_local)
for sid,body,index,stage,role in [(6,'leg',2,2,'ankle pitch'),(7,'upper_leg_left',1,1,'knee pitch'),(8,'upper_leg_left',4,1,'hip pitch'),(9,'yaw2roll',1,3,'hip roll'),(10,'trunk_base',4,4,'hip yaw')]:
    add(f'motor{sid}',f'XL330 · ID{sid} · {role}','Motor',body,'xl330',stage=stage,index=index,
        desc='Black rectangular XL330-M288-T motor from the OMX-AI kit. The output face rotates; the opposite case and rear center are different attachments. ID is a planned MicroDuck label, not a verified setting on your motor.',aliases=f'XL330-M288-T · planned ID{sid}')

schedule = json.loads((OUT.parent / 'assembly-fasteners.json').read_text())
screws = [c for c in schedule['connections'] if c.get('servo_ids') and 6 <= c['servo_ids'][0] <= 10 and not (c['servo_ids']==[10] and c['category']=='case')]
for c in screws:
    sid = c['servo_ids'][0]
    c['stage'] = 1 if sid in [7,8] and c['category'] != 'horn' else 2 if sid in [6,7] else 3 if sid in [8,9] else 4
totals={}
for c in screws: totals[c['spec']] = totals.get(c['spec'],0)+c['quantity']
assert len(screws)==34
# A print-to-print connection omitted from the legacy MOTOR-only schedule.
point=(ankle_transform@np.array([13.91,-4.57,.11,1]))[:3]
axis=ankle_transform[:3,:3]@np.array([0,1,0])  # Outward normal; insertion is -axis.
screws.append(dict(id='left-foot-retainer',component='Left ankle bracket to combined left foot',servo_ids=[6],
                  category='print_retainer',quantity=1,spec='M2 x 6 TAP',length_mm=6,stage=2,
                  world_center_mm=point.tolist(),world_axis=axis.tolist(),stack_mm=[2.,2.],washer_mm=0,
                  source_ids=[66,44],passed=True,penetration_mm=[4.,4.],remaining_pilot_length_mm=1.,
                  evidence='Derived from actual community 3MF retaining holes: foot through-pilot diameter1.6 through a5mm-long boss; ankle clearance diameter2.2/countersink diameter4.4; head seat to pilot entry2.0mm;4mm engagement leaves1mm of pilot before boss exit. Physical fit not yet verified. This print-to-print fastener was absent from the old motor-joint schedule.'))
totals['M2 x 6 TAP']+=1
# Actual specified washer dimensions, placed outside each measured head seat.
# These are fastener envelopes, separate from the 17 source print/motor meshes.
for c in screws:
    if not c.get('washer_mm'):
        continue
    sid=c['servo_ids'][0]
    m=trimesh.creation.annulus(r_min=1.35,r_max=2.5,height=.5,sections=64)
    direction=np.array(c['world_axis'])
    T=trimesh.geometry.align_vectors([0,0,1],direction)
    T[:3,3]=np.array(c['world_center_mm'])+direction*.25
    m.apply_transform(T)
    pos=np.array(m.vertices,dtype='<f4');faces=np.array(m.faces,dtype='<u4')
    items.append(dict(key=f'washer{sid}',name=f'0.5 mm metal washer · ID{sid}',color='#b7c4d0',colorName='Metal',
        sourceId=None,sourceName='DIN433 / ISO7092 M2.5 washer envelope',body='leg' if sid==6 else 'yaw2roll',referenceMesh='specified_washer',index=0,stage=c['stage'],
        description=f'Metal washer under motor ID{sid} rear-center screw head, against the printed retainer shoulder. ID 2.7 mm, OD 5 mm, thickness 0.5 mm. Do not put it between the two rotating links.',
        aliases='DIN433 / ISO7092 M2.5 · metal · 2 required',bounds=m.bounds.tolist(),center=m.bounds.mean(0).tolist(),dimensions=[5.,5.,.5],
        positionB64=base64.b64encode(pos.tobytes()).decode(),indexB64=base64.b64encode(faces.tobytes()).decode(),triangles=len(m.faces),
        sourceTransformWorld=T.tolist(),fastenerId=c['id'],geometryKind='specified-fastener-envelope'))
color_source=SIM/'team-share-20261001/02-STL-and-Editable-Projects/STL-Instance-Manifest.json'
data = dict(problem='P5', side='left', checked='2026-10-06', units='mm', parts=items, screws=screws,
            screwTotals=totals, deferredTorsoScrews=[c for c in schedule['connections'] if c.get('servo_ids')==[10] and c['category']=='case'],
            sourceHashes={str(p.relative_to(SIM)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [XML, color_source, motor_step, ns['SOURCE'], OUT.parent/'assembly-fasteners.json', ASSEMBLY/'community-print-inventory.json', ASSEMBLY/'source-surface-refinement.json']},
            footRegistration='Actual community foot44 and ankle66: native retaining holes coaxial and mating faces seated. Source44/source66 native ray intersections determine retention depth; small ring62 is coaxial with the lower-link boss and ankle66 pocket. The native sleeve bore is about9.65mm against a10mm boss; external14.6/15mm clearance is nominal. Physical sliding fit remains unverified.',
            physicalAssemblyVerified=False)
(OUT/'leg-data.json').write_text(json.dumps(data,separators=(',',':')))

from bundle_guide import bundle
bundle(data)
print(json.dumps({'html':str(OUT/'LEFT-LEG.html'),'parts':len(items),'screws':len(screws),'triangles':sum(p['triangles'] for p in items),'screwTotals':totals}))
