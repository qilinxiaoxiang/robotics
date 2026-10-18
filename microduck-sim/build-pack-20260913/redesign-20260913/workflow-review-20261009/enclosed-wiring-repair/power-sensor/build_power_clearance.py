"""Native tangent line/arc sweeps for the body-side I2C branch only."""
from pathlib import Path
import cadquery as cq,math,json,hashlib
D=Path(__file__).resolve().parent

def vec(q):return cq.Vector(*q)
def sub(a,b):return [a[i]-b[i] for i in range(3)]
def add(a,b):return [a[i]+b[i] for i in range(3)]
def mul(a,s):return [x*s for x in a]
def norm(a):return math.sqrt(sum(x*x for x in a))
def unit(a):return mul(a,1/norm(a))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def fillet_path(ps,r):
 edges=[];last=ps[0];segments=[]
 for a,p,b in zip(ps,ps[1:],ps[2:]):
  u=unit(sub(p,a));v=unit(sub(b,p));theta=math.acos(sum(x*y for x,y in zip(u,v)));d=r*math.tan(theta/2)
  assert d*2<min(norm(sub(p,a)),norm(sub(b,p)))
  start=sub(p,mul(u,d));end=add(p,mul(v,d));axis=unit(cross(u,v));normal=cross(axis,u);center=add(start,mul(normal,r));rv=sub(start,center);perp=cross(axis,rv)
  mid=add(center,add(mul(rv,math.cos(theta/2)),mul(perp,math.sin(theta/2))))
  edges+=[cq.Edge.makeLine(vec(last),vec(start)),cq.Edge.makeThreePointArc(vec(start),vec(mid),vec(end))]
  segments += [{'type':'line','start':last,'end':start},{'type':'arc','start':start,'mid':mid,'end':end,'radiusMm':r}];last=end
 edges.append(cq.Edge.makeLine(vec(last),vec(ps[-1])));segments.append({'type':'line','start':last,'end':ps[-1]})
 return cq.Wire.assembleEdges(edges),segments
rows=[]
# Power main corridor begins beyond the converter top edge, not at a fabricated pad plane.
# It is a pair before distribution; downstream branch topology stays separate.
for net,y0,y1 in [('5V',-10.5,-7.6),('GND',.2,-3.8)]:
 y2=y1
 points=[[-35.5,y0,3.0],[-34.0,y1,17],[-34.0,y1,36.7],[-12,y2,36.7],[6,y2,48],[6,y2,55]]
 path,segs=fillet_path(points,6)
 plane=cq.Plane(origin=vec(points[0]),normal=vec(sub(points[1],points[0])))
 tube=cq.Workplane(plane).circle(1.6).sweep(cq.Workplane('XY').newObject([path]),isFrenet=False).val();assert tube.isValid()
 key='power_'+net.lower();stl=D/(key+'-clearance-world.stl');step=D/(key+'-clearance-world.step')
 cq.exporters.export(tube,str(step));cq.exporters.export(tube,str(stl),tolerance=.01,angularTolerance=.1)
 rows.append({'key':key,'net':net,'file':str(stl),'sha256':hashlib.sha256(stl.read_bytes()).hexdigest(),'nativeStep':str(step),'routeSections':segs,'diameterMm':3.2,'diameterBasis':'Conservative16AWG receiving allowance; existing stock insulation diameter not established','minimumBendRadiusMm':6,'bendBasis':'CAD routing allowance; not manufacturer cable bend rating','lengthMm':path.Length(),'from':points[0],'fromStatus':'Outside-board receiving interface,2mm beyond top board edge; not a registered solder point','toFreeNeckBoundary':points[-1],'headEndpointAccepted':False,'status':'Body corridor trial only; distribution, pad solder lead and head continuation excluded'})
(D/'power-clearance-routes.json').write_text(json.dumps({'scope':'Stationary body to open neck boundary: four I2C conductors and paired power corridor; actual solder lead/distribution/head not accepted','parts':rows,'sourceHashes':{str(D/'bno085-endpoint-registration.json'):hashlib.sha256((D/'bno085-endpoint-registration.json').read_bytes()).hexdigest(),str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'wholeHarnessAccepted':False},indent=2)+'\n')
print(json.dumps([{'key':r['key'],'length':r['lengthMm']} for r in rows]))
