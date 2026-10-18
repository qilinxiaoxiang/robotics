"""P5/P6: external SC0727 -> USB-A mating pair -> Adafruit4472, unchanged topology.
Source geometry read-only. Receiving hypotheses are explicit, never measurements.
"""
from pathlib import Path
import json,base64,hashlib,sys,io,numpy as np,trimesh,manifold3d as mf
from scipy.optimize import brentq
D=Path(__file__).resolve().parent;U=D.parent;H=U.parent;C=H/'curved-head';G=H.parent/'leg-guide-20261006';sourceHashes={}
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def tri(s):
 q=s.to_mesh();return trimesh.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True)
def load(p):
 b=p.read_bytes();sourceHashes[str(p.relative_to(H))]=hashlib.sha256(b).hexdigest();return trimesh.load(io.BytesIO(b),file_type='stl',force='mesh')
def hits(a,b):
 x=np.array(a.bounding_box()).reshape(2,3);y=np.array(b.bounding_box()).reshape(2,3)
 if np.any(x[0]>=y[1]) or np.any(y[0]>=x[1]):return 0.
 return max(0,float((a^b).volume()))
def box(c,s):return trimesh.creation.box(s).apply_translation(c)
sourceHashes['../leg-guide-20261006/full-build-data.json']=hashlib.sha256((G/'full-build-data.json').read_bytes()).hexdigest()
data=json.loads((G/'full-build-data.json').read_text());config=json.loads((H/'viewer-candidate.json').read_text());obs={}
for p in data['parts']:
 k=p['key']
 if k in config['removedParts']:continue
 if k in config['replacementMeshes']:m=load(H/config['replacementMeshes'][k])
 else:m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
 obs[k]=man(m)
for p in config['additionalParts']:
 if p['key'] in ['pi_usb_receiving','openrb_usb_receiving'] or str(p['mesh']).startswith('usb-access/full-harness/'):continue
 obs[p['key']]=man(load(H/p['mesh']))
# PUBLISHED_CONNECTOR_FROM_SOURCE_SHOULDER
# Build from immutable source local dimensions, never rescale another generated
# receiving mesh: root check_usb publishes this output back to its legacy path.
SIM=H.parent.parents[1]
sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'))
from assembly_fk import fk
bodyPoses,_=fk();bodyPose=np.asarray(bodyPoses['jaw_soft'])
import os
for sourcePath in [SIM/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py',SIM/'hardware-design-20260912/whole-robot-20260912/electrical/head-layout/build_head_electronics.py']:
 sourceHashes[os.path.relpath(sourcePath,H)]=hashlib.sha256(sourcePath.read_bytes()).hexdigest()
layoutPath=C/'curved-layout.json';sourceHashes[str(layoutPath.relative_to(H))]=hashlib.sha256(layoutPath.read_bytes()).hexdigest()
T=np.asarray(json.loads(layoutPath.read_text())['transformsFromGuideWorld']['openrb'])@bodyPose
axis=T[:3,:3]@np.array([0.,0,1.]);axis/=np.linalg.norm(axis)
shoulder=(T@np.array([27.2,0,16.1,1.]))[:3];ctail=shoulder+axis*27
plug=box([27.2,0,29.6],[7,12,27]).apply_transform(T)
assert abs(np.ptp(plug.vertices@axis)-27)<1e-6
plug.export(D/'openrb-usb-c-published-envelope-world.stl')
piPlug=load(C/'zero_w_usb_moulding-world.stl');ptail=piPlug.bounds.mean(0);ptail[2]=piPlug.bounds[1,2]
rows=[];ps=man(plug)
for off in np.arange(30,-.001,-.25):
 q=ps.translate(axis*off);hh={k:hits(q,o) for k,o in obs.items() if hits(q,o)>1e-4};rows.append({'offsetMm':float(off),'intersectionsMm3':hh})
report={'officialDrawingUrl':'https://cdn-shop.adafruit.com/product-files/4472/4472_PCM-0207_TYPE_C_M-USB2.0_A_M__.pdf','officialDrawingSha256':hashlib.sha256((D/'adafruit-4472-drawing.pdf').read_bytes()).hexdigest(),'axialBodyPlusStrainReliefMm':27,'bodyOnlyMm':22,'strainReliefMm':5,'maleMetalLengthMm':6.7,'seatedShoulderWorldMm':shoulder.tolist(),'outwardAxis':axis.tolist(),'cableExitWorldMm':ctail.tolist(),'receivingCrossSectionMm':[7,12],'crossSectionBoundary':'12mm width from drawing;7mm thickness remains inherited receiving assumption, not dimensioned in this drawing','legacyAxialLengthMm':15,'connectorInsertion':{'stepMm':.25,'samples':rows,'passed':not any(r['intersectionsMm3'] for r in rows)},'sourceHashes':sourceHashes,'physicalFitVerified':False}
(D/'published-usbc-verification.json').write_text(json.dumps(report,indent=2)+'\n');print('PUBLISHED_C',report['connectorInsertion']['passed'], 'exit',ctail.tolist(),flush=True)
# Exact circular arcs; repeated junction samples are removed before tube lofting.
def arc(p,t,u,r):
 theta=np.arccos(np.clip(t@u,-1,1));a=np.cross(t,u);a/=np.linalg.norm(a);center=p+np.cross(a,t)*r;v=p-center;aa=np.linspace(0,theta,max(2,int(np.ceil(r*theta/.25)))+1);return np.array([center+v*np.cos(q)+np.cross(a,v)*np.sin(q) for q in aa]),r*theta
sc=[];p=ptail.copy();t=np.array([0.,0,1.]);aa,L=arc(p,t,np.array([-1.,0,0]),10);sc.extend(aa);p=aa[-1];t=np.array([-1.,0,0])
for u in [np.array([0.,1,0]),np.array([-1.,0,0]),np.array([0.,-1,0]),np.array([-1.,0,0])]:
 aa,l=arc(p,t,u,10);sc.extend(aa[1:]);L+=l;p=aa[-1];t=u
p2=p+t*(80-L);sc.extend(np.linspace(p,p2,max(2,int(np.ceil((80-L)/.25)))+1)[1:]);sc=np.array(sc);femaleTail=p2;mate=femaleTail+[-25,0,0];maleTail=mate+[-22.9,0,0]
def rounded(wp,r):
 cuts=[]
 for i in range(1,len(wp)-1):
  u=wp[i]-wp[i-1];u/=np.linalg.norm(u);v=wp[i+1]-wp[i];v/=np.linalg.norm(v);theta=np.arccos(np.clip(u@v,-1,1));d=r*np.tan(theta/2);a=wp[i]-u*d;b=wp[i]+v*d;cuts.append((a,b,u,v,d))
 for i in range(len(wp)-1):
  need=(cuts[i-1][4] if i else 0)+(cuts[i][4] if i<len(cuts) else 0)
  if np.linalg.norm(wp[i+1]-wp[i])+1e-7<need:raise ValueError('overlapping fillets')
 pts=[wp[0]];L=0.;prev=wp[0]
 for a,b,u,v,d in cuts:
  le=np.linalg.norm(a-prev)
  if le>1e-8:pts.extend(np.linspace(prev,a,max(2,int(np.ceil(le/.25)))+1)[1:])
  L+=le;aa,l=arc(a,u,v,r);pts.extend(aa[1:]);L+=l;prev=b
 le=np.linalg.norm(wp[-1]-prev);pts.extend(np.linspace(prev,wp[-1],max(2,int(np.ceil(le/.25)))+1)[1:]);return np.array(pts),L+le
# Use actual published shoulder-to-shoulder length, subtract both moulding runs.
acTarget=152.4-22.9-27
best=None
for rear in [-48,-49,-50,-51,-52]:
 for r in [12.,11.,10.]:
  def ac(yy):
   q=ctail+axis*((ctail[0]-rear)/(-axis[0]));q[1]=yy
   wp=np.array([maleTail,[rear,maleTail[1],maleTail[2]],[rear,yy,maleTail[2]],q,[rear,0,q[2]],ctail])
   return (*rounded(wp,r),wp)
  # The duplicate-X top first corner cannot be collinear; handle feasible lengths
  # by finite samples and bracket only consecutive valid candidates.
  val=[]
  for y in np.arange(20,46,.5):
   try:a,ll,w=ac(y);val.append((y,ll-acTarget))
   except (ValueError,AssertionError):continue
  for (y0,f0),(y1,f1) in zip(val,val[1:]):
   if f0*f1<=0:
    yy=brentq(lambda y:ac(y)[1]-acTarget,y0,y1);ap,ll,wp=ac(yy);best=(ap,ll,wp,r,rear,yy);break
  if best:break
 if best:break
if not best:raise RuntimeError('No valid rear-side cable loop in finite search')
acpoints,acLength,acWp,acRadius,rear,yy=best
# Swept round cables. Parallel-transport section frame avoids artificial twists.
def tube(points,diameter):
 points=np.array(points);keep=np.r_[True,np.linalg.norm(np.diff(points,axis=0),axis=1)>1e-7];points=points[keep];t=np.gradient(points,axis=0);t/=np.linalg.norm(t,axis=1)[:,None];
 if np.allclose(points[0],ptail):t[0]=[0,0,1]
 verts=[];a=np.array([0.,1,0]);prev=None
 for p,tt in zip(points,t):
  if prev is not None:a=prev-tt*(prev@tt)
  else:a=a-tt*(a@tt)
  if np.linalg.norm(a)<1e-6:a=np.cross(tt,[1,0,0])
  a/=np.linalg.norm(a);b=np.cross(tt,a);prev=a.copy()
  for q in np.linspace(0,2*np.pi,16,endpoint=False):verts.append(p+diameter/2*(a*np.cos(q)+b*np.sin(q)))
 faces=[]
 for i in range(len(points)-1):
  for j in range(16):a=i*16+j;b=i*16+(j+1)%16;faces.extend([[a,b,b+16],[a,b+16,a+16]])
 verts.extend([points[0],points[-1]]);c0=len(verts)-2;c1=c0+1
 for j in range(16):faces.extend([[c0,(j+1)%16,j],[c1,(len(points)-1)*16+j,(len(points)-1)*16+(j+1)%16]])
 m=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(m);assert m.is_watertight;return m
sm=tube(sc,3.5);am=tube(acpoints,4.5);fm=box((femaleTail+mate)/2,[25,20,12]);mm=box((mate+maleTail)/2,[22.9,20,12]);cables={'sc0727_external_cable':sm,'adafruit4472_external_cable':am,'usb_a_female_receiving':fm,'usb_a_male_receiving':mm,'openrb_usb_c_published':plug,'pi_usb_receiving':piPlug};checks={}
for k,m in cables.items():
 s=man(m);checks[k]={n:hits(s,o) for n,o in obs.items() if hits(s,o)>1e-4};m.export(D/(k+'-world.stl'))
print('HARNESS',acLength,'radius',acRadius,'rear',rear,'Y',yy,'hits',checks,flush=True)
# Intermediate USB-A mating after both board plugs are seated. Male approaches
# along -X and is advanced+X15mm, with its loose cable unrestrained until mating.
mateRows=[];fmSolid=man(fm)
for d in np.arange(15,-.001,-.25):
 q=man(mm).translate([-d,0,0]);hh={n:hits(q,o) for n,o in obs.items() if hits(q,o)>1e-4};mateRows.append({'unmatedOffsetMm':float(d),'intersectionsMm3':hh})
report={'status':'conditional-external-harness-receiving-candidate','topology':'Pi Zero W Micro-B data -> existing SC0727 femaleUSB-A -> existing4472 maleUSB-A -> OpenRB USB-C; GPIO powersPi. No topology change.','manufacturerSearch':{'checked':'2026-10-08','SC0727OfficialProductPage':'80mm length only; no endpoint definition or mould drawing linked','officialPipSearches':[{'url':'https://pip.raspberrypi.com/search?q=SC0727','result':'No results found'},{'url':'https://pip.raspberrypi.com/search?q=Micro+USB+Male','result':'No results found'}],'boundary':'This finite public-source search does not prove all manufacturer documentation unavailable. No substitute cable dimensions are claimed.'},'sourceReferences':[{'url':'https://www.raspberrypi.com/products/micro-usb-male-to-usb-a-female-cable/','fact':'SC0727 nominal80mm; manufacturer page does not define endpoints of that length or overmould dimensions'},{'url':'https://www.adafruit.com/product/4472','fact':'nominal6in/15.2cm, cableOD4.5mm'},{'url':'https://cdn-shop.adafruit.com/product-files/4472/4472_PCM-0207_TYPE_C_M-USB2.0_A_M__.pdf','fact':'L between metal/overmould shoulder planes;A moulding22.9mm,C moulding27mm incl5mmstrainrelief'}],'lengthAccounting':{'sc0727NominalMm':80,'sc0727ModeledFlexibleSpanMm':80,'sc0727LengthInterpretationVerified':False,'adafruitNominalShoulderToShoulderMm':152.4,'adafruitAMouldingMm':22.9,'adafruitCMouldingMm':27,'adafruitModeledFlexibleSpanMm':acLength,'adafruitLengthReading':'102.5mm =152.4−22.9−27; drawing L arrow endpoints inspected. Actual received length/tolerance still unmeasured.'},'receivingAssumptions':{'sc0727CableDiameterMm':3.5,'sc0727FemaleBodyMm':[25,20,12],'adafruitAMouldingCrossSectionMm':[20,12],'adafruitCMouldingCrossSectionMm':[12,7],'sc0727BendRadiusMm':10,'adafruitBendRadiusMm':acRadius,'manufacturerMinimumBendRadiusKnown':False,'physicalDimensionsMeasured':False},'geometry':{'piCableExitMm':ptail.tolist(),'usbCCableExitMm':ctail.tolist(),'usbAMatingPlanePointMm':mate.tolist(),'usbAAxis':[1,0,0],'usbAFemaleCableExitMm':femaleTail.tolist(),'usbAMaleCableExitMm':maleTail.tolist(),'acWaypointsMm':acWp.tolist(),'scCenterlineMm':sc.tolist(),'acCenterlineMm':acpoints.tolist()},'staticIntersectionsMm3':checks,'intermediateUsbAMating':{'stepMm':.25,'samples':mateRows,'passed':not any(r['intersectionsMm3'] for r in mateRows)},'assemblyOrder':['Complete internal face/FFC and cap fastening with both external USB cables unplugged.','Insert SC0727 Micro-B from above using the verified top entry corridor. Keep its USB-A female end free.','Insert complete27mm4472 USB-C from behind along verified axis. Keep its USB-A male end free.','Shape both loose cables around the declared radius guides without tension; bring USB-A male into free female body before fastening any cable restraint.','Only after final connector seating, install removable restraint; do not use USB sockets to carry the free coupling weight.','To open cap, release restraints and unplug both external board connectors first; full harness is not carried through cap closure.'],'gates':{'staticSolidClear':not any(checks.values()),'entireHarnessPhysicalFit':False,'lengthAndOvermouldMeasurementRequired':True,'jointMotionChecked':False,'strainReliefComplete':False},'sourceHashes':sourceHashes,'physicalFitVerified':False,'manufacturingAccepted':False}
(D/'full-harness-report.json').write_text(json.dumps(report,indent=2)+'\n')
