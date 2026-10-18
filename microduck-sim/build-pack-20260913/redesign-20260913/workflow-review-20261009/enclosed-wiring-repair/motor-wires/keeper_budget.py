"""Rigid endpoint/guide distance only; not a flexible cable simulator or fit certificate."""
from pathlib import Path
import json,sys,hashlib,itertools,numpy as np
D=Path(__file__).parent;SIM=D.parents[4];FK=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py'
sys.path.insert(0,str(FK.parent));from assembly_fk import fk
B,_=fk();rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for filename,side,sourcebody,targetbody in [('local-route.json','right','bearing_roll','upper_leg_right'),('mirror-route.json','left','yaw2roll','upper_leg_left')]:
 a=json.loads((D/filename).read_text());case=[]
 # Use right 4->3 route material direction, mirrored for physical9->8 (new second branch direction).
 raw=json.loads((D/'local-route.json').read_text())
 for w in raw['strands']:
  ps=w['primitives'];A=np.array(ps[0]['end']);returnline=ps[8];C=(np.array(returnline['start'])+np.array(returnline['end']))/2
  sC=sum(p['lengthMm']for p in ps[:8])+np.linalg.norm(C-np.array(returnline['start']));free=sC-ps[0]['lengthMm'];tail=180-sC
  if side=='left':A[1]*=-1;C[1]*=-1
  al=np.linalg.inv(B[sourcebody])@np.r_[A,1];cl=np.linalg.inv(B[targetbody])@np.r_[C,1];samples=[]
  for roll,pitch in itertools.product([-22,-15,-10,-5,0,5,10,15,22],range(-90,91,10)):
   posed,_=fk({side+'_hip_roll':np.deg2rad(roll),side+'_hip_pitch':np.deg2rad(pitch)});aa=(posed[sourcebody]@al)[:3];cc=(posed[targetbody]@cl)[:3];chord=float(np.linalg.norm(cc-aa));samples.append({'rollDegrees':roll,'pitchDegrees':pitch,'chordMm':chord})
  largest=max(samples,key=lambda x:x['chordMm']);case.append({'wire':w['id'],'sourceGuideWorldMm':A.tolist(),'targetGuideCandidateWorldMm':C.tolist(),'targetGuidePhysicallyAnchored':False,'fixedTargetTailMm':tail,'freeServiceLengthMm':free,'largestStraightSeparation':largest,'remainingBeyondStraightChordMm':free-largest['chordMm'],'samples':samples})
 rows.append({'side':side,'sourceBody':sourcebody,'targetBody':targetbody,'routeSha256':sha(D/filename),'wires':case})
 print(side,[(w['wire'],round(w['freeServiceLengthMm'],2),round(w['largestStraightSeparation']['chordMm'],2),round(w['remainingBeyondStraightChordMm'],2))for w in case])
(D/'keeper-service-budget.json').write_text(json.dumps({'sourceHashes':{str(FK):sha(FK)},'scope':'Rigid guide-point reach lower bound across source joint ranges; does not prove collision-free flexible shapes, retention, usable bend radius or physical joint calibration. Target guide is a candidate, not verified fixing point.','results':rows},indent=2))
