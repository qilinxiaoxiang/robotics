import sys,json,hashlib,numpy as np
from pathlib import Path
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/camera-retainer/cabling');sys.path.insert(0,str(D))
import s_bend_lead_search as s
c=s.c
# Keep16mm forfirst30mm then2.25mmtransition as explicit oversize region,
# not as a manufacturer dimension. PCN36 has only the two widths dimensioned.
import inspect
code=inspect.getsource(c.make).replace('def make(', 'def make_reception(').replace('(arc-5)/8','(arc-30)/2.25')
exec(code,c.__dict__);c.make=c.make_reception
baselinePi=c.pi.copy();baselineObs=c.obs.copy();baselineSlot=c.slots.copy()
rows=[]
for shift in [0,-1,-2]:
 c.pi=baselinePi+np.array([0,shift,0.]);c.obs=baselineObs.copy();c.slots=baselineSlot.copy();c.slots['zero_w_components']=baselineSlot['zero_w_components'].translate([0,shift,0])
 for k in ['pi','zero_w_components','zero_w_header_and_housing','zero_w_gpio_solder_tails']:c.obs[k]=baselineObs[k].translate([0,shift,0])
 for front in [34.9,35.4,35.9]:
  s.front=front
  lead=1.5;top=c.pi[1]+3+lead+.3+.5
  try:r=c.make(top=top,width=11.5,lead=lead)
  except AssertionError:continue
  q=r[0]^c.obs['curved_cap'];row=r[-1]|{'piTranslationYmm':shift,'cameraSturnY':front,'capIntersectionBounds':list(q.bounding_box()) if q.volume()>1e-5 else None};rows.append(row);print(json.dumps(row),flush=True)
(D/'source-width-repack-probe.json').write_text(json.dumps({'scope':'Finite candidate only; 16mmfirst30mm plus2.25taper is receiving envelope, not PCN dimension; R3/thickness0.3/lead1.5 assumptions','rows':rows,'assemblyAcceptance':False,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*c.files.values(),c.G/'full-build-data.json',D/'source_width_repack_probe.py',D/'sc1892-official-spec.json']}},indent=2))
