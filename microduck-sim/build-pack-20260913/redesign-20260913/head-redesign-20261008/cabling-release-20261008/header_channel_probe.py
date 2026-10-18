from check_routes import *
# Complete GPIO mate depth<=11mm from component-sidePCB face67.31 is a declared
# receiving spec. Replace the legacy15mm combined housing+wire box with actual
# housing capacity11mm, preserving independent populated components/tails.
obs.pop('zero_w_populated_receiving')
for k in ['zero_w_components','zero_w_gpio_solder_tails']:obs[k]=man(load(H/'curved-head'/(k+'-world.stl')))
obs['gpio_housing_11mm']=mf.Manifold.cube([11,52,7],True).translate([61.81,-.011,119.5496])
for k,f in [('head_cap','cap-audio-rotation-candidate-world.stl'),('amplifier','amplifier-audio-rotation-candidate-world.stl'),('curved_cap_hardware','hardware-audio-rotation-candidate-world.stl'),('speaker_keeper','speaker-keeper-wire-relief-candidate-world.stl')]:obs[k]=man(load(D/f))
rows=[]
for x in [54.5,55.5]:
 for z in [124.5,126.5,128.5]:
  pts=[[x,25,z],[x,-28,z],[x,-28,138],[44,-28,138]];s=tube(pts,.75);hh=check(s)
  rows.append({'x':x,'z':z,'points':pts,'hits':hh})
print(json.dumps(rows,indent=2));(D/'header-channel-probe.json').write_text(json.dumps({'rows':rows,'sourceHashes':hashes},indent=2)+'\n')
