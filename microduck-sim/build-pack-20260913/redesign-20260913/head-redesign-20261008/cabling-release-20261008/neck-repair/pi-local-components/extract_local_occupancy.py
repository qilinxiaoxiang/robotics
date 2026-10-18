"""Local official drawing extraction only; no CAD or package-height inference."""
from pathlib import Path
import sys,json,math,hashlib
O=Path(__file__).resolve().parent;N=O.parent;H=N.parents[1]
sys.path.insert(0,str(N));from zero_vector_paths import paths
P={p['id']:p for p in paths};scale=(P[929]['bbox'][0]-P[923]['bbox'][0])/65;origin=[P[923]['bbox'][0],P[926]['bbox'][1]]
def hull(points):
 p=sorted(set((round(x,5),round(y,5)) for x,y in points))
 def cross(o,a,b):return(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 lo=[];hi=[]
 for q in p:
  while len(lo)>1 and cross(lo[-2],lo[-1],q)<=1e-7:lo.pop()
  lo.append(q)
 for q in reversed(p):
  while len(hi)>1 and cross(hi[-2],hi[-1],q)<=1e-7:hi.pop()
  hi.append(q)
 return [list(x) for x in lo[:-1]+hi[:-1]]
def polygon(ids):return hull([[(q[k]-origin[k])/scale for k in range(2)] for i in ids for seg in P[i]['segments'] for q in seg])
def distance(p,a,b):
 v=[b[k]-a[k] for k in [0,1]];l=sum(x*x for x in v);t=max(0,min(1,sum((p[k]-a[k])*v[k] for k in [0,1])/l)) if l else 0
 return math.dist(p,[a[k]+t*v[k] for k in [0,1]])
def inside_expanded(p,poly,r):
 pos=neg=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  q=(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]);pos|=q>1e-8;neg|=q< -1e-8
 return not(pos and neg) or min(distance(p,a,b) for a,b in zip(poly,poly[1:]+poly[:1]))<=r
# Each list is one visually identified closed component contour; hull only closes
# duplicated near-coincident SVG endpoints. Do not hull different components.
groups=[
 ('left-upper-rectangular-component',[275,304,282],3.8),
 ('left-square-component',[254,273,293],3.8),
 ('left-lower-rectangular-component',[287,288,289,292],3.8),
 ('octagonal-component',[297,298,301,302,303,370,392,393],3.8),
 ('middle-passive-a',[295,296,300,365],3.8),
 ('middle-passive-b',[367,368,369,391],3.8),
 ('lower-passive-a',[341,342,343,344],3.8),
 ('lower-passive-b',[329,330,331,332],3.8),
 ('lower-passive-c',[335,336,337,338],3.8),
 ('indicator-body-and-outline',list(range(310,317))+list(range(323,327)),3.8),
 ('bottom-usb-edge-context',[225,226,286],3.8),
 ('csi-connector-body-conservative-hull',list(range(423,435)),2.2),
 ('csi-connector-pins-conservative-hull',list(range(345,365))+list(range(371,390))+list(range(394,421)),2.2),
]
rows=[]
for key,ids,height in groups:
 poly=polygon(ids);rows.append({'key':key,'sourceSvgPathIndices':ids,'footprintOfficialXYMm':poly,'boundsOfficialXYMm':[[min(q[k] for q in poly) for k in [0,1]],[max(q[k] for q in poly) for k in [0,1]]],'xyExpansionMm':.1,'heightAbovePcbMm':height,'heightBasis':'Compatible CSI manufacturer 2.00mm nominal +0.20mm receiving allowance; not installed-part measurement' if key.startswith('csi') else 'Existing conservative 3.8mm retained only over this actual drawn component footprint; unknown actual height','identity': 'CSI connector and terminals' if key.startswith('csi') else 'Drawing/photo component outline; package reference and actual height not identified'})
contact=H/'camera-ribbon-repair/fixed-pose-local-bend/pi-component-contact-classification.json';j=json.loads(contact.read_text());vv=j['verticesOfficialXYHeight']
for row in rows:
 row['intersectionVerticesProjectedInsideExpandedFootprint']=sum(inside_expanded(v[:2],row['footprintOfficialXYMm'],.1) for v in vv)
 row['intersectionVerticesWithinReceivingPrism']=sum(v[2]<=row['heightAbovePcbMm'] and inside_expanded(v[:2],row['footprintOfficialXYMm'],.1) for v in vv)
# Coverage check: all drawing line samples in the replacement window must be
# assigned to a footprint, except the explicitly identified mounting circles.
uncovered=set();tested=0
for q in paths:
 if q['id']>=922 or q['id'] in {472,439,421,422,440,435,308,309}:continue
 for aa,bb in q['segments']:
  length=math.dist(aa,bb)/scale
  for i in range(max(1,math.ceil(length/.05))+1):
   t=i/max(1,math.ceil(length/.05));v=[((1-t)*aa[k]+t*bb[k]-origin[k])/scale for k in [0,1]]
   if not(55.7<=v[0]<=64.2 and 10.2<=v[1]<=25.3):continue
   tested+=1
   if not any(inside_expanded(v,r['footprintOfficialXYMm'],.1) for r in rows):uncovered.add(q['id'])
assert not uncovered,uncovered
report={'acceptedHardwareFit':False,'purpose':'Replace only the locally investigated full component-box portion with source-supported distinct receiving footprints, retaining unknown component heights. Actual route/static acceptance belongs to owner.','drawingUrl':'https://pip-assets.raspberrypi.com/categories/592-raspberry-pi-zero-w/documents/RP-008367-DS-1-raspberry-pi-zero-w-mechanical-drawing.pdf','connectorHeightUrl':'https://www.amphenol-cs.com/product/f32q1a7h111022.html','sourceDrawingTitle':'Raspberry Pi Zero W mechanical drawing RP-008367-DS-1','svgOriginPt':origin,'svgPointsPerMm':scale,'coordinateConvention':'Official drawing XY: PCB left/top straight edges as origin, X along65mm, Y along30mm. Height measured from component-side PCB surface.','localReplacementWindowOfficialXYMm':[[55.7,10.2],[64.2,25.3]],'replacementInstructions':'Outside this XY window preserve existing full receiving box and all explicit meshes. Inside window intersect each footprint expanded by0.1mm with window, then extrude from PCB surface to indicated height. Keep PCB, solder, header, connector latch/engagement and every actual obstacle separately; this does not authorize subtraction from physical meshes.','footprintMethod':'Each component gets its own convex hull of its drawn perimeter endpoints; octagonal component stays octagonal. CSI multi-line body/pins conservatively enclosed separately. Not a hull across components.','xyAllowanceBasis':'0.1mm design receiving allowance for line stroke/registration, not manufacturer tolerance.','rows':rows,'drawingOutlineCoverage':{'testedSamples':tested,'maxLineSampleStepMm':.05,'unassignedPathIndices':sorted(uncovered),'excludedMountingCirclePathIndices':[472,439,421,422,440,435,308,309]},'contactProjectionDiagnostic':{'vertices':len(vv),'boundary':'Vertex projection is only localization, not proof of no triangle/prism intersection; owner must do actual solid check.','minimumHeightMm':min(v[2] for v in vv),'unknownFootprintsTouched':[r['key'] for r in rows if r['heightAbovePcbMm']==3.8 and r['intersectionVerticesProjectedInsideExpandedFootprint']>0]},'limitations':['No exact local component can be established from these sources to exceed3.421mm. Several drawn footprints overlap the projection and retain3.8mm until physical package height evidence exists; no blanket clearance claim.','Photo confirms populated small parts and connector locations but is oblique and uncalibrated for height; cannot certify maximum package height.','Manufacturer height2.00 applies to named compatible connector; official Pi compatibility and installed connector identity remain separately sourced by main review.','Camera route is frozen. This evidence does not change route or printing geometry.'],'sourceHashes':{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),N/'zero_vector_paths.py',N/'zero-w-official-mechanical.svg',N/'zero-w-official-mechanical.pdf',H/'camera-ribbon-repair/sources/received-standard-mini200-20261008.jpg',contact]}}
(O/'local-occupancy.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'output':str((O/'local-occupancy.json').resolve()),'rows':[(r['key'],r['boundsOfficialXYMm'],r['intersectionVerticesWithinReceivingPrism']) for r in rows]},indent=2))
