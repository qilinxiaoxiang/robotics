from scene import *
keys=['amplifier','speaker','speaker_cradle','speaker_keeper','speaker_wire_0','speaker_wire_1']
rows=[];peak={}
for z in np.arange(40,-.001,-.25):
 hh={}
 for k in keys:
  q=obs[k].translate([0,0,-z])
  for f in ['head_cap','openrb']:
   v=hits(q,obs[f])
   if v>1e-5:hh[k+'--'+f]=v;peak[k+'--'+f]=max(peak.get(k+'--'+f,0),v)
 rows.append({'translationMm':[0,0,-float(z)],'hits':hh})
out={'problemIds':['P5','P6'],'movingKeys':keys,'fixedKeys':['head_cap','openrb'],'samples':rows,'peakHitsMm3':peak,'sourceHashes':hashes,'scope':'Prewired speaker+amp+two speaker wires+loose cage fit to detached cap; power/I2S loose tails, restraints and final Pi connection not included yet.'}
(D/'prewired-audio-baseline.json').write_text(json.dumps(out,indent=2)+'\n');print(peak)
