import json
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
D=Path(__file__).resolve().parent;c.guarded_import();f=D/'amp16z2-placement-world.stl';m=c.tm.load(f,force='mesh');s=pm.load(c,f)
r={'sourceSha256':c.sha(f),'sourceTrimeshWatertight':bool(m.is_watertight),'sourceWindingConsistent':bool(m.is_winding_consistent),'sourceManifoldStatus':str(s.status()),'sourceManifoldVolumeMm3':s.volume(),'triangles':len(m.faces),'integrationReady':False}
o=D/'amp16z2-closed-receiving-world.stl'
try:
 r['roundTrip']=pm.export(c,s,o);b=pm.load(c,o);r['removedMm3']=max(0,(s-b).volume());r['addedMm3']=max(0,(b-s).volume());r['outputSha256']=c.sha(o);r['sameSolid']=r['removedMm3']<1e-8 and r['addedMm3']<1e-8
except Exception as e:r['error']=str(e)
c.atomic_json(D/'amp-closed-readback.json',r);print(json.dumps(r))
