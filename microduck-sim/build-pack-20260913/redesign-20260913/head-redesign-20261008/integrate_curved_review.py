"""Assemble source-bound candidates for the restored-curvature review page."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
read=lambda p:json.loads((D/p).read_text())
layout=read('curved-head/curved-layout.json');camera=read('camera-retainer/camera-retainer-report.json')
accepted_fragments=[]
config={'transforms':{},'replacementMeshes':{},'additionalParts':[],'removedParts':layout['removedParts'],'boardScope':read('board-scope.json')}
for key,file in layout['replacements'].items():config['replacementMeshes'][key]=str(Path('curved-head')/file)
# Final world-space exports include every layout transformation exactly once.
for key in ['openrb','speaker','amplifier']:config['replacementMeshes'][key]='curved-head/'+key+'-curved-layout-world.stl'
config['replacementMeshes'].update(face_panel='camera-retainer/face-with-camera-anchors-world.stl',camera_board='camera-retainer/camera-shifted-reference-world.stl')
for key,file,color,name in [
 ('camera_retainer','camera-retainer/camera-retainer-world.stl','#303833','Removable camera frame'),
 ('camera_mount_screws','camera-retainer/camera-all-six-screw-envelopes-world.stl','#a1acb3','Six camera/frame fasteners'),
 ('zero_components','curved-head/zero_w_components-world.stl','#2d7046','Zero W component receiving envelope'),
 ('zero_header','curved-head/zero_w_header_and_housing-world.stl','#5a6573','Soldered 40-pin header, housing and wire exit envelope'),
 ('zero_solder','curved-head/zero_w_gpio_solder_tails-world.stl','#a1acb3','GPIO solder-tail receiving envelope')]:
 config['additionalParts'].append(dict(key=key,mesh=file,color=color,name=name,receivingAssembly='pi' if key.startswith('zero_') else None))
for fragment in ['curved-head/viewer-fragment.json','jaw-access/viewer-fragment.json']:
 if (D/fragment).exists():
  delta=read(fragment)
  if delta.get('integrationReady') is not True:continue
  accepted_fragments.append(fragment)
  if any(p['key']=='zero_w_populated_receiving' for p in delta.get('additionalParts',[])):
   config['additionalParts']=[p for p in config['additionalParts'] if p.get('receivingAssembly')!='pi']
  config['replacementMeshes'].update(delta.get('replacementMeshes',{}));config['additionalParts']+=delta.get('additionalParts',[])
  config['transforms'].update(delta.get('transforms',{}));config['removedParts']+=delta.get('removedParts',[])
for key,file,name in [('pi_usb_receiving','curved-head/zero_w_usb_moulding-world.stl','Pi USB plug receiving space'),('openrb_usb_receiving','usb-access/full-harness/openrb-usb-c-published-envelope-world.stl','OpenRB USB-C plug receiving space')]:
 config['additionalParts'].append(dict(key=key,mesh=file,color='#448aca',name=name,plugEnvelope=True,opacity=.32))
# Enforce an unambiguous frame: no world-space replacement can also be moved.
assert not (set(config['replacementMeshes'])&set(config['transforms']))
config['removedParts']=sorted(set(config['removedParts']))
for spec in config['additionalParts']:assert (D/spec['mesh']).is_file(),spec
for file in config['replacementMeshes'].values():assert (D/file).is_file(),file
config['description']='The original community curved shell is restored. The camera sits behind the existing eye on a removable internal frame. The controller and audio parts are rearranged inside the curved head.'
config['findings']=['Original curved shell replaces the rejected box conversion.','Camera and frame fasten on the detached face before the Pi is installed.','Preferred board: first-generation Zero W with soldered 40-pin header. Pi 3B remains the bench alternative.','The Pi USB plug space extends about 14 mm above the shell; use Show plug clearance to inspect it.','Full camera-ribbon and USB-cable routing remains a separate gate.']
config['boundary']='Digital design review. No complete physical fit or commissioning claim. Actual plugs, camera rear components, screw heads and printed joints must match the declared receiving envelopes. Pi 3 fit unverified; A7Z purchase is not needed on current evidence.'
config['evidence']={p:hashlib.sha256((D/p).read_bytes()).hexdigest() for p in ['curved-head/curved-layout.json','camera-retainer/camera-retainer-report.json','board-scope.json']+accepted_fragments+[read(p)['report'] for p in accepted_fragments if read(p).get('report')]}
mesh_paths=set(config['replacementMeshes'].values())|{p['mesh'] for p in config['additionalParts']}
config['meshHashes']={p:hashlib.sha256((D/p).read_bytes()).hexdigest() for p in sorted(mesh_paths)}
config['sourceDataSha256']=hashlib.sha256((D.parent/'leg-guide-20261006/full-build-data.json').read_bytes()).hexdigest()
config['geometryChanges']={'head_cap':'Restore true source curvature; local Pi USB and rear USB-C service openings, internal mounts and lower mating-rim relief are documented in the curved-head report.','face_panel':'Original exterior with local internal camera clearance and two internal retainer anchors.','camera_board':'Existing camera envelope moved behind eye; drilled mounting holes follow official drawing.'}
(D/'viewer-candidate.json').write_text(json.dumps(config,indent=2)+'\n')
print('CURVED_REVIEW_INTEGRATED',len(config['replacementMeshes']),len(config['additionalParts']))
