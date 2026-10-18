from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'pack_populated_boards.py').read_text().split('pikeys=')[0])
import math
O=D/'pi-roof-mounts';posefile=D/'pi-front-up05-pose.json';Tp=np.array(json.loads(posefile.read_text())['piCurrentWorldDelta']);pifile=H/'camera-ribbon-repair/fixed-pose-local-bend/pi-spacer2-pose.json';piT=np.array(json.loads(pifile.read_text())['worldTransform']);hashes[str(posefile)]=sha(posefile);hashes[str(pifile)]=sha(pifile)
cap=load(O/'closed-cap-with-pi-bosses-world.stl');parts={}
for k in rows:
 if not(k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_'))):continue
 s=source(k)
 if k.startswith('gpio_pin_'):s=(s.transform(np.linalg.inv(piT)[:3])^mf.Manifold.cube([200,400,400]).translate([50.52,-200,-100])).transform(piT[:3])
 parts[k]=s.transform(Tp[:3])
parts['microB']=mf.Manifold.cube([6,13,25]).translate([63.01,2.4,146.0496]).transform(piT[:3]).transform(Tp[:3])
checks=[];fail=[]
def test(kind,a,b,label,offset=None,contact=False):
 ba=np.array(a.bounding_box()).reshape(2,3);bb=np.array(b.bounding_box()).reshape(2,3)
 v=0.0 if np.any(ba[1]<bb[0])or np.any(bb[1]<ba[0])else max(0,(a^b).volume())
 allowed=bool(contact and v<1e-4)
 row={'operation':kind,'pair':label,'offsetMm':offset,'volumeMm3':v,'intentionalSourcePlaneContact':allowed}
 checks.append(row)
 if v>1e-7 and not allowed:fail.append(row)
for dz in np.linspace(-15,0,61):
 for k,s in parts.items():test('prewired Pi moves up to roof bosses',s.translate([0,0,float(dz)]),cap,k,float(dz),k=='pi' and abs(dz)<1e-8)
for x,y in [[47.5,-30],[47.5,28],[70.5,-30],[70.5,28]]:
 tool=mf.Manifold.cylinder(24.4,2,circular_segments=32).translate([x,y,105])
 test('M2x6 driver access from open underside',tool,cap,str([x,y]))
 for k,s in parts.items():test('M2x6 driver access from open underside',tool,s,str([x,y])+'/'+k)
 nut=mf.Manifold.cylinder(1.6,4/math.sqrt(3),circular_segments=6).translate([x,y,134.4])
 for dx in np.linspace(-10,0,41):test('M2 nut side-load before Pi installation',nut.translate([float(dx),0,0]),cap,str([x,y]),float(dx))
r={'status':'PASSED_LOCAL_DIGITAL_ASSEMBLY'if not fail else'FAILED_LOCAL_ASSEMBLY','passed':not fail,'complete':True,'sourceHashes':hashes,'checks':checks,'failures':fail,'scope':'Cap on bench: side-load four nuts, preconnect used GPIO/MicroUSB plugs to Pi, lift populated Pi15mm into underside seats, drive four M2x6 before face/audio closure. Cap-to-whole-robot closure and flexible tails excluded.','physicalFitVerified':False,'connectorAssumption':'Same source-bound16.79mm female class hardware bound. 18mm extra air is not included as rigid hardware.','fastening':{'screw':'M2x6','quantity':4,'nut':'M2','nutAFMm':4,'nutHeightMm':1.6,'boardStackMm':1.6,'nutFloorMm':2,'blindBoreDepthMm':5,'screwTipEndZMm':136.7,'blindBoreEndZMm':137.3},'sampling':{'piTranslationMm':.25,'nutTranslationMm':.25},'physicalChecks':['Nut sliding fit and printed wall integrity','Confirm owned plug plastic/wire tail clears while cap closes']}
(O/'pi-mount-assembly-check.json').write_text(json.dumps(r,indent=2));print(json.dumps({'status':r['status'],'checks':len(checks),'failures':fail[:20],'failureCount':len(fail)},indent=2))
