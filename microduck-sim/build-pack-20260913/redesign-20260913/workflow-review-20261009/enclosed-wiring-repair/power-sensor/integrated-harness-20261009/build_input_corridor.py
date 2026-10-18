from pathlib import Path
import json,hashlib
from wire_geometry import primitives,sample,tube,self_check
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[]
paths=[('vin',[[-30.85,10.9,5],[-30.85,10.9,9],[-42.2,10.9,9],[-42.2,7.5,-45]],3),('gnd',[[-33.5,-3.8,17],[-42.2,-3.8,17],[-42.2,-3.8,-45]],4)]
for net,pts,r in paths:
 pr=primitives(pts,r);q,t=sample(pr);st=self_check(pr,q,2.5);m=tube(q,t,1.25);assert m.is_volume
 f=D/f'input20v-{net}-world.stl';m.export(f)
 rows.append({'key':'input20v_'+net,'net':'VIN' if net=='vin' else 'GND','file':str(f),'sha256':sha(f),'primitives':pr,'lengthMm':sum(p['lengthMm']for p in pr),'gaugeAWG':18,'receivingDiameterMm':2.5,'minimumBendRadiusMm':r,'start':pts[0],'end':pts[-1],'selfClearance':st})
import trimesh
m=trimesh.creation.cylinder(radius=2.8,height=10,sections=32);m.apply_translation([-33.5,-2.6,17]);f=D/'input20v-gnd-t-joint-world.stl';m.export(f)
rows.append({'key':'input20v_gnd_joint','net':'GND','file':str(f),'sha256':sha(f),'geometryMeaning':'Maximum insulated T-splice receiving envelope, not a purchased part or solder workmanship acceptance','positionMm':[-33.5,-2.6,17],'boundsMm':m.bounds.tolist()})
bare=trimesh.creation.cylinder(radius=.51,height=5,sections=24);bare.apply_translation([-30.85,10.9,2.5]);land=trimesh.creation.cylinder(radius=1,height=1.3,sections=24);land.apply_transform(trimesh.transformations.rotation_matrix(1.5707963267948966,[0,1,0]));land.apply_translation([-30.85,10.9,0]);bare=trimesh.boolean.union([bare,land],engine='manifold');assert bare.is_volume;f=D/'input20v-vin-solder-lead-world.stl';bare.export(f)
rows.append({'key':'input20v_vin_pad','net':'VIN','file':str(f),'sha256':sha(f),'geometryMeaning':'18AWG bare lead and receiving solder fillet; insulate after soldering','padWorldMm':[-31.5,10.9,0]})
(D/'input20v-corridor.json').write_text(json.dumps({'parts':rows,'sourceHashes':{str(Path(__file__)):sha(__file__),str(D/'wire_geometry.py'):sha(D/'wire_geometry.py')},'integrationReady':False},indent=2)+'\n')
