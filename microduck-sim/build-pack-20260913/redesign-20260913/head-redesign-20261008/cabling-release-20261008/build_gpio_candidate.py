"""Finite complete four-I2S wiring route under explicit11mm mate+OD1.5/R2 specs."""
from check_routes import *
import ast
for node in ast.parse((H/'usb-access/full-harness/build_harness.py').read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['arc','rounded']:exec(compile(ast.Module(body=[node],type_ignores=[]),'<arc>','exec'))
obs.pop('zero_w_populated_receiving')
for k in ['zero_w_components','zero_w_gpio_solder_tails']:obs[k]=man(load(H/'curved-head'/(k+'-world.stl')))
obs['gpio_housing_11mm']=mf.Manifold.cube([11,52,7],True).translate([61.81,-.011,119.5496])
for k,f in [('head_cap','cap-audio-rotation-candidate-world.stl'),('amplifier','amplifier-audio-rotation-candidate-world.stl'),('curved_cap_hardware','hardware-audio-rotation-candidate-world.stl'),('speaker_keeper','speaker-keeper-wire-relief-candidate-world.stl')]:obs[k]=man(load(D/f))
for i in [0,1]:obs[f'speaker_wire_{i}']=man(load(D/f'speaker-wire-{i}-candidate-world.stl'))
rows=[];sol=[]
for i,(pin,signal,pad,lane) in enumerate([(12,'BCLK',6,54.31),(20,'GND',2,58.31),(35,'LRCLK',7,60.31),(40,'DIN',5,62.31)]):
 y=-24.141+2.54*((pin-1)//2);z=118.2796+(2.54 if pin%2==0 else 0);start=np.array([56.31,y,z]);pts,L=arc(start,np.array([-1.,0,0]),np.array([0.,0,1.]),2);p=pts[-1]
 # Exact EagleJP1 R180 pose and current amp+90/+0.8 transform.
 pady=(24.1100006104+8.89-(-7.62+(pad-1)*2.54))-56.2
 end=np.array([40.257000885,pady,133.5849994]);busz=126.5+i*2
 wp=[p,[54.31,y,busz]]
 if lane>54.31:wp.append([lane,y,busz])
 wp.extend([[lane,pady,busz],[lane,pady,138],[end[0],pady,138],end]);wp=np.array(wp)
 try:pp,ll=rounded(wp,2)
 except ValueError as e:print(pin,wp);raise
 pts=np.vstack([pts,pp[1:]]);L+=ll;s=tube(pts,.75);sol.append(s);hh={}
 for k,o in obs.items():
  if k=='gpio_housing_11mm':o-=mf.Manifold.cube([2,2.4,2.4],True).translate(start)
  if k=='amplifier':o-=mf.Manifold.cube([2.4,2.4,2],True).translate(end)
  v=hits(s,o)
  if v>1e-5:hh[k]=v
 tri(s).export(D/f'gpio-{pin}-candidate-world.stl');rows.append({'physicalPin':pin,'signal':signal,'ampEaglePad':pad,'startMm':start.tolist(),'endMm':end.tolist(),'lengthMm':L,'diameterMm':1.5,'Rmm':2,'centerlineMm':pts.tolist(),'intersectionsMm3':hh})
pairs={}
for i in range(4):
 for j in range(i+1,4):
  v=hits(sol[i],sol[j])
  if v>1e-5:pairs[f'{rows[i]["physicalPin"]}-{rows[j]["physicalPin"]}']=v
out={'assumption':'Header plus fully seated female housing totaldepth<=11mm from component-sidePCBface; pins on standard2.54grid, pin1 atSD/-Y end and oddrowboardedge/-Z. Map must match actual marked pin1. OD1.5/R2 are receiving specs.','rows':rows,'wirePairIntersectionsMm3':pairs,'sourceHashes':hashes,'accepted':False};(D/'gpio-candidate.json').write_text(json.dumps(out,indent=2)+'\n');print([(x['physicalPin'],x['intersectionsMm3']) for x in rows]);print('pairs',pairs)
