from pathlib import Path
import json,numpy as np,trimesh,hashlib,re
F=Path(__file__).resolve().parent;r=json.loads((F/'custom-harness-package.json').read_text());P=np.array(r['piCurrentWorldDelta']);axis=P[:3,2];ports=[]
for q in r['parts']:
 if 'gpio_pin_'not in q['key']:continue
 m=trimesh.load_mesh(q['file']);m.apply_transform(q['worldTransform']);v=np.asarray(m.vertices);localAxis=axis;d=v@axis;mask=m.face_normals@axis>.99999;end=np.average(m.triangles_center[mask],axis=0,weights=m.area_faces[mask]);mask=m.face_normals@axis<-.99999;front=np.average(m.triangles_center[mask],axis=0,weights=m.area_faces[mask]);pin=int(re.search(r'pin_(\d+)',q['key']).group(1));ports.append({'physicalPin':pin,'wireExitWorldMm':end.tolist(),'femaleSeatedFrontWorldMm':front.tolist(),'outwardAxis':localAxis.tolist(),'receivingLengthMm':float(d.max()-d.min()),'partKey':q['key'],'file':q['file'],'sha256':q['sha256'],'worldTransform':q['worldTransform']})
T=np.array(r['boardNativeToWorld']);j4=[]
for x,net in [(-1.71,'GND'),(1.79,'VIN+')]:
 p=(T@np.array([x,-33.89,4.215,1]))[:3];j4.append({'net':net,'mouthWorldMm':p.tolist(),'outwardAxis':(-T[:3,1]).tolist(),'insertionAxis':T[:3,1].tolist(),'source':'roof-wiring-stage/roof/j4/terminal-registration.json; official native J4 cavity at X +/-1.75 Y-33.89 Z4.215; polarity official VIN jumper side mapping'})
out={'status':'CURRENT_RIGID_DATUMS_ONLY','sourceManifest':str(F/'custom-harness-package.json'),'sourceSha256':hashlib.sha256((F/'custom-harness-package.json').read_bytes()).hexdigest(),'group':'all head electronics follow detached cap; mechanisms and face installed later','piPorts':ports,'OpenRBJ4':j4,'branchNets':'Pi5V pins2/4 with matching ground pins6/14 per integrated-harness plan; IMU pins1/3/5/9; I2S12/35/40/20. No topology change implicit.','routesAccepted':False};(F/'current-head-interfaces.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
