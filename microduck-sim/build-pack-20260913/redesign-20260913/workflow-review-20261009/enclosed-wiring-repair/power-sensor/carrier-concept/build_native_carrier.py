from pathlib import Path
import cadquery as cq,json,hashlib
D=Path(__file__).resolve().parent

def box(a,b):return cq.Workplane('XY').box(*[b[i]-a[i]for i in range(3)]).translate(tuple((a[i]+b[i])/2 for i in range(3)))
features=[]
def add(name,a,b):features.append({'name':name,'kind':'box','min':a,'max':b});return box(a,b)
# Rear plane is 9.5 mm behind the PCB seating surface; pins project toward -X.
s=add('rear-spine',[-42,-16,-53.1],[-39,16,30.8])
s=s.cut(box([-43,-9,-24],[-38,9,22]))
s=s.cut(box([-40.6,-13.6,-51.1],[-38,13.6,-41.4]))
for y in [-1,1]:
 y0,y1=sorted([y*16,y*20]);
 for z in [-7,16]:s=s.union(add('source-frame-bridge',[-42,y0,z],[-20,y1,z+3]))
# Outer side cheeks reconnect original front screw/IMU webs around the new controller bay.
for ya,yb in [(-16.5,-11.8),(11.8,16.5)]:s=s.union(add('original-mount-side-cheek',[-21,ya,-7],[-18.9,yb,28]))
s=s.cut(box([-19.5,-17,-1.5],[-18.8,17,2.5]))
# Four corner bosses have PCB-safe contact rings, not a full board backing plate.
for y in [-10.25,10.25]:
 for z in [-31.75,29.75]:
  boss=cq.Workplane('YZ',origin=(-40,y,z)).circle(1.5 if z>0 else 2.5).extrude(5)
  boss=boss.union(cq.Workplane('YZ',origin=(-35,y,z)).circle(2.5).extrude(5.5))
  pilot=cq.Workplane('YZ',origin=(-34.7,y,z)).circle(.85).extrude(5.3)
  s=s.union(boss.cut(pilot));features.append({'name':'M2x6-controller-boss','kind':'axis-cylinder','axis':[1,0,0],'seat':[-29.5,y,z],'radius':2.5,'pilotDiameter':1.7,'pilotDepth':5.2,'screwThroughPCB':1.6,'nominalEngagement':4.4})
# The old crossmember is replaced by a lower shelf and two outboard load rails.
s=s.union(add('DFR-open-shelf',[-42,-16,-53.1],[-8,16,-51.1]))
for ya,yb in [(-16,-13.6),(13.6,16)]:s=s.union(add('DFR-edge-rail',[-42,ya,-53.1],[-8,yb,-41.4]))
# Open both X end faces for the labelled solder pads and insulated lead exits.
for x in [-34,-16]:s=s.cut(box([x-2.6,-17,-54],[x+2.6,17,-51.1]))
# Upper/lower tie slots are in the outer carrier ears, not over board components.
for x in [-34,-16]:
 for y in [-14.8,14.8]:s=s.cut(box([x-2.6,y-1.3,-49.6],[x+2.6,y+1.3,-42.4]))
s=s.cut(box([-15,-13.4,-54],[-7,13.4,-49.2]))
s=s.cut(box([-43,-13.4,-51.8],[-35,13.4,-49.2]))
pigtails=[]
for net,y in [('GND',-1.71),('VIN+',1.79)]:
 a=cq.Vector(-25.285,y,-34.89);b=cq.Vector(-25.285,y,-36.89);mid=cq.Vector(-24.1134271247462,y,-39.7184271247462);c=cq.Vector(-21.285,y,-40.89);e=cq.Vector(-7,y,-40.89)
 path=cq.Wire.assembleEdges([cq.Edge.makeLine(a,b),cq.Edge.makeThreePointArc(b,mid,c),cq.Edge.makeLine(c,e)])
 wire=cq.Workplane(cq.Plane(origin=a,normal=(0,0,-1))).circle(.8).sweep(cq.Workplane('XY').newObject([path]),isFrenet=True)
 assert wire.val().isValid();name='j4-'+('positive'if net=='VIN+'else'ground')+'-local-exit'
 cq.exporters.export(wire,str(D/(name+'.step')));cq.exporters.export(wire,str(D/(name+'.stl')),tolerance=.02,angularTolerance=.08)
 pigtails.append({'net':net,'mouthWorldMm':a.toTuple(),'outward':[0,0,-1],'straightMm':2,'bendRadiusMm':4,'receivingDiameterMm':1.6,'endWorldMm':e.toTuple(),'lengthMm':path.Length(),'step':str(D/(name+'.step')),'stl':str(D/(name+'.stl')),'scope':'Local terminal exit only, not complete power route or wire ampacity selection.'})
for net,y in [('VIN',10.9),('GND',.2),('VOUT',-10.5)]:
 bare=cq.Workplane('YZ',origin=(-11,y,-51.15)).circle(.65).extrude(1.6)
 insulated=cq.Workplane('YZ',origin=(-9.4,y,-51.15)).circle(1.6).extrude(6.4)
 lead=bare.union(insulated);assert lead.val().isValid();name='dfr-'+net.lower()+'-pad-exit'
 cq.exporters.export(lead,str(D/(name+'.step')));cq.exporters.export(lead,str(D/(name+'.stl')),tolerance=.02,angularTolerance=.08)
 pigtails.append({'net':'DFR_'+net,'padWorldMm':[-11,y,-50],'bareCopperDiameterMm':1.3,'insulationReceivingDiameterMm':3.2,'padCenterSourceUncertaintyMm':.8,'step':str(D/(name+'.step')),'stl':str(D/(name+'.stl')),'scope':'Short solder-side receiver through open end; not full power harness or an installed solder joint.'})
assert s.val().isValid();cq.exporters.export(s,str(D/'carrier-additions-world.step'));cq.exporters.export(s,str(D/'carrier-additions-world.stl'),tolerance=.04,angularTolerance=.1)
report={'pigtails':pigtails,'nativeFeatures':features,'nativeVolumeMm3':s.val().Volume(),'nativeSolids':len(s.solids().vals()),'openrbNativeToWorld':[[0,0,1,-29.5],[1,0,0,0],[0,1,0,-1],[0,0,0,1]],'openrbHoleEvidence':'Actual manufacturer PCB mesh: native hole axes X +/-10.25,Y +/-30.75,Z0..1.6, diameter2.5.','boardBackClearanceMm':9.5,'DFRBoundsMm':[[-40,-13,-50],[-10,13,-42]],'DFRReceivingClearanceMm':1.1,'DFRRetention':'Open end-face tray, side edge rails and removable narrow ties through rail slots. 1.1 mm bottom allowance receives an insulating liner; tie must avoid the module component/thermal face.','fasteners':'4 x M2x6 tapping screws at controller; 1.6 PCB +4.4 nominal pilot engagement,5.2 pilot depth. No available-stock claim.','manufacturingAccepted':False,'wholeAssemblyAccepted':False}
for name in ['carrier-additions-world.step','carrier-additions-world.stl']:report[name]={'sha256':hashlib.sha256((D/name).read_bytes()).hexdigest()}
(D/'native-carrier.json').write_text(json.dumps(report,indent=2));print(json.dumps({'solids':report['nativeSolids'],'volume':report['nativeVolumeMm3']}))
