from pathlib import Path
import cadquery as cq,json,hashlib
D=Path(__file__).resolve().parent;SIM=next(p for p in D.parents if p.name=='microduck-sim');A=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/trunk-imu'
def cyl(x0,x1,y,z,r):return cq.Solid.makeCylinder(r,x1-x0,cq.Vector(x0,y,z),cq.Vector(1,0,0))
def box(lo,hi):return cq.Solid.makeBox(*(hi[i]-lo[i] for i in range(3)),cq.Vector(*lo))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
h=cq.importers.importStep(str(D/'imu-clamp-side-port-world.step')).val();c=cq.importers.importStep(str(A/'imu_rear_cover.step')).val();seats=[]
for y in [-10.16,10.16]:
 for z in [6.11,23.89]:
  # Four source2.5mm PCB holes: flat rear support,1.0mm radius pin.
  pad=cyl(-53,-52.5,y,z,2.2);pin=cyl(-55.2,-52.9,y,z,1)
  h=h.fuse(pad).fuse(pin)
  # Annular stop meets only the plated mounting-hole surround.
  # 0.20mm axial receiving clearance against the component-side PCB face.
  ring=cyl(-61.5,-54.83,y,z,2.2).cut(cyl(-61.6,-54.7,y,z,1.4))
  c=c.fuse(ring)
  seats.append({'worldY':y,'worldZ':z,'sourceHoleDiameterMm':2.5,'pinDiameterMm':2,'radialClearanceMm':.25,'supportXmm':-53,'rearStopXmm':-54.83,'nominalPCBComponentFaceXmm':-54.63,'axialFreePlayMm':.2,'supportOuterDiameterMm':4.4,'stopInnerDiameterMm':2.8})
# One integral rear-cover tie land supports the low-current leads after the port bend.
# No additional screw/printed part;4.8x1.2 receiving strap threads after closure.
c=c.fuse(box([-62.6,-33,23.5],[-61.4,-18,31.5]))
c=c.fuse(box([-61.5,-29.6,25.1],[-57.2,-25.4,29.9]))
for y in [-31,-24]:c=c.cut(box([-63,y-.8,24.5],[-61,y+.8,30.5]))
for y in [-17.5,17.5]:
 for z in [4,26]:c=c.cut(cyl(-63,-61,y,z,1.1))
for name,obj in [('imu-clamp-retained-world',h),('imu-cover-retained-world',c)]:
 assert obj.isValid() and len(obj.Solids())==1,(name,len(obj.Solids()))
 cq.exporters.export(obj,str(D/f'{name}.step'));cq.exporters.export(obj,str(D/f'{name}.stl'),tolerance=.02,angularTolerance=.1)
r={'scope':'Rigid PCB capture within existing IMU holder and4-screw cover; source mounting-hole support only','geometryValid':True,'parts':[{ 'key':k,'file':str(D/f'{n}.stl'),'step':str(D/f'{n}.step'),'sha256':sha(D/f'{n}.stl'),'bodyCount':1} for k,n in [('imu_clamp','imu-clamp-retained-world'),('imu_cover','imu-cover-retained-world')]],'seats':seats,'componentHeightSource':'Official4754 STL PCB component face nativeZ1.63, transformedworldX−54.63','sourceHashes':{str(p):sha(p) for p in [D/'imu-clamp-side-port-world.step',A/'imu_rear_cover.step',D/'sources/bno085.brd',D/'sources/bno085.stl',Path(__file__)]},'assemblyOrder':['Place unconnected BNO085 board from world−X onto the four locating pins; source component side faces−X.','Connect CONN4 from world−Y through the repaired aperture, with rear cover still off.','Seat the original four-screw rear cover from−X; annular stops locate only PCB mounting-hole surrounds.','Fasten original four rear-cover screws; check0.2mm maximum nominal axial freeplay and no component compression.'],'strainRelief':{'type':'Integral rear-cover tie land and4.8x1.2mm strap receiving slots','landBoundsMm':[[-62.6,-33,23.5],[-61.4,-18,31.5]],'wireSupportPlaneXmm':-57.2,'wireBackXmm':-56.935,'nominalGapMm':.265,'strapThreading':'After the cover is seated, pass a nylon tie through the two open slots around the four leads; tighten only to retain insulation without crushing it. No new screw or separate printed part.','strapSupplyVerified':False},'staticAndInsertionAccepted':False,'physicalFitVerified':False}
(D/'imu-retention.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'parts':r['parts'],'seats':seats}))
