from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;H=D.parent;O=D/'positive-x225';hashes={}
def read(p):
 b=p.read_bytes();hashes[str(p.resolve())]=hashlib.sha256(b).hexdigest();return json.loads(b)
m=read(D/'local-candidate-manifest.json');pi=read(O/'pi-geometry-manifest.json');cam=read(O/'camera-three-screw-clamp-report.json');support=read(O/'pi-support-report.json');pose=read(D/'positive-x225-pose.json');header=read(D/'header-side-audit.json');assert header['passed']
m['integrationReady']=False;m['purpose']='Independent +2.25X Pi, +0.8X camera, three-screw four-land clamp candidate. Static/support subchecks only; full ribbon and assembly pending.'
m['replacementMeshes'].update({'pi':'camera-ribbon-repair/positive-x225/pi-world.stl','face_panel':support['exports']['face_panel'],'head_bottom':support['exports']['head_bottom'],'camera_board':cam['exports']['camera_board_clamped'],'camera_retainer':cam['exports']['camera_three_screw_clamp'],'eye_trim':cam['exports']['eye_three_screw_camera'],'head_cap':'usb-access/usb-repair/cap-usb-positive-x225-world.stl'})
m['additionalParts']=[x for x in m['additionalParts'] if not x['key'].endswith('_revision_screw')]
by={x['key']:x['mesh'] for x in pi['parts']}
for x in m['additionalParts']:
 if x['key'] in by:x['mesh']=by[x['key']]
for row in support['screws']:
 m['additionalParts'].append({'key':row['id']+'_revision_screw','name':row['id']+' M2.5 x 6 TAP','mesh':support['exports'][row['id']],'color':'#b9bec6'})
for row in cam['screws']:
 m['additionalParts'].append({'key':row['id'],'name':row['id']+' M2 x 4 TAP','mesh':cam['exports'][row['id']],'color':'#b9bec6'})
m['piWorldTransform']=pose['worldTransform'];m['cameraShiftFromPublishedMm']=[.9,0,0];m['piMounting']='Exactly E-pi-01,02,04 fixed with M2.5x6 TAP; original03 omitted and passively supported. Header/18mm female on component face; solder tails only on underside.';m['cameraFasteners']=cam['screws'];m['cameraMounting']='Four printed bearing lands at PCB holes; round and relieved locating pegs; entire rear clamp retained by three non-collinear M2x4 TAP screws. No nuts required, no screws through camera PCB.'
m['pending']=['All insertion/fastener tool/closure paths for new candidate','Full 200mm SC1892 ribbon width16 and revision11.5 routes','GPIO and USB full harness against this pose and hardware','Complete articulation domain and source-contact review','Printed material/load and hardware dimensional commissioning']
m['diagnosticGeometry']={};m['diagnosticRibbonStatus']='No ribbon is accepted or included in candidate. Previous diagnostic geometries belong to other endpoints; preserve their negative reports only.'
for f in ['build_x225_manifest.py','build_x225_pi_support.py','build_three_screw_camera_clamp.py','build_reverse_nut_camera.py']:
 p=D/f;hashes[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
for f in list(m['replacementMeshes'].values())+[x['mesh'] for x in m['additionalParts']]:
 p=H/f;hashes[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
m['sourceHashes']=hashes;(O/'candidate-manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(hashlib.sha256((O/'candidate-manifest.json').read_bytes()).hexdigest())
