from check_routes import *
r=json.loads(read(D/'audio-route-candidate.json'))
for k,f in [('head_cap','cap-audio-rotation-candidate-world.stl'),('amplifier','amplifier-audio-rotation-candidate-world.stl'),('curved_cap_hardware','hardware-audio-rotation-candidate-world.stl')]:obs[k]=man(load(D/f))
wirechecks=[]
for diameter in [1.2,1.5]:
 for i,row in enumerate(r['speakerWires']):
  points=np.array(row['centerlineMm']);s=tube(points,diameter/2);p=points[0];end=points[-1];hh={}
  for k,o in obs.items():
   if k=='speaker':o-=mf.Manifold.cube([2.4,2.4,1.6],True).translate(p)
   if k=='amplifier':o-=mf.Manifold.cube([1.8,1.8,1.8],True).translate(end)
   v=hits(s,o)
   if v>1e-5:hh[k]=v
  wirechecks.append({'wire':i,'diameterMm':diameter,'intersectionsMm3':hh})
# Physical pin index is deliberately NOT inferred from a rectangular receiver.
# Probe available wire departure capacity over the full20x2 geometric row grid.
# Any mapping needs board orientation/pin1 resolved before final net routing.
header=[]
for zi,z in enumerate([118.2796,120.8196]):
 for i in range(20):
  y=-24.141+2.54*i;p=np.array([52.31,y,z]);s=tube([p,p+[-5,0,0]],.75);hh=check(s,['zero_w_populated_receiving']);header.append({'row':zi,'column':i,'exitMm':p.tolist(),'straight5mmIntersectionsMm3':hh})
out={'speakerWireDiameterSensitivity':wirechecks,'headerDepartureProbe':header,'headerSpecBoundary':'20x2 standard2.54mm grid inside the frozen15mm housing/lead receiving box. This is neither actual plug model nor electricalpin mapping. All other physical obstacles retained. Ø1.5 wire5mm straight exit normal to board.','sourceHashes':hashes,'assemblyAcceptance':False}
(D/'interface-checks.json').write_text(json.dumps(out,indent=2)+'\n');print('WIRE',wirechecks);print('HEADER',sum(bool(a['straight5mmIntersectionsMm3']) for a in header),'of',len(header),'blocked');print([a for a in header if a['straight5mmIntersectionsMm3']][:6])
