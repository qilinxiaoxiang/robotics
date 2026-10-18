"""One compact four-joint candidate. Purestdlib; no CAD, optimization or fit claim."""
from pathlib import Path
import math,json,hashlib
from rolling_loop_math import planar_rolling_loop
from single_circle_candidate import arc,line
from prepare_single_candidate import moved,add,sub,mul,dot,cross,norm
D=Path(__file__).resolve().parent;H=D.parent.parent
ORDER=['neck_pitch','head_pitch','head_yaw','head_roll']
BODIES={'trunk_base':0,'neck':1,'neck_pitch':2,'yaw_roll_motion':3,'jaw_soft':4}
SPECS=[
 {'name':'neck_pitch_loop','joint':'neck_pitch','parent':'trunk_base','child':'neck','center':[26,-38,32.4215],'axis':[0,1,0],'radial':[-1,0,0],'Ri':12,'Ro':30,'C':55,'sign':-1},
 {'name':'head_pitch_loop','joint':'head_pitch','parent':'neck','child':'neck_pitch','center':[26,-56,82.4215],'axis':[0,1,0],'radial':[-1,0,0],'Ri':12,'Ro':30,'C':75,'sign':1},
 {'name':'head_yaw_loop','joint':'head_yaw','parent':'neck_pitch','child':'yaw_roll_motion','center':[26,0,94],'axis':[0,0,1],'radial':[-1,0,0],'Ri':30,'Ro':48,'C':115,'sign':1},
 {'name':'head_roll_loop','joint':'head_roll','parent':'yaw_roll_motion','child':'jaw_soft','center':[-41,0,115.6146],'axis':[-1,0,0],'radial':[0,0,-1],'Ri':20,'Ro':38,'C':27,'sign':1}]

def move_body(p,q,body,vector=False):return moved(p,{k:q.get(k,0) for k in ORDER[:BODIES[body]]},vector)
def make_path(start,tangent):return {'points':[start],'lengthMm':0.,'startTangent':tangent,'endTangent':tangent,'minimumRadiusMm':1e20}
def straight(path,end):
 a=path['points'][-1];delta=sub(end,a);L=norm(delta)
 if L>1e-9:
  t=mul(delta,1/L);assert norm(sub(t,path['endTangent']))<1e-8,'Non-tangent straight';path['points']+=line(a,end)[1:];path['lengthMm']+=L;path['endTangent']=t
 return path

def turn(path,tangent,R):
 p,L=arc(path['points'][-1],path['endTangent'],tangent,R);path['points']+=p[1:];path['lengthMm']+=L;path['endTangent']=tangent;path['minimumRadiusMm']=min(path['minimumRadiusMm'],R);return path

def ubridge(start,end,tangent,R,leg=3):
 delta=sub(end,start);axial=dot(delta,tangent);chord=sub(delta,mul(tangent,axial));dist=norm(chord);e=mul(chord,1/dist);R=min(R,dist/2);assert leg-axial>=0
 p=make_path(start,tangent);straight(p,add(start,mul(tangent,leg)));turn(p,e,R);straight(p,add(p['points'][-1],mul(e,dist-2*R)));turn(p,mul(tangent,-1),R);straight(p,end);return p

def fixed_paths():
 body=make_path([-57,-66,22.4215],[1,0,0]);straight(body,[38,-66,22.4215]);turn(body,[0,1,0],14);turn(body,[-1,0,0],14);straight(body,[24,-38,22.4215]);turn(body,[0,0,1],10)
 nh=ubridge([-4,-38,32.4215],[14,-56,82.4215],[0,0,-1],12)
 hy=make_path([-4,-56,82.4215],[0,0,-1]);turn(hy,[0,1,0],10);straight(hy,[-4,0,72.4215]);turn(hy,[0,0,1],10);straight(hy,[-4,10,84]);turn(hy,[0,-1,0],10)
 yr=ubridge([-22,0,94],[-41,0,95.6146],[0,1,0],16)
 rh=make_path([-41,0,77.6146],[0,1,0]);turn(rh,[0,0,1],24);straight(rh,[-41,24,109]);turn(rh,[1,0,0],16)
 return [('torso_entry','trunk_base',body),('neck_to_head_pitch','neck',nh),('head_pitch_to_yaw','neck_pitch',hy),('yaw_to_roll','yaw_roll_motion',yr),('roll_to_head_portal','jaw_soft',rh)]
FIXED=fixed_paths()

def geometry(q,step=.5):
 loops=[]
 for s in SPECS:
  angle=math.radians(q.get(s['joint'],0))*s['sign'];a=planar_rolling_loop(s['center'],s['axis'],s['radial'],s['Ri'],s['Ro']-s['Ri'],math.radians(s['C']),angle,step)
  e=cross(s['axis'],s['radial']);from prepare_single_candidate import rot
  endT=mul(rot(e,s['axis'],angle),-1)
  loops.append({'name':s['name'],'body':s['parent'],'points':[move_body(p,q,s['parent']) for p in a['points']],'lengthMm':a['analyticLengthMm'],'minimumRadiusMm':a['minimumCenterlineRadiusMm'],'startTangent':move_body(e,q,s['parent'],True),'endTangent':move_body(endT,q,s['parent'],True)})
 fixed=[]
 for name,body,p in FIXED:
  fixed.append({'name':name,'body':body,'points':[move_body(x,q,body) for x in p['points']],'lengthMm':p['lengthMm'],'minimumRadiusMm':p['minimumRadiusMm'],'startTangent':move_body(p['startTangent'],q,body,True),'endTangent':move_body(p['endTangent'],q,body,True)})
 out=[fixed[0]]
 for i in range(4):out += [loops[i],fixed[i+1]]
 return out

def verify_math():
 source=H/'usb-access/usb-repair/rigid-domain.json';base=json.loads(source.read_text());cases=[r['jointDegrees'] for r in base['samples']]
 for j,(lo,hi) in base['sourceJointLimitsDegrees'].items():
  cases += [{j:float(a)} for a in range(round(lo),round(hi)+1)]
 zero=geometry({});L=sum(p['lengthMm'] for p in zero);maximumGap=0.;maximumTangentGap=0.;maximumBridgeChordChange=0.;minimumRadius=1e20;maximumLengthDrift=0.;minimumAngle=1e20
 for q in cases:
  parts=geometry(q,2);maximumLengthDrift=max(maximumLengthDrift,abs(sum(p['lengthMm'] for p in parts)-L));minimumRadius=min(minimumRadius,min(p['minimumRadiusMm'] for p in parts))
  for a,b in zip(parts,parts[1:]):maximumGap=max(maximumGap,norm(sub(a['points'][-1],b['points'][0])));maximumTangentGap=max(maximumTangentGap,norm(sub(a['endTangent'],b['startTangent'])))
  # Rigid bridge preserves every sampled segment, not just its endpoints.
  for i in [0,2,4,6,8]:
   for (a,b),(c,d) in zip(zip(zero[i]['points'],zero[i]['points'][1:]),zip(parts[i]['points'],parts[i]['points'][1:])):
    maximumBridgeChordChange=max(maximumBridgeChordChange,abs(norm(sub(a,b))-norm(sub(c,d))))
  for s in SPECS:
   angle=math.radians(q.get(s['joint'],0))*s['sign'];theta=math.radians(s['C'])+s['Ro']/(s['Ri']+s['Ro'])*angle
   minimumAngle=min(minimumAngle,theta,theta-angle)
 assert maximumGap<1e-8 and maximumTangentGap<1e-8 and maximumLengthDrift<1e-8 and maximumBridgeChordChange<1e-8
 points=[p for s in zero for p in s['points']];bound=[list(map(min,zip(*points))),list(map(max,zip(*points)))];sources=[source,Path(__file__),D/'rolling_loop_math.py',D/'single_circle_candidate.py',D/'prepare_single_candidate.py'];native=H.parent/'leg-guide-20261006/full-build-data.json';data=json.loads(native.read_text());keys=['shell_left','shell_right','imu_clamp','neck_pitch','neck_pitch_ring','head_yaw_link','motor11','motor12','motor13','motor14','head_bottom','head_cap'];sources.append(native)
 report={'accepted':False,'geometryChecked':False,'design':'One compact four-joint segmented candidate; native ranges unchanged','loopFormula':'thetaJoin=C+Ro/(Ri+Ro)*q; length=Ri*thetaJoin+Ro*(thetaJoin-q)+pi*(Ro-Ri)/2=(Ri+Ro)*C+pi*(Ro-Ri)/2','loopSpecs':SPECS,'mathVerification':{'poses':len(cases),'all229SourcePosesIncluded':True,'eachSingleJointAtOneDegreeIncluded':True,'maxJoinGapMm':maximumGap,'maxJoinTangentVectorDifference':maximumTangentGap,'maxLengthDriftMm':maximumLengthDrift,'maxRigidBridgeSegmentLengthDriftMm':maximumBridgeChordChange,'minimumCenterlineRadiusMm':minimumRadius,'minimumInnerRadiusBoundFor7mmReceivingMm':minimumRadius-3.5,'minimumArcAngleDegrees':math.degrees(minimumAngle)},'neutralCenterlineBounds':bound,'neutralReceivingBounds':[[v-3.5 for v in bound[0]],[v+3.5 for v in bound[1]]],'sourceNeutralBounds':{p['key']:p['bounds'] for p in data['parts'] if p['key'] in keys},'segments':[{'name':s['name'],'body':s['body'],'lengthMm':s['lengthMm'],'start':s['points'][0],'end':s['points'][-1],'startTangent':s['startTangent'],'endTangent':s['endTangent'],'minimumRadiusMm':s['minimumRadiusMm']} for s in zero],'totalModeledLengthMm':L,'headPortalMovedTo':[-25,24,125],'bodyInputHoldingPoint':[-57,-66,22.4215],'sourceBinding':{str(p.relative_to(H.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'limitations':['Lengths coverbodyholdingpoint-to-headportal only, notactualpin/socketfanouts. Existing150mm4397 and250mmtargetextensions cannot beclaimedadequate.','LongerI2Croute needs electricalsignal-integrityverification and actualextensionstock; no electricalacceptance/purchase release implied.','Receiving diameter7mm and individualpower/audio wireOD bounds are design assumptions; 4397OD0.8 is manufacturerdrawing.','Free rolling-Ushapes are a kinematic family; needguides/retention, actualwiremotion/fatigue andinstallation proof.','No solidobstacle orwire-selfintersection checkrun. No cap/face printreleased.']}
 (D/'compact-segmented-candidate.json').write_text(json.dumps(report,indent=2)+'\n');(D/'compact-neutral-centerlines.json').write_text(json.dumps(zero,separators=(',',':'))+'\n');print(json.dumps({'mathVerification':report['mathVerification'],'lengthMm':L,'receivingBounds':report['neutralReceivingBounds']},indent=2))
if __name__=='__main__':verify_math()
