"""Lightweight endpoint/arclength planning; no mesh library or acceptance claim."""
from pathlib import Path
import json,math,hashlib,argparse,struct
D=Path(__file__).resolve().parent;H=D.parent.parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--pose',type=Path,default=H/'camera-ribbon-repair/saved-pose-pair-checks.json')
parser.add_argument('--output',type=Path,default=D/'vertical-usb-length-plan.json')
parser.add_argument('--side-exit',action='store_true',help='Turn USB-C lead toward +Y before the rear run, avoiding the IMU clamp')
parser.add_argument('--pi-edge-mesh',type=Path,help='Optional numerical reconciliation to the authoritative exported PCB edge plane; shifts exceeding0.0001mm are rejected')
args=parser.parse_args()
posefile=args.pose;p=json.loads(posefile.read_text());cfile=D.parent/'full-harness/published-usbc-verification.json';o=json.loads(cfile.read_text())
def add(a,b):return [x+y for x,y in zip(a,b)]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def mul(a,s):return [x*s for x in a]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(a):return math.sqrt(dot(a,a))
def unit(a):return mul(a,1/norm(a))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
alignment=None
if args.pi_edge_mesh:
 b=args.pi_edge_mesh.read_bytes();vertices=[]
 n=struct.unpack('<I',b[80:84])[0] if len(b)>=84 else -1
 if len(b)==84+50*n:
  for i in range(n):
   row=struct.unpack_from('<12fH',b,84+50*i)
   vertices.extend(row[j:j+3] for j in (3,6,9))
 else:
  vertices=[tuple(map(float,line.split()[1:4])) for line in b.decode().splitlines() if line.strip().startswith('vertex ')]
 assert vertices,'Missing PCB edge vertices'
 original=p['usbShoulderWorldMm'];axis=unit(p['usbOutwardAxis'])
 shift=max(dot(sub(v,original),axis) for v in vertices)
 assert abs(shift)<=.0001,('Not numerical edge reconciliation',shift)
 alignment={'sourceMesh':str(args.pi_edge_mesh.resolve()),'sourceSha256':hashlib.sha256(b).hexdigest(),'originalShoulderMm':original,'outwardShiftMm':max(0.,shift),'purpose':'Align the receiving shoulder to the exported PCB edge plane. This corrects source serialization noise; it is not a mechanical clearance or tolerance allowance.'}
 p['usbShoulderWorldMm']=add(original,mul(axis,max(0.,shift)))
def fillet_length(w,r):
 lengths=[norm(sub(b,a)) for a,b in zip(w,w[1:])];cuts=[];arcs=[]
 for i in range(1,len(w)-1):
  a,b=unit(sub(w[i],w[i-1])),unit(sub(w[i+1],w[i]));theta=math.acos(max(-1,min(1,dot(a,b))))
  if math.pi-theta<1e-7:raise ValueError('cusp')
  cuts.append(r*math.tan(theta/2));arcs.append(r*theta)
 for i,L in enumerate(lengths):
  if L<((cuts[i-1] if i else 0)+(cuts[i] if i<len(cuts) else 0))-1e-8:raise ValueError('overlappingfillets')
 return sum(lengths)-2*sum(cuts)+sum(arcs)
start=add(p['usbShoulderWorldMm'],mul(p['usbOutwardAxis'],25));t=p['usbOutwardAxis'];u=[-1,0,0];axis=unit(cross(t,u));radius=10;angle=math.acos(dot(t,u));center=add(start,mul(cross(axis,t),radius));v=sub(start,center);arcend=add(center,add(mul(v,math.cos(angle)),mul(cross(axis,v),math.sin(angle))));arcL=radius*angle;c=o['cableExitWorldMm'];ca=o['outwardAxis'];rows=[]
cArcEnd=add(c,add(mul(ca,10),[0,10,0]));cArcLength=5*math.pi
for span in range(25,81,5):
 tail=add(arcend,mul(u,span-arcL));mate=add(tail,mul(u,25));male=add(mate,mul(u,22.9))
 def route(extra):
  if args.side_exit:
   rear=male[0]-20-extra;w=[male,[rear,male[1],male[2]],[cArcEnd[0],30,cArcEnd[2]],cArcEnd]
   return fillet_length(w,10)+cArcLength,w
  rear=min(male[0],c[0])-12-extra;q=add(c,mul(ca,(rear-c[0])/ca[0]));w=[male,[rear,male[1],male[2]],q,c];return fillet_length(w,10),w
 L0,_=route(0);left,right=0.,100.
 if L0>102.5:rows.append({'scFlexibleMm':span,'possibleInThisFamily':False,'minimumACMm':L0});continue
 for i in range(45):
  mid=(left+right)/2
  if route(mid)[0]<102.5:left=mid
  else:right=mid
 L,w=route((left+right)/2);rows.append({'scFlexibleMm':span,'possibleInThisFamily':True,'usbAFemaleCableExitMm':tail,'usbAMatingPointMm':mate,'usbAMaleCableExitMm':male,'acWaypointsMm':w,'acExactLengthMm':L,'scExactArcMm':arcL,'scRemainingStraightMm':span-arcL,'bendRadiusMm':10})
out={'status':'length-only-plan-awaits-solid-check','sourcePose':str(posefile.resolve()),'sourcePoseSha256':hashlib.sha256(posefile.read_bytes()).hexdigest(),'sourceHashes':{str(cfile.resolve()):hashlib.sha256(cfile.read_bytes()).hexdigest(),str(Path(__file__).resolve()):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'piShoulderMm':p['usbShoulderWorldMm'],'piPlugTailMm':start,'piPlugOutwardAxis':t,'scFinalDirection':u,'rows':rows,'physicalSCFlexibleLengthKnown':False,'parameterRangeIsMeasured':False,'notes':'25–80mm is a deliberate engineering exploration interval, not a manufacturer tolerance. Continue adjustable-restraint development; exact supplied-cable acceptance needs a source-backed dimensional bound or compatible physical fit. No mesh collision or assembly acceptance from this calculation.'}
if args.side_exit:out['cEndArc']={'startMm':c,'incoming':ca,'outgoing':[0,1,0],'radiusMm':10,'lengthMm':cArcLength,'traversal':'reverse after acWaypoints'}
if alignment:
 out['pcbEdgeNumericalAlignment']=alignment;out['sourceHashes'][alignment['sourceMesh']]=alignment['sourceSha256']
args.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'spanCases':len(rows),'lengthSolutions':sum(r['possibleInThisFamily'] for r in rows),'piPlugTail':start,'candidateOnly':True}))
