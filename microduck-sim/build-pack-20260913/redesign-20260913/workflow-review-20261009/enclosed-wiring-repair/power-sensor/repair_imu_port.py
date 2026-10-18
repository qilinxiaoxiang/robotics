"""One registered side-port aperture; native BRep subtraction, no route search."""
from pathlib import Path
import cadquery as cq,json,hashlib
D=Path(__file__).resolve().parent
SIM=next(p for p in D.parents if p.name=='microduck-sim')
A=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/trunk-imu'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def box(lo,hi):return cq.Solid.makeBox(*(hi[i]-lo[i] for i in range(3)),cq.Vector(*lo))
def vol(s):return sum(x.Volume() for x in s.Solids())
h=cq.importers.importStep(str(A/'imu_clamp_holder.step')).val()
c=cq.importers.importStep(str(A/'imu_rear_cover.step')).val()
# Width7 includes JST pull protrusions; height2.8 and length5 official SH PDF.
# Entire receiving box is conservative; cavity mating material is not tested as interference.
# MouthXsource=.065, socket rear4.315; mated total length6.25 gives outward end=-1.935.
plug=box([-57.48,-14.635,11.5],[-54.68,-9.635,18.5])
# Fixed 0.6+ allowance about the published housing at the sidewall.
aperture=box([-58.1,-16.3,10.9],[-54.0,-14.4,19.1])
fixed=h.cut(aperture)
assert h.isValid() and fixed.isValid() and len(fixed.Solids())==1
# Check full continuous 12mm straight insertion swept envelope, no frame omission.
sweep=box([-57.48,-26.635,11.5],[-54.68,-9.635,18.5])
negative=vol(h.intersect(sweep));positive=vol(fixed.intersect(sweep));cover=vol(c.intersect(sweep))
assert negative>1 and positive<1e-8 and cover<1e-8,(negative,positive,cover)
# Every original rear screw boss entire geometric zone unchanged, not just hole centers.
bosses=[]
for y in [-17.5,17.5]:
 for z in [4,26]:
  zone=box([-61.5,y-2.01,z-2.01],[-55.9,y+2.01,z+2.01])
  removed=vol(h.intersect(zone).cut(fixed));assert removed<1e-8
  bosses.append({'centerWorldMm':[-58.9,y,z],'removedMm3':removed})
for key,obj in [('imu-clamp-side-port-world',fixed),('jst-sh4-receiving-world',plug),('jst-sh4-insertion-sweep-world',sweep)]:
 cq.exporters.export(obj,str(D/f'{key}.step'));cq.exporters.export(obj,str(D/f'{key}.stl'),tolerance=.03,angularTolerance=.1)
r={'scope':'BNO085 CONN4 housing insertion through existing IMU clamp; separate from complete wire routing and physical fit','status':'DIGITAL_PORT_APERTURE_PASSED','sourceHashes':{str(p):sha(p) for p in [A/'imu_clamp_holder.step',A/'imu_clamp_holder_body.stl',A/'imu_rear_cover.step',D/'bno085-endpoint-registration.json',D/'sources/jst-sh.pdf',Path(__file__)]},'connector':{'source':'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf','page':2,'family':'SHR-04V-S-B with protrusions conservatively received','bodyMm':[7,2.8,5],'axisConvention':'width worldZ; height worldX; insertion world+Y','installedReceivingBoundsMm':[[-57.48,-14.635,11.5],[-54.68,-9.635,18.5]],'socketMatingDepthCaveat':'Housing box is only a conservative external receiving volume. Source socket mating contact is excluded from this enclosure clearance test.'},'apertureBoundsMm':[[-58.1,-16.3,10.9],[-54,-14.4,19.1]],'minimumHousingSideClearanceMm':.6,'insertionTravelMm':12,'continuousSweptVolumeIntersectionsMm3':{'originalHolder':negative,'repairedHolder':positive,'rearCover':cover},'originalVolumeMm3':vol(h),'repairedVolumeMm3':vol(fixed),'removedVolumeMm3':vol(h)-vol(fixed),'validBRep':True,'solidCount':1,'preservedRearBosses':bosses,'section':{'sideWallRemainingXWidthsMm':[3.3,2.6],'wallThicknessMm':1.2,'openingZmm':[10.9,19.1],'bottomAndTopFrameUnchanged':True},'installation':['Connect the keyed SH plug while the rear cover is off.','Place the BNO085 board in the declared orientation with plug through the negative-Y aperture.','Retain the cable outside the opening before fastening the rear cover; retain slack and do not pull the socket.'],'remaining':['Actual board retention and source board-to-holder installation need verification.','Four conductors and strain-relief route to neck boundary are not accepted by this port-only test.'],'outputs':{key:{'file':str(D/f'{key}.stl'),'sha256':sha(D/f'{key}.stl')} for key in ['imu-clamp-side-port-world','jst-sh4-receiving-world','jst-sh4-insertion-sweep-world']},'physicalFitVerified':False}
(D/'imu-side-port-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
