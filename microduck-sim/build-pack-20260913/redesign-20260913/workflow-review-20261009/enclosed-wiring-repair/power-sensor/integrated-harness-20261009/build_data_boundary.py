from pathlib import Path
import ast,json,hashlib,math
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;M=D.parents[1]/'motor-wires'
from wire_geometry import primitives,sample,tube,solid,self_check
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=[]
for name,points in [('data_12_05',[[-5.5,-9.5,22],[-5.5,-9.5,24.5],[-5.5,-17,24.5],[11.5,-17,24.5],[11.5,-17,30],[18,-17,38.9215],[18,-10.5,38.9215]]),('data_openrb_10',[[-5.5,25.5,22],[-5.5,25.5,24.5],[-5.5,10,24.5],[11.5,10,24.5],[11.5,10,43],[6,1,49],[6,1,55]])]:
 pr=primitives(points);q,t=sample(pr);selftest=self_check(pr,q);mesh=tube(q,t);assert mesh.is_volume
 f=D/(name+'-world.stl');mesh.export(f)
 rows.append({'key':name,'net':'DATA','file':str(f),'sha256':sha(f),'primitives':pr,'lengthMm':sum(x['lengthMm']for x in pr),'gaugeAWG':22,'receivingDiameterMm':1.5,'selfClearance':selftest,'start':points[0],'end':points[-1],'headEndpointAccepted':False})
(D/'data-boundary.json').write_text(json.dumps({'parts':rows,'status':'CANDIDATE_DATA_ONLY_ZONE_BOUNDARIES','sourceHashes':{str(Path(__file__)):sha(__file__),str(D/'wire_geometry.py'):sha(D/'wire_geometry.py')}},indent=2)+'\n');print([(r['key'],r['lengthMm'])for r in rows])
