from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;E=D.parents[1];W=E.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
topfile=D.parent/'active-topology.json';top=json.loads(topfile.read_text());package=E/'power-sensor/head-controller-study/final-integration-20261009/custom-harness-package.json';x=json.loads(package.read_text());obs=x['parts'].copy()
old=W/'roof-wiring-stage/motor-wires/obstacles';native=json.loads((E/'ankle-wires/native-motors/manifest.json').read_text())
for key in ['neck_pitch','head_yaw_link','neck','upper_pad','neck_roll','neck_link','torso_base','shell_left','shell_right','power_support']:
 p=old/(key+'.json')
 if p.exists():
  o=json.loads(p.read_text());o['worldTransform']=[[1,0,0,o.get('importTranslationMm',[0,0,0])[0]],[0,1,0,o.get('importTranslationMm',[0,0,0])[1]],[0,0,1,o.get('importTranslationMm',[0,0,0])[2]],[0,0,0,1]];obs.append(o)
# Motor11/12 native pieces are added by the geometric checker using the same official source and registered transforms.
ids=['ttl-15-14','ttl-14-13','ttl-13-11','ttl-11-12'];routes=[r for r in top['routes']if r['id']in ids]
plan={'status':'candidate','routes':routes,'ports':{k:v for k,v in top['ports'].items()if any(k==r[side]for r in routes for side in ['fromPort','toPort'])},'obstacles':obs,'nativeMotorSource':[p for p in native['parts']if p['motor']==2], 'sourceHashes':{str(topfile):sha(topfile),str(package):sha(package),str(E/'ankle-wires/native-motors/manifest.json'):sha(E/'ankle-wires/native-motors/manifest.json')},'wholeHarnessAccepted':False}
(D/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');print(len(obs),'obstacles')
