"""Bind staged roof/harness artifacts to the restored-body Fusion assembly."""
from pathlib import Path
import json,hashlib,copy,shutil
import trimesh
P=Path(__file__).resolve().parent
base=P.parent/'original-body-converter/fusion-import-manifest.json'
x=json.loads(base.read_text());parts=copy.deepcopy(x['parts']);roof=json.loads((P/'roof/roof-restoration.json').read_text())
for p in parts:
 if p['key']=='head_cap':
  p.update(file=roof['output'],sha256=roof['outputSha256'],name='Restored continuous crown - original surface',expectedFinalBoundsMm=trimesh.load(roof['output'],force='mesh').bounds.tolist())
 p['isWire']=p['key']=='camera_ribbon_200'
for label in ['head-wires','motor-wires']:
 f=P/label/'manifest.json';y=json.loads(f.read_text())
 (P/'fusion'/(label+'-manifest.json')).write_text(json.dumps(y,indent=2)+'\n')
 for extra in ['routes.json','local-check.json','static-summary.json','route-check-summary.json','stage-summary.json','head-local-check.json','head-internal-check.json','i2s-final-check.json','review-summary.json']:
  e=P/label/extra
  if e.exists():shutil.copyfile(e,P/'fusion'/(label+'-'+extra))
 for q in y['parts']:
  if q.get('adopted',True) is False:continue
  p=copy.deepcopy(q);p['importTranslationMm']=[0,0,0];p['isWire']=True
  # Wire records can replace an inherited ribbon/connector rather than duplicate it.
  replace='openrb_usb_receiving' if p['key']=='mac_usb_c_plug' else p.get('replacesKey',p['key'])
  parts=[old for old in parts if old['key']!=replace]
  p.setdefault('group',label);p.setdefault('color','#666666');p.setdefault('name',p['key']);p['color']=p.get('reviewColor',p['color'])
  p['expectedFinalBoundsMm']=trimesh.load(p['file'],force='mesh').bounds.tolist()
  p['sha256']=hashlib.sha256(Path(p['file']).read_bytes()).hexdigest()
  dest=P/'fusion/model-inputs'/Path(p['file']).name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p['file'],dest);p['originalFile']=p['file'];p['file']=str(dest);assert hashlib.sha256(dest.read_bytes()).hexdigest()==p['sha256']
  parts.append(p)
assert len(set(p['key'] for p in parts))==len(parts)
x.update(status='ROOF_AND_WIRING_NATIVE_CAD_STAGE',parts=parts,sourceBodyManifest=str(base),motorBusOwner='Mac via OpenRB USB; Pi only sensors/audio',runtimeMigrationPassed=False,physicalAssemblyAccepted=False,printReady=False)
(P/'fusion/fusion-import-manifest.json').write_text(json.dumps(x,indent=2)+'\n')
print(json.dumps({'parts':len(parts),'wireAndConnectorBodies':sum(p['isWire'] for p in parts)}))
