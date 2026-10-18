import json
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
D=Path(__file__).resolve().parent;A=D/'cap-amp16z2';c.guarded_import();cap=pm.load(c,A/'cap-current-audio-usb-world.stl');amp=pm.load(c,D/'amp16z2-closed-receiving-world.stl').translate([0,0,-2]);rem=cap-pm.load(c,A/'amp-new-post-0-world.stl')-pm.load(c,A/'amp-new-post-1-world.stl');r=[]
for i,x in enumerate(rem.decompose()):
 gap=float(amp.min_gap(x,2))
 if True:r.append({'part':i,'gap':gap,'volume':x.volume(),'bounds':list(x.bounding_box())})
c.atomic_json(D/'speaker-rewire/amp-entry-gap-diagnosis.json',{'rows':r});print(json.dumps(r))
