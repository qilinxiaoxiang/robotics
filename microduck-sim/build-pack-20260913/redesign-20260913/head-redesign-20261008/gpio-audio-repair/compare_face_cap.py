import json,gc
from pathlib import Path
import unify_amp_cap as u
import bounded_amp_static as b
u.core.guarded_import();c=u.core;row=b.rows()['face_panel'];face=u.load(row['path']);files=[u.U/'head-cap-usb-service-world.stl',u.OUT/'cap-current-audio-usb-world.stl'];results=[]
for f in files:
 cap=u.load(f);v,bb=c.volume_pair(cap,face);results.append({'cap':str(f),'overlapMm3':v,'boundsMm':bb});del cap;gc.collect()
report={'results':results,'faceFile':str(row['path']),'sourceHashes':u.inputs([Path(__file__),*files,row['path'],b.C/'local-candidate-manifest.json']),'integrationReady':False,'boundary':'Same-face comparison. Existing-interface provenance is not an acceptance waiver.'};c.atomic_json(u.OUT/'face-cap-conflict.json',report);print(json.dumps(results))
