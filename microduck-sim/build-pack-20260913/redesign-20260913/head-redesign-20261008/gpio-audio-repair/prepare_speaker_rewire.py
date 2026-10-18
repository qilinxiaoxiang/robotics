#!/usr/bin/env python3
"""Stdlib-only path proposal; no CAD imports or collision acceptance."""
import argparse,hashlib,json,math,xml.etree.ElementTree as ET
from pathlib import Path
D=Path(__file__).resolve().parent;H=D.parent

def add(a,b):return [x+y for x,y in zip(a,b)]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def mul(a,s):return [x*s for x in a]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(a):return math.sqrt(dot(a,a))
def unit(a):return mul(a,1/length(a))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def transform(T,p):return [sum(T[i][j]*p[j] for j in range(3))+T[i][3] for i in range(3)]
def rounded(wp,r,step=.25):
 bends=[]
 for i in range(1,len(wp)-1):
  u=unit(sub(wp[i],wp[i-1]));v=unit(sub(wp[i+1],wp[i]));c=max(-1,min(1,dot(u,v)));theta=math.acos(c)
  assert 1e-7<theta<math.pi-1e-7
  cut=r*math.tan(theta/2);a=sub(wp[i],mul(u,cut));b=add(wp[i],mul(v,cut));normal=unit(sub(v,mul(u,c)));center=add(a,mul(normal,r));e0=mul(sub(a,center),1/r)
  bends.append({'a':a,'b':b,'center':center,'e0':e0,'tangent':u,'angle':theta,'cut':cut,'radius':r})
 points=[wp[0]];segments=[];total=0
 def line(a,b):
  nonlocal total
  L=length(sub(b,a));total+=L;n=max(1,math.ceil(L/step));segments.append({'kind':'line','startMm':a,'endMm':b,'lengthMm':L})
  for j in range(1,n+1):points.append(add(a,mul(sub(b,a),j/n)))
 for i,b in enumerate(bends):
  prior=bends[i-1]['b'] if i else wp[0]
  assert length(sub(wp[i+1],wp[i]))>=b['cut']+(bends[i-1]['cut'] if i else 0), 'Fillets exceed segment'
  line(prior,b['a']);L=r*b['angle'];total+=L;n=max(1,math.ceil(L/step));segments.append({'kind':'arc','startMm':b['a'],'endMm':b['b'],'centerMm':b['center'],'radiusMm':r,'angleRadians':b['angle'],'lengthMm':L})
  for j in range(1,n+1):
   a=b['angle']*j/n;points.append(add(b['center'],mul(add(mul(b['e0'],math.cos(a)),mul(b['tangent'],math.sin(a))),r)))
  assert length(sub(points[-1],b['b']))<1e-8
 assert length(sub(wp[-1],wp[-2]))>bends[-1]['cut'];line(bends[-1]['b'],wp[-1]);return points,segments,total

def main(z,rear_drop):
 old=json.loads((D/'audio-design.json').read_text());T=[r[:] for r in old['terminalLocalToWorld']]
 for i,d in enumerate([16,0,z]):T[i][3]+=d
 brd=H/'curved-head/sources/adafruit-3006.brd';root=ET.parse(brd);el=next(e for e in root.findall('.//element') if e.get('name')=='X1');assert el.get('rot')=='R180'
 pkg=next(p for p in root.findall('.//package') if p.get('name')==el.get('package'));pads={p.get('name'):[float(el.get('x'))-float(p.get('x')),float(el.get('y'))-float(p.get('y'))] for p in pkg.findall('pad')}
 nets={ref.get('pad'):n.get('name') for n in root.findall('.//signal') for ref in n.findall('contactref') if ref.get('element')=='X1'}
 rows=[];tools=[]
 for i,p in enumerate(old['paths']):
  pin='2' if i==0 else '1';end=add(p['waypointsMm'][-1],[16,0,z]);start=p['waypointsMm'][0];x=start[0];rise=138.0+2.4*i
  # New R3 path: retain fixed speaker endpoint, reroute rear bay and lengthened
  # terminal lead. No previous path points or clearance result are reused.
  wp=[start,[x,.94,135.85],[x,-5-2*i,135.85],[x,-13-4*i,131.8+3.5*i],[32,end[1],end[2]],end]
  pts,segs,L=rounded(wp,3)
  axis=transform(T,[pads[pin][0],pads[pin][1],11.97]);assert abs(axis[1]-end[1])<1e-5
  rows.append({'id':'speaker-'+str(i),'net':nets[pin],'terminalPin':pin,'speakerPadWorldMm':start,'speakerPadPolarityBoundary':'Original pad1/pad2 pairing retained; XY was drawing-scaled, not a dimensioned or physical polarity proof. Verify the marked speaker polarity before soldering.','terminalMouthWorldMm':end,'terminalOutwardAxisWorld':[-1,0,0],'terminalWireInsertionAxisWorld':[1,0,0],'waypointsMm':wp,'analyticSegments':segs,'centerlineMm':pts,'analyticCenterlineLengthMm':L,'wireDiameterReceivingMm':1.5,'minimumCenterlineRadiusReceivingMm':3,'terminalStraightLeadMm':segs[-1]['lengthMm'],'stockCutLengthMm':None,'noCollisionClaim':True})
  tools.append({'terminalPin':pin,'net':nets[pin],'screwAxisXYWorldMm':axis[:2],'receivingTopWorldMm':axis,'outwardToolAxisWorld':[0,0,1],'driverInsertionWorld':[0,0,-1],'driverShaftDiameterReceivingMm':3,'shaftLengthReceivingMm':45,'handleDiameterReceivingMm':18,'handleLengthReceivingMm':60,'handleStartsAboveReceivingTopMm':45,'bladeWidthReceivingMm':2.5,'screwHeadActualRecessMm':None,'dimensionsBoundary':'Tool dimensions are proposed receiving space. Screw axis XY from Eagle pads; Z is terminal receiving top, not manufacturer screw-recess dimension.','assemblyState':'Loose amplifier on bench, cap/Pi/camera/OpenRB absent from tool corridor; soldered speaker held in a separate fixture.'})
 # Conservative lower bound between the two *sampled continuous* paths: any
 # point is <=step/2 from a sample; subtract maximum analytic sample spacing (0.25mm) once.
 maxstep=max(length(sub(a,b)) for p in rows for a,b in zip(p['centerlineMm'],p['centerlineMm'][1:]))
 samplemin=min(length(sub(a,b)) for a in rows[0]['centerlineMm'] for b in rows[1]['centerlineMm'])
 report={'status':'STDLIB_ENDPOINTS_AND_ROUNDED_ROUTE_PROPOSAL_ONLY','integrationReady':False,'cadRun':False,'rearDropSecondWireMm':rear_drop,'ampDeltaWorldMm':[16,0,z],'terminalLocalToWorld':T,'routes':rows,'terminalTools':tools,'wirePairDistanceLowerBoundMm':samplemin-.25-1.5,'wirePairCenterlineSampleMinMm':samplemin,'wirePairNegativeControl':rear_drop==0,'radiusBoundary':'R3 and OD1.5 are receiving assumptions; no vendor-specific minimum bending radius or actual available speaker-wire OD is certified.','sourceHashes':{str(p):sha(p) for p in [Path(__file__),D/'audio-design.json',D/'build_audio_candidate.py',D/'connector-dimensions.json',brd,H/'curved-head/sources/cms-30204-18x.pdf',D/'amp16-placement-stage.json']},'pending':['Exact tube-vs-current-cap/motors/FFC/static geometry','Clearances with +-0.5mm pad/mouth receiving shifts','Bare conductor engagement and strip length from selected terminal; route length excludes wire inside clamp and solder allowance','Prewired insertion, wire restraints, tool shaft/handle volumes and full closure','Actual marked speaker polarity and chosen wire stock'],'sequence':[{'id':1,'action':'Keep cap separate; solder two speaker pads on the loose speaker, with heat-sensitive retaining pieces absent. Identify actual + and - markings; neither amplifier output is ground.','tool':'Temperature-controlled soldering tool; no temperature or dwell specified without speaker soldering limits.'},{'id':2,'action':'Form the two new routes around a radius-3mm former. Clamp each stripped end in its matching X1 output with the amplifier loose; keep insulation outside conductor clamp, using actual terminal stripping specification.','tool':'Appropriately fitting small flat blade; proposed2.5mm blade, Ø3x45mm shaft, Ø18x60mm handle.'},{'id':3,'action':'Transfer speaker and amplifier together to an open jig retaining endpoint spacing; keep cable curves supported. Bring the entire prewired pair toward the detached cap.','tool':'Open jig/removable temporary support; proposed assembly translation from -Z40 to seated, not reusing old insertion acceptance.'},{'id':4,'action':'After final roof posts and paths are validated, fasten amp from underside with two existing M2.5x8; install separate speaker keeper/cradle around the already-connected wires. Do not thread terminated wires through a closed keeper.','tool':'Matching M2.5 driver; same-side mounting path still requires new geometry check.'},{'id':5,'action':'Fit removable wire restraints on insulation beyond pad and clamp exits, away from speaker diaphragm and amplifier terminal screws. Connect power/I2S before closure according to the final routed assembly sequence.','tool':'Restraints pending full FFC and GPIO routing; no retaining feature is manufactured by this proposal.'}]}
 tag=str(z).replace('.','p');suffix='-negative' if rear_drop==0 else '';out=D/f'speaker-rewire-amp16z{tag}{suffix}-proposal.json';out.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'file':str(out),'endpoints':[r['terminalMouthWorldMm'] for r in rows],'lengthsMm':[r['analyticCenterlineLengthMm'] for r in rows],'terminalStraightMm':[r['terminalStraightLeadMm'] for r in rows],'pairGapLowerBoundMm':report['wirePairDistanceLowerBoundMm']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--z',type=float,default=2);p.add_argument('--rear-drop',type=float,default=2.4);a=p.parse_args();main(a.z,a.rear_drop)
