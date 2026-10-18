"""Conditional side-exit feasibility during Pi layout search; not release geometry."""
from pathlib import Path
import json,numpy as np,sys,hashlib
from scipy.optimize import brentq
from route_geometry import circular_arc,fillet_polyline,tube,unit
D=Path(__file__).resolve().parent;H=D.parent.parent;OLD=D.parent/'full-harness'
posepath=H/'camera-ribbon-repair/optimized-pi-pose.json';T=np.array(json.loads(posepath.read_text())['transform'])
r=json.loads((OLD/'full-harness-report.json').read_text());p=(T@np.r_[r['geometry']['piCableExitMm'],1])[:3];axis=unit(T[:3,:3]@[0,0,1]);end=np.array([-1.,0,0]);c=np.array(r['geometry']['usbCCableExitMm']);caxis=np.array(json.loads((OLD/'published-usbc-verification.json').read_text())['outwardAxis'])
arc,arcLength=circular_arc(p,axis,end,10);rows=[]
for span in [25,30,40,50,60,70,80]:
 femaleTail=arc[-1]+end*(span-arcLength);mate=femaleTail+end*25;maleTail=mate+end*22.9
 shortest=None;best=None
 # Four waypoints create two radius10 bends joined by a diagonal straight.
 def get(extra):
  rear=min(maleTail[0],c[0])-12-extra
  q=c+caxis*((rear-c[0])/caxis[0])
  wp=[maleTail,[rear,maleTail[1],maleTail[2]],q,c]
  return (*fillet_polyline(wp,10),wp)
 previous=None
 for extra in np.arange(0,101,.5):
  try:pts,L,wp=get(extra)
  except ValueError:continue
  if shortest is None or L<shortest:shortest=L
  f=L-102.5
  if previous and f*previous[1]<=0:
   val=brentq(lambda e:get(e)[1]-102.5,previous[0],extra);points,L,waypoints=get(val);best={'extraRearMm':float(val),'lengthMm':L,'points':points.tolist(),'waypoints':np.array(waypoints).tolist()};break
  previous=(extra,f)
 row={'conditionalSCFlexibleSpanMm':span,'piExitWorldMm':p.tolist(),'piAxis':axis.tolist(),'femaleTailWorldMm':femaleTail.tolist(),'maleTailWorldMm':maleTail.tolist(),'shortestTestedACMm':shortest,'candidate':best};rows.append(row)
 print(span,'min',shortest,'solution',bool(best),flush=True)
report={'scope':'Conditional route feasibility only; candidate Pi pose not accepted, no collision/strain relief/assembly acceptance','sourcePiPoseSha256':hashlib.sha256(posepath.read_bytes()).hexdigest(),'scLengthInterpretationKnown':False,'samples':rows,'manufacturingAccepted':False};(D/'side-usb-feasibility.json').write_text(json.dumps(report,indent=2)+'\n')
