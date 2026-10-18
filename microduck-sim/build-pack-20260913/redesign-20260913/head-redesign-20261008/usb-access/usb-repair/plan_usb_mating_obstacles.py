"""Bound all sampled USB-A mating shapes before isolated obstacle checks."""
from pathlib import Path
import hashlib,json,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from route_geometry import fillet_polyline,circular_arc
D=Path(__file__).resolve().parent
paths=[D/'positive-x225-usb-plan.json',D/'positive-x225-mating-plan.json',D/'positive-x225-obstacle-plan.json']
p,m,scene=[json.loads(f.read_text()) for f in paths]
for r in (p,m,scene):
    for f,h in r['sourceHashes'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,('Stale',f)
end=p['cEndArc'];arc,_=circular_arc(end['startMm'],end['incoming'],end['outgoing'],10)
jobs=[];bounds={}
for row in m['rows']:
    span=row['spanMm'];final=next(r for r in p['rows'] if r['scFlexibleMm']==span)
    boxes=[]
    for s in row['samples']:
        pts,_=fillet_polyline(s['waypointsMm'],10);pts=np.vstack([pts,arc[-2::-1]])
        # Covers the nominal round cable and its circular-arc chord deviation.
        boxes.append([pts.min(axis=0)-2.252,pts.max(axis=0)+2.252])
        mate=np.asarray(final['usbAMatingPointMm'])+np.asarray(p['scFinalDirection'])*s['withdrawalMm']
        boxes.extend([[mate+[-22.9,-10,-6],mate+[0,10,6]],
                      [mate+[0,-6,-2.25],mate+[15,6,2.25]]])
    bb=np.array([np.min(np.array(boxes)[:,0],axis=0),np.max(np.array(boxes)[:,1],axis=0)])
    bounds[span]=bb.tolist()
    for key,part in scene['obstacles'].items():
        ob=np.array(part['bounds'])
        if np.all(bb[0]<ob[1]) and np.all(ob[0]<bb[1]):jobs.append({'spanMm':span,'obstacle':key})
out={'jobs':jobs,'obstacleCount':len(scene['obstacles']),'boundsBySpan':bounds,
     'sourceHashes':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths+[Path(__file__),D/'route_geometry.py']},
     'scope':'Conservative union bounds of all61 mating samples at neutral robot pose; not final assembly acceptance.'}
(D/'positive-x225-mating-obstacles.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'selectedJobs':len(jobs),'obstacles':sorted({j['obstacle'] for j in jobs})}))
