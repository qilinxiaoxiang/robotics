from pathlib import Path
import ast,json,hashlib,math
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parents[1]/'motor-wires'
from wire_geometry import primitives,sample,tube,solid,self_check
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[]
for net,points in [('5V',[[-7,-7,35.5],[-7,-7,44],[6,-7.6,48],[6,-7.6,55]]),('GND',[[-7,7,35.5],[1,7,37.4],[6,-3.8,48],[6,-3.8,55]])]:
 pr=primitives(points,4);q,t=sample(pr);selftest=self_check(pr,q,2.5);mesh=tube(q,t,1.25);assert mesh.is_volume
 f=D/f'head-trunk-{net.lower()}-world.stl';mesh.export(f)
 rows.append({'key':'head_trunk_'+net.lower(),'net':net,'file':str(f),'sha256':sha(f),'primitives':pr,'lengthMm':sum(x['lengthMm']for x in pr),'gaugeAWG':18,'receivingDiameterMm':2.5,'start':points[0],'end':points[-1],'selfClearance':selftest,'endpointAxis':[0,0,1],'headEndpointAccepted':False})
(D/'head-trunk.json').write_text(json.dumps({'parts':rows,'status':'STATIONARY_BODY_TO_OPEN_NECK_BOUNDARY_ONLY','sourceHashes':{str(Path(__file__)):sha(__file__),str(D/'wire_geometry.py'):sha(D/'wire_geometry.py')}},indent=2)+'\n');print([(r['key'],r['lengthMm'])for r in rows])
