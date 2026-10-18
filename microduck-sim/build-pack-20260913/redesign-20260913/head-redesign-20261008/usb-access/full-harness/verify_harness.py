"""Independent self-intersection and articulated swept-state checks for external harness."""
from pathlib import Path
D=Path(__file__).resolve().parent
exec((D/'build_harness.py').read_text().split('# PUBLISHED_CONNECTOR_FROM_SOURCE_SHOULDER')[0])
import itertools
r=json.loads((D/'full-harness-report.json').read_text());names=['sc0727_external_cable','adafruit4472_external_cable','usb_a_female_receiving','usb_a_male_receiving','openrb_usb_c_published','pi_usb_receiving'];s={k:man(load(D/(k+'-world.stl'))) for k in names}
pairs={}
for a,b in itertools.combinations(names,2):
 v=hits(s[a],s[b])
 if v>1e-4:pairs[a+'--'+b]=v
# Exact segment distances use finite capsule-line closest points, not visual loops.
def segment_dist(p1,q1,p2,q2):
 u=q1-p1;v=q2-p2;w=p1-p2;a=u@u;b=u@v;c=v@v;d=u@w;e=v@w;den=a*c-b*b
 ss=np.clip((b*e-c*d)/den if den>1e-20 else 0,0,1);tt=np.clip((b*ss+e)/c,0,1);ss=np.clip((b*tt-d)/a,0,1);tt=np.clip((b*ss+e)/c,0,1);return np.linalg.norm(w+ss*u-tt*v)
selfRows={}
for key,points,diam in [('sc0727',r['geometry']['scCenterlineMm'],3.5),('adafruit4472',r['geometry']['acCenterlineMm'],4.5)]:
 pts=np.array(points);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))];best=1e9;pair=None
 for i in range(len(pts)-1):
  for j in range(i+1,len(pts)-1):
   if arc[j]-arc[i+1]<diam*2:continue
   if np.linalg.norm(pts[i]-pts[j])>best+1:continue
   dis=segment_dist(pts[i],pts[i+1],pts[j],pts[j+1])
   if dis<best:best=dis;pair=[i,j]
 selfRows[key]={'minimumNonlocalSegmentCenterDistanceMm':best,'diameterMm':diam,'surfaceGapMm':best-diam,'closestSegmentPair':pair,'localArcNeighborhoodExcludedMm':diam*2,'reasonForLocalExclusion':'Adjacent points on a smooth R10 tube occupy the same local neighbourhood;2D diameter arc-neighbourhood excluded only from nonlocal self-contact search.'}
SIM=H.parent.parents[1];sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'));from assembly_fk import fk,TREE
B,_=fk();Pinv={k:np.linalg.inv(v) for k,v in B.items()};bodymap={p['key']:p.get('body','jaw_soft') for p in data['parts']};unmatched={k:bodymap[k] for k in obs if k in bodymap and bodymap[k] not in B}
for k in obs:
 if k not in bodymap:bodymap[k]='jaw_soft'
bodymap={k:b if b in B else 'trunk_base' for k,b in bodymap.items()};headBody='jaw_soft';combined=mf.Manifold.batch_boolean(list(s.values()),mf.OpType.Add)
# Test source stated joint ranges at5deg, all other joints zero, plus a modest
# combined grid. This detects new restrictions; it is not a continuous dynamics proof.
js=['neck_pitch','head_pitch','head_yaw','head_roll'];limits={j:np.rad2deg(np.fromstring(next(x for x in TREE.iter('joint') if x.get('name')==j).get('range'),sep=' ')).tolist() for j in js};cases=[]
for j,(lo,hi) in limits.items():
 for a in np.linspace(lo,hi,int(np.ceil((hi-lo)/5))+1):cases.append({j:float(a)})
for a in itertools.product([-20,0,20],[-30,0,30],[-90,0,90],[-20,0,20]):cases.append(dict(zip(js,a)))
rows=[]
for qdeg in cases:
 posed,_=fk({k:np.deg2rad(v) for k,v in qdeg.items()});T=posed[headBody]@Pinv[headBody];harness=combined.transform(T[:3,:]);hh={}
 for k,o in obs.items():
  b=bodymap[k]
  if b==headBody:continue # same rigid transform; full static checks own these
  Tb=posed[b]@Pinv[b];v=hits(harness,o.transform(Tb[:3,:]))
  if v>1e-4:hh[k]=v
 baseline={}
 if hh:
  for part in ['head_cap','head_bottom']:
   moved=obs[part].transform(T[:3,:])
   for k,o in obs.items():
    b=bodymap[k]
    if b==headBody:continue
    Tb=posed[b]@Pinv[b];vv=hits(moved,o.transform(Tb[:3,:]))
    if vv>1e-4:baseline[part+'--'+k]=vv
 rows.append({'jointDegrees':qdeg,'intersectionsMm3':hh,'rigidHeadBaselineIntersectionsMm3':baseline})
fail=[p for p in rows if p['intersectionsMm3']];out={'selfPairsMm3':pairs,'nonlocalTubeChecks':selfRows,'unmatchedSourceBodies':unmatched,'sourceJointLimitsDegrees':limits,'articulatedSamples':rows,'articulatedFailedSamples':len(fail),'articulatedTotalSamples':len(rows),'allSampledStatesClear':not fail,'failedStatesAlreadyBlockedByRigidHead':all(p['rigidHeadBaselineIntersectionsMm3'] for p in fail),'newlyBlockedSampledStates':sum(not p['rigidHeadBaselineIntersectionsMm3'] for p in fail),'currentPoseStaticClear':r['gates']['staticSolidClear'],'sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [D/'full-harness-report.json',D/'build_harness.py',C/'curved-cap-final-candidate-world.stl']},'physicalFitVerified':False}
(D/'harness-path-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'selfPairs':pairs,'nonlocal':selfRows,'motionFailures':fail,'samples':len(rows),'unknownBodies':unmatched},indent=2),flush=True)
