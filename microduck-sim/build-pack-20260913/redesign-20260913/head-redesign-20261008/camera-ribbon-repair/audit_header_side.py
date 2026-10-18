"""Stdlib plane/sign audit; no CAD or whole-scene load."""
from pathlib import Path
import json,hashlib,math
D=Path(__file__).resolve().parent;H=D.parent;hashes={}
def read(p):
 b=p.read_bytes();hashes[str(p.resolve())]=hashlib.sha256(b).hexdigest();return b
pose=json.loads(read(D/'positive-x225-pose.json'));T=pose['worldTransform'];normal=[-T[i][0] for i in range(3)];origin=[T[i][0]*67.31+T[i][3] for i in range(3)]
m=json.loads(read(D/'positive-x225/pi-geometry-manifest.json'));rows=[]
for q in m['parts']:
 p=H/q['mesh'];text=read(p).decode();vals=[]
 for line in text.splitlines():
  f=line.split()
  if f and f[0]=='vertex':
   xyz=list(map(float,f[1:]));vals.append(sum((xyz[i]-origin[i])*normal[i] for i in range(3)))
 k=q['key'];expected=([-1.6,0] if k=='pi' else [0,3.8] if k=='zero_w_components' else [-3.6,-1.6] if k=='zero_w_gpio_solder_tails' else [0,8.5] if k=='zero_w_gpio_male_receiving' else [2.54,18])
 actual=[min(vals),max(vals)];okay=all(abs(a-b)<.0001 for a,b in zip(actual,expected));rows.append({'part':k,'signedDistanceFromPcbComponentFaceMm':actual,'expectedMm':expected,'rangePassed':okay})
for p in [Path(__file__),H/'curved-head/board_envelopes.py',H/'gpio-audio-repair/scene.py',D/'rebuild_gpio_individual.py']:read(p)
r={'passed':all(q['rangePassed'] for q in rows),'scope':'Only verifies sidedness and receiving-depth geometry; does not accept whole head','userConfirmed':'Header pins are on component/top face; only solder joints on underside.','pcbLocalSourceZRangeMm':[-60.81,-59.21],'sourceComponentFaceNormal':[0,0,1],'sourceToOriginalWorldComponentNormal':[-1,0,0],'candidateComponentSideWorldNormal':normal,'worldUpIsNotBoardTop':True,'componentPlaneWorldPoint':origin,'receivingDimensionsAreNotPhysicalMeasurements':True,'note':'Positive signed distance is the PCB component/header side; negative is underside. Male and female extend positively; solder tails negatively. 0.0001mm applies only to float32 source coordinate-range roundoff, never collision acceptance.','officialMechanicalDrawing':'https://pip-assets.raspberrypi.com/categories/592-raspberry-pi-zero-w/documents/RP-008367-DS-1-raspberry-pi-zero-w-mechanical-drawing.pdf','officialDrawingScope':'Board outline and component face; header direction is also explicitly user-confirmed. Header/body heights are bounded receiving assumptions, not dimensions certified by this drawing.','checks':rows,'sourceHashes':hashes}
(D/'header-side-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':r['passed'],'normal':normal,'failures':[x for x in rows if not x['rangePassed']]}));assert r['passed']
