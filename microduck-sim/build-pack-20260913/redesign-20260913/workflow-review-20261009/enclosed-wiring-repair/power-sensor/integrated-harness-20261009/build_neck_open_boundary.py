from pathlib import Path
import json,hashlib
from wire_geometry import primitives,sample,tube,self_check
D=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for net,y,od in [('5v',-7.6,2.5),('gnd',-3.8,2.5),('data',1,1.5)]:
 pts=[[6,y,55],[6,y,67],[-4,y,77],[-4,y,85],[6,y,95],[6,y,98]];pr=primitives(pts,4);q,t=sample(pr);check=self_check(pr,q,od);mesh=tube(q,t,od/2);assert mesh.is_volume;f=D/f'neck-open-{net}-world.stl';mesh.export(f)
 rows.append({'key':'neck_open_'+net,'net':net.upper(),'file':str(f),'sha256':sha(f),'primitives':pr,'lengthMm':sum(p['lengthMm']for p in pr),'start':pts[0],'end':pts[-1],'diameterMm':od,'selfClearance':check,'jointMotionValidated':False,'meaning':'Neutral flexible dressing example, not a prescribed rigid shape or certified flex loop; endpoint is an open interface below the head.'})
(D/'neck-open-boundary.json').write_text(json.dumps({'parts':rows,'integrationReady':False,'sourceHashes':{str(Path(__file__)):sha(__file__),str(D/'wire_geometry.py'):sha(D/'wire_geometry.py')}},indent=2)+'\n')
