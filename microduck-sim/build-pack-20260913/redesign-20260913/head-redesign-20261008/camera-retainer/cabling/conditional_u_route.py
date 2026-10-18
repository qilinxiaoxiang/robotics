from pathlib import Path
import json,numpy as np,trimesh,manifold3d as mf
from scipy.optimize import brentq
D=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/camera-retainer/cabling')
src=(D/'build_full_ribbon.py').read_text();exec(src[:src.index('loopx=brentq')].replace('D=Path(__file__).resolve().parent','D=Path('+repr(str(D))+')'));exec(src[src.index("files={'curved_cap'"):src.index('hits={}')])

for k in ['head_yaw_link','motor13','neck_pitch','neck_pitch_ring','head_roll_ring_a','head_roll_ring_b','jaw_frame','upper_pad','lower_pad']:obs[k]=dec(k)
def route(lowY,left=53.5,top=35.9,r=3.,lead=0.):
 wp=np.array([cam-[0,5,0],[cam[0],top,end_z],[left,top,end_z],[left,lowY,end_z],[left+6,lowY,end_z],[left+6,pi[1]+r+lead,end_z],[pi[0],pi[1]+r+lead,end_z],pi-[0,4.4,0]])
 wp[-1,2]=end_z;cuts=[]
 for i in range(1,len(wp)-1):
  u=wp[i]-wp[i-1];u/=np.linalg.norm(u);v=wp[i+1]-wp[i];v/=np.linalg.norm(v);theta=np.arccos(np.clip(u@v,-1,1));d=r*np.tan(theta/2);axis=np.cross(u,v);axis/=np.linalg.norm(axis);a=wp[i]-u*d;b=wp[i]+v*d;center=a+np.cross(axis,u)*r;cuts.append((a,b,center,axis,theta,d))
 for i in range(len(wp)-1):assert np.linalg.norm(wp[i+1]-wp[i])+1e-6>=(cuts[i-1][5] if i else 0)+(cuts[i][5] if i<len(cuts) else 0)
 pts=[wp[0]];total=0.;prev=wp[0]
 for a,b,center,axis,theta,d in cuts:
  le=np.linalg.norm(a-prev);pts.extend(np.linspace(prev,a,max(1,int(np.ceil(le/.15)))+1)[1:]);total+=le;va=a-center
  for ang in np.linspace(0,theta,max(2,int(np.ceil(r*theta/.15)))+1)[1:]:pts.append(center+va*np.cos(ang)+np.cross(axis,va)*np.sin(ang))
  total+=r*theta;prev=b
 le=np.linalg.norm(wp[-1]-prev);pts.extend(np.linspace(prev,wp[-1],max(1,int(np.ceil(le/.15)))+1)[1:]);return np.array(pts),total+le,wp

def make(left=53.5,top=35.9,width=11.5,thick=.3,lead=0.):
 low=brentq(lambda y:route(y,left,top,lead=lead)[1]-200,-45,-15);points,L,wp=route(low,left,top,lead=lead);points=points[np.r_[True,np.linalg.norm(np.diff(points,axis=0),axis=1)>1e-7]];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
 ww=np.maximum(width,16-(16-width)*np.clip((arc-5)/8,0,1));ww=np.maximum(ww,11.5-(11.5-width)*np.clip((arc[-1]-arc-4.4)/8,0,1))
 v=np.gradient(points,axis=0);v/=np.linalg.norm(v,axis=1)[:,None];w=np.tile([0,0,1.],(len(points),1));n=np.cross(v,w);verts=[]
 for p,a,b,wd in zip(points,w,n,ww):verts.extend([p-a*wd/2-b*thick/2,p+a*wd/2-b*thick/2,p+a*wd/2+b*thick/2,p-a*wd/2+b*thick/2])
 faces=[[0,2,1],[0,3,2]]
 for i in range(len(points)-1):
  for j in range(4):a=4*i+j;b=4*i+(j+1)%4;c=b+4;d=a+4;faces.extend([[a,b,c],[a,c,d]])
 nv=len(verts);faces.extend([[nv-4,nv-3,nv-2],[nv-4,nv-2,nv-1]]);m=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(m);cable=man(m)
 assert cable.status()==mf.Error.NoError and m.is_watertight
 hits={k:max(0,float((cable^(o-slots[k] if k in slots else o)).volume())) for k,o in obs.items()};hits={k:v for k,v in hits.items() if v>1e-5}
 return cable,m,points,arc,np.asarray(verts).reshape(-1,4,3),{'leftXmm':left,'topYmm':top,'lowYmm':low,'middleWidthMm':width,'thicknessMm':thick,'bendRadiusMm':3,'outsidePiStraightLeadMm':lead,'totalAnalyticLengthMm':L,'waypointsMm':wp.tolist(),'intersectionsMm3':hits}

def self_test(vv,arc):
 # All strip sections are vertical; each cell's XY footprint is an exact quad.
 # Nonadjacent footprint intersection + overlappingZ bounds implies true3D
 # self-intersection. Adjacent cells share their intended end face only.
 from shapely.geometry import Polygon,box as shapelybox
 from shapely.strtree import STRtree
 polys=[Polygon([vv[i,0,:2],vv[i+1,0,:2],vv[i+1,3,:2],vv[i,3,:2]]) for i in range(len(vv)-1)];tree=STRtree(polys);hits=[];mindist=1e6;pair=None
 for i,p in enumerate(polys):
  xmin,ymin,xmax,ymax=p.bounds
  for j in tree.query(shapelybox(xmin-1,ymin-1,xmax+1,ymax+1)):
   j=int(j)
   if j<=i+1:continue
   za=(min(vv[i:i+2,:,2].ravel()),max(vv[i:i+2,:,2].ravel()));zb=(min(vv[j:j+2,:,2].ravel()),max(vv[j:j+2,:,2].ravel()));overlapz=min(za[1],zb[1])-max(za[0],zb[0])
   if overlapz<=0:continue
   area=p.intersection(polys[j]).area
   if area>1e-9:hits.append({'cellA':i,'cellB':j,'planarAreaMm2':area,'overlapHeightMm':overlapz})
   if arc[j]-arc[i+1]>=10:
    dist=p.distance(polys[j])
    if dist<mindist:mindist=dist;pair=[i,j]
 return {'nonadjacentCellIntersections':hits,'minimumNonlocalSolidGapMm':mindist,'minimumGapCellPair':pair,'distanceExclusion':'Only distance metric excludes sections separated by<10mm of cable arclength. Intersection test excludes only immediately adjacent cells with a normal shared end face.','method':'Exact2D polygon intersections of vertical3D cells plus overlappingZ bounds, using full0.3mm strip thickness.'}

if __name__=='__main__':
 import hashlib
 baseline=make();selfcheck=self_test(baseline[4],baseline[3]);assert not selfcheck['nonadjacentCellIntersections'];assert not baseline[-1]['intersectionsMm3']
 # Bound the attainable same-plane topbar spacing before source cap collision.
 low,high=35.9,36.2
 for _ in range(12):
  mid=(low+high)/2;r=make(top=mid)
  if r[-1]['intersectionsMm3']:high=mid
  else:low=mid
 widened=make(top=low);wide_self=self_test(widened[4],widened[3])
 # Capture how much rigid mini-end protrusion this family can accept before
 # violating self-clearance or the actual curved shell. No actual rigid length
 # is assumed safe merely because the flexible-body calculation is clear.
 leads=[]
 for lead in [0,.25,.5,1.,1.5,2.]:
  r=make(top=low,lead=lead);st=self_test(r[4],r[3]);leads.append({**r[-1],'selfCheck':st})
 cable,mesh,points,arc,vv,row=baseline;closure=[];peak={}
 moving=['curved_cap','openrb','audio-roof-posts','speaker','amplifier','speaker-cradle','speaker-keeper','cap-eight-screw-heads-four-nuts']
 for dz in np.arange(40,-.001,-.25):
  h={}
  for k in moving:
   q=obs[k].translate([0,0,float(dz)])^cable;vol=max(0,q.volume())
   if vol>1e-5:h[k]=vol;peak[k]=max(peak.get(k,0),vol)
  closure.append({'offsetZmm':float(dz),'intersectionsMm3':h})
 # Negative control of wider cable, without substituting16mm compatibility.
 wide_negative=make(top=low,width=16)[-1]
 mesh.export(D/'sc1892-200mm-conditional-U-world.stl')
 (D/'conditional-U-centerline.json').write_text(json.dumps({'centerlineWorldMm':points.tolist(),'parameters':row},indent=2)+'\n')
 source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files.values()}
 report={'date':'2026-10-08','status':'CONDITIONAL_STATIC_GEOMETRY_ONLY_NOT_ASSEMBLY_RELEASE','originalIndependentCandidate':baseline[-1],'independentSelfCheck':selfcheck,'maximumSamePlaneTopbarBeforeCollisionMm':low,'nextFailingTopbarMm':high,'spacingImprovementCandidate':widened[-1],'spacingBoundaryIsNotRecommended':True,'publishedCandidate':row,'spacingSelfCheck':wide_self,'leadSensitivity':leads,'sixteenMmNegativeControl':wide_negative,'closure':{'moving':moving,'fixed':['fullFFC','face','retainer','camera','ZeroW'],'samples':closure,'stepMm':.25,'peakIntersectionsMm3':peak,'passes':not bool(peak)},'maximumCenterlineSegmentMm':float(np.linalg.norm(np.diff(points,axis=0),axis=1).max()),'actualContactAndLatchBoundary':{'cameraInsertedLengthAssumedMm':5,'piInsertedLengthAssumedMm':4.4,'cameraOutsideStraightBeforeFirstBendMm':row['topYmm']-3-cam[1],'piOutsideStraightBeforeFirstBendMm':0,'piModelHeightOffsetMm':float(cam[2]-pi[2]),'actualStiffenerLengthsKnown':False,'actualLatchFingerAccessCertified':False,'constraint':'This route bends immediately outside Pi mouth. Any stiffener protruding from the latched connector invalidates the zero-outside-lead model; see explicit0.25–2mm sensitivity.'},'parametersAreReceivingAssumptions':['11.5mm body width','0.3mm total thickness','R3mm static bend radius','camera end16mm with5mm straight+8mm transition','Pi end11.5mm with4.4mm insertion'],'assemblyAcceptance':False,'physicalFitVerified':False,'publication':'Keep original upward-exit baseline published.90deg mechanical variant and this11.5mm route remain independent conditional candidates.','requiredMeasurements':['SC1892 actual body maximum width and total thickness','Mini-end rigid length remaining outside closedZeroWlatch after full seating','Camera-end rigid length remaining outside closedcamera latch','Actual static bend-radius capability without crease/rebound and connector loading'],'sourceHashes':source_hashes}
 (D/'conditional-U-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'baselineStatic':baseline[-1]['intersectionsMm3'],'baselineSelf':selfcheck,'widenedStatic':row['intersectionsMm3'],'widenedTopY':low,'widenedGap':wide_self['minimumNonlocalSolidGapMm'],'closurePeak':peak,'leadResults':[{ 'lead':a['outsidePiStraightLeadMm'],'external':a['intersectionsMm3'],'selfPairCount':len(a['selfCheck']['nonadjacentCellIntersections'])} for a in leads]},indent=2))
