from pathlib import Path
D=Path(__file__).resolve().parent
src=(D/'verify_harness.py').read_text();exec(src[:src.index('rows=[]\nfor qdeg')])
guides={k:man(load(D/(k+'-world.stl'))) for k in ['removable_rear_cable_guide','removable_rear_cable_guide_cover']};failure=[]
for qdeg in cases:
 posed,_=fk({k:np.deg2rad(v) for k,v in qdeg.items()});T=posed[headBody]@Pinv[headBody];hh={}
 for k,g in guides.items():
  a=g.transform(T[:3,:])
  for n,o in obs.items():
   if bodymap[n]==headBody:continue
   Tb=posed[bodymap[n]]@Pinv[bodymap[n]];v=hits(a,o.transform(Tb[:3,:]))
   if v>1e-4:hh[k+'--'+n]=v
 if hh:failure.append({'jointDegrees':qdeg,'intersectionsMm3':hh})
install=[]
for pitch in [0,60]:
 posed,_=fk({'head_pitch':np.deg2rad(pitch)});T=posed[headBody]@Pinv[headBody];ob={k:o.transform((posed[bodymap[k]]@Pinv[bodymap[k]])[:3,:]) for k,o in obs.items()};peak={}
 for dz in np.arange(-40,.001,.25):
  g=guides['removable_rear_cable_guide'].translate([0,0,dz]).transform(T[:3,:])
  for k,o in ob.items():
   v=hits(g,o)
   if v>1e-4:peak[k]=max(peak.get(k,0),v)
 install.append({'headPitchDegrees':pitch,'localStartOffset':[0,0,-40],'localEndOffset':[0,0,0],'samples':161,'peakIntersectionsMm3':peak})
result={'optionalGuideOnly':True,'articulatedStatesTested':len(cases),'articulatedFailures':failure,'installationPaths':install,'strainReliefPhysicalVerified':False};(D/'removable-guide-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
