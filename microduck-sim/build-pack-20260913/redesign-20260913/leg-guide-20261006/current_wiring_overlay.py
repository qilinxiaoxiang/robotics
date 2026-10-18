"""Display-only current head and source-backed Pi contacts; no CAD or electrical changes."""
from pathlib import Path
import json,hashlib,base64,array,copy
G=Path(__file__).resolve().parent;H=G.parent/'head-redesign-20261008'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_overlay(data):
 scenePath=H/'final-viewer-20261008/scene.json';scene=json.loads(scenePath.read_text());manifest=H/'final-viewer-20261008/viewer-manifest.json';m=json.loads(manifest.read_text());assert sha(scenePath)==m['outputHashes']['scene.json']
 posePath=H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json';T=json.loads(posePath.read_text())['worldTransform'];old={p['key']:p for p in data['parts']};parts=[]
 for s in scene['parts']:
  a=array.array('f');a.frombytes(base64.b64decode(s['positionB64']));bounds=[[min(a[i::3]) for i in range(3)],[max(a[i::3]) for i in range(3)]]
  p={**old.get(s['key'],{}),**s,'bounds':bounds,'center':[(bounds[0][i]+bounds[1][i])/2 for i in range(3)],'dimensions':[bounds[1][i]-bounds[0][i] for i in range(3)],'moduleId':'head','geometryKind':'current-head-receiving' if s.get('envelope') else 'current-head-display','partKind':'reference' if s.get('envelope') else 'assembly','sourceReference':str(scenePath),'sourceSha256':sha(scenePath),'wiringRole':'cable' if s.get('flexible') else 'receiving' if s.get('envelope') else 'component'}
  if s['key']=='camera_ribbon_200':p['wiringConnectionIds']=['camera-ribbon']
  if s['key'].startswith('gpio_pin_') and s['key'].endswith('_receiving'):p['wiringRole']='receiving'
  if s['key']=='jaw_support':p['name']='Original community jaw motor support'
  parts.append(p)
 replace=sorted({p['key'] for p in data['parts'] if p['moduleId'] in ['head','head-close','electronics','camera']}|{p['key'] for p in parts})
 def point(q):return [sum(T[i][j]*q[j] for j in range(3))+T[i][3] for i in range(3)]
 pins={}
 for pin in range(1,41):
  q=[58.81,-24.141+2.54*((pin-1)//2),118.2796+(2.54 if pin%2==0 else 0)]
  pins[pin]={'partKey':'pi','connectorId':f'pi-header-{pin}','connectorType':'dupont-1pin','contactLabel':f'Pi physical {pin}','pinNumber':pin,'position':point(q),'outwardAxis':[-T[i][0] for i in range(3)],'upAxis':[T[i][2] for i in range(3)],'seatedOffsetMm':-5.96,'poseVerified':True,'poseEvidence':'Current spacer2 transform and discrete 40-pin header geometry from final head scene; pin tip frame. Seat front is -5.96 mm along outward normal at the male plastic base. Physical insertion remains untested.','illustrativeOnly':False,'connectorGeometry':{'bodyMm':[2.54,2.54,14.25],'pinCount':1,'pitchMm':2.54,'insertionDepthMm':5.96,'geometryEvidence':'Female housing receiving bound, not a measured connector; no clearance claim from this display.'}}
 return {'currentParts':parts,'replacePartKeys':replace,'piEndpoints':pins,'sourceHashes':{str(p):sha(p) for p in [scenePath,manifest,posePath,Path(__file__)]},'sceneGeometrySource':str(scenePath),'sceneGeometrySha256':sha(scenePath)}
