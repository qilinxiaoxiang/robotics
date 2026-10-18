"""Necessarylengthconditiononly; no pretendwideFFC motionorjointclearancepass."""
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np,json,itertools,hashlib,trimesh
D=Path(__file__).resolve().parent;project=D.parents[6]
xmlpath=project/'microduck-simulator/app/public/robot/mjlab/robot_allcollisions.xml'
# explicitcanonicalpath ratherthan guessingparentcount
xmlpath=Path('/Users/xiangzheng/code/robotics/microduck-sim/microduck-simulator/app/public/robot/mjlab/robot_allcollisions.xml')
root=ET.parse(xmlpath).getroot();parents={child:parent for parent in root.iter() for child in parent}
body=next(a for a in root.iter('body') if a.get('name')=='jaw_soft');chain=[]
while body.tag=='body':chain.append(body);body=parents[body]
chain.reverse();names=['neck_pitch','head_pitch','head_yaw','head_roll'];limits={}
for b in chain:
 for j in b.findall('joint'):
  if j.get('name') in names:limits[j.get('name')]=list(map(float,j.get('range').split()))
def fk(q):
 T=np.eye(4)
 for b in chain:
  B=trimesh.transformations.quaternion_matrix(np.fromstring(b.get('quat','1 0 0 0'),sep=' '));B[:3,3]=1000*np.fromstring(b.get('pos','0 0 0'),sep=' ');
  if b.get('name')=='trunk_base':B[:3,3]=0 # guidecoordinatesomit120mmMuJoCostandingheight
  T=T@B
  for j in b.findall('joint'):
   if j.get('name') in names:T=T@trimesh.transformations.rotation_matrix(q.get(j.get('name'),0),np.fromstring(j.get('axis','0 0 1'),sep=' '))
 return T
cam=np.array([74.73,-.0913783,140.5766,1.]);local=np.linalg.inv(fk({}))@cam
samples=[]
for vals in itertools.product(*[[limits[n][0],0.,limits[n][1]] for n in names]):
 q=dict(zip(names,vals));samples.append((q,(fk(q)@local)[:3]))
r=json.loads((D/'report.json').read_text());rows=[]
for idx,a in enumerate(r['insideCandidates']):
 p=np.array(a['piMouthWorldMm']);values=[(float(np.linalg.norm(c-p))+9.4,q) for q,c in samples];length,q=max(values,key=lambda v:v[0]);rows.append({'candidateIndex':idx,'maxSampledStraightLowerBoundMm':length,'fails200mmNecessaryCondition':length>200,'worstJointsRadians':q})
report={'status':'NECESSARY_LENGTH_BOUNDS_NOT_CABLE_ACCEPTANCE','jointRangesDegrees':{k:(np.array(v)*180/np.pi).tolist() for k,v in limits.items()},'postures':len(samples),'posesReviewed':len(rows),'countOver200mm':sum(a['fails200mmNecessaryCondition'] for a in rows),'minimumAcrossCandidateWorstBoundsMm':min(a['maxSampledStraightLowerBoundMm'] for a in rows),'maximumAcrossCandidateWorstBoundsMm':max(a['maxSampledStraightLowerBoundMm'] for a in rows),'assumedContactsIncludedMm':9.4,'method':'Currentcamera-worldmouthmappedintooriginaljaw_softlocalframeatzeropose; existingMJCF4jointkinematics sampledmin/zero/max, with120mmglobaltrunkstandingtranslationremovedtomatchguideworld. Camera remainshead-mounted,Piistorso-fixed. Straightdistancedoesnotincludeobstacles,wrap,torsionorserviceloops. NoneofthesePiposeshaveclearplacement.','rows':rows,'routingAcceptance':False,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [xmlpath,D/'report.json',D/'joint_lower_bounds.py']}}
(D/'joint-length-report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['rows','sourceHashes']},indent=2))
