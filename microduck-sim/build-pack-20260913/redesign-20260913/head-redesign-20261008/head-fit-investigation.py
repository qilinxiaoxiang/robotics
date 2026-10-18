"""Read-only head fit diagnosis and isolated Boolean candidate evaluation.
No accepted source mesh, guide, or print job is modified.
"""
from pathlib import Path
import json,base64,hashlib,sys
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;G=D.parent/'leg-guide-20261006';SIM=D.parents[2];raw=(G/'full-build-data.json').read_bytes();data=json.loads(raw);by={p['key']:p for p in data['parts']};solids={}
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)))
def solid(k):
 if k not in solids:
  p=by[k];solids[k]=man(trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True))
 return solids[k]
def box(lo,hi):return mf.Manifold.cube(np.array(hi)-lo).translate(lo)
def cylinder_y(r,lo,hi,x=26.1,z=118.6146):return mf.Manifold.cylinder(hi-lo,r,r,circular_segments=128,center=True).rotate([90,0,0]).translate([x,(lo+hi)/2,z])
def samples(moving,fixed,start,stop=(0,0,0),step=.25):
 a,b=np.array(start),np.array(stop);rows=[];peak={}
 for t in np.linspace(0,1,int(np.ceil(np.linalg.norm(b-a)/step))+1):
  v=a*(1-t)+b*t;hits={}
  for k,s in moving.items():
   so=s.translate(v);bb=np.array(so.bounding_box()).reshape(2,3)
   for q,ss in fixed.items():
    qb=np.array(ss.bounding_box()).reshape(2,3)
    if np.any(bb[1]<qb[0]) or np.any(qb[1]<bb[0]):continue
    vol=max(0.,float((so^ss).volume()))
    if vol>1e-7:hits[k+'--'+q]=vol;peak[k+'--'+q]=max(peak.get(k+'--'+q,0),vol)
  rows.append({'translation':v.tolist(),'contactsMm3':hits})
 return {'start':list(start),'stop':list(stop),'spacingMm':step,'peakContactsMm3':peak,'samples':rows}
report={'problemIds':['P5','P6'],'checked':'2026-10-08','sourceDataSha256':hashlib.sha256(raw).hexdigest(),'scope':'Isolated digital fit investigation; no physical force/elasticity or strength acceptance','materialEvidence':{'source':'../../assembly/print-list.html','planned':'PLA for jaw, support, shell, cap and nominal soft pads','actualPrintedMaterialVerified':False},'findings':{}}
# Passive boss projection determines geometric splay needed to pass a closed seat.
passive=solid('jaw_frame')^cylinder_y(5.15,-50,-30)
bb=passive.bounding_box();report['findings']['passiveBoss']={'boundsMm':list(bb),'supportOuterFaceY':-39.7,'minimumOutwardReliefMmToClearClosedBoreLip':max(0,bb[4]-(-39.7)),'closedBoreMm':10.4,'nominalBossMm':10,'supportAxialThicknessMm':2.7,'interpretation':'Pure axial relief requirement for passive boss only; not a permissible PLA deflection or full path certificate.'}
print('PASSIVE',report['findings']['passiveBoss'],flush=True)
# Compare unmodified source support and localized removal candidate.
sys.path.insert(0,str(SIM/'hardware-design-20260912/whole-robot-20260912/assembly'))
from assembly_fk import fk,raw as source_mesh
bodies,geoms=fk();g=next(g for g in geoms if g['body']=='jaw_soft' and g['mesh']=='motor_support');original=man(source_mesh(g['mesh']).apply_transform(g['world']))
support=solid('jaw_support');jaw_group={k:solid(k) for k in ['jaw_frame','motor15','lower_pad']}
slot=box([20.8,-40.5,90],[31.4,-36.5,118.6146]);candidate=support-slot
candidates={'currentClosedSeat':support,'originalCommunitySupport':original,'openLowerSeatCandidate':candidate}
for name,shape in candidates.items():
 result=samples(jaw_group,{name:shape},[0,0,-32]);result.update(volumeMm3=float(shape.volume()),removedFromCurrentMm3=float((support-shape).volume()),componentCount=len(shape.decompose()),status=str(shape.status()));report['findings'][name]=result;print(name,result['peakContactsMm3'],result['removedFromCurrentMm3'],result['componentCount'],flush=True)
report['findings']['openLowerSeatCandidate']['cutBoundsWorldMm']=[[20.8,-40.5,90],[31.4,-36.5,118.6146]]
report['findings']['openLowerSeatCandidate']['retentionStatus']='Open-seat test only. A removable keeper and verified fasteners/load path are required before adoption.'
# Quantify cap-rim crossing locality and geometric opening displacement.
cap=solid('head_cap');face=solid('face_panel');cap_scan=samples({'cap':cap},{'face':face},[0,0,48]);worst=max(cap_scan['samples'],key=lambda r:r['contactsMm3'].get('cap--face',0));offset=worst['translation'];inter=cap.translate(offset)^face;verts=np.asarray(inter.to_mesh().vert_properties)[:,:3]
report['findings']['capFaceBaseline']={**cap_scan,'worstOffset':offset,'worstIntersectionBoundsWorldMm':list(inter.bounding_box()),'intersectionVertexCount':len(verts)}
print('CAP',offset,inter.volume(),inter.bounding_box(),flush=True)
# Split the cap at the symmetry plane and move its sides outward: geometric
# required spread only, with every mesh frozen. This does not estimate strain.
negative=cap^box([-100,-100,0],[150,0,250]);positive=cap^box([-100,0,0],[150,100,250]);spread=[]
for gap in [0,.1,.2,.3,.5,.75,1,1.5,2,3]:
 shape=negative.translate([0,-gap,0])+positive.translate([0,gap,0]);scan=samples({'spreadCap':shape},{'face':face},[0,0,48],step=.5);peak=max(scan['peakContactsMm3'].values(),default=0);spread.append({'eachSideShiftMm':gap,'totalSeparationMm':2*gap,'maxOverlapMm3':peak});print('SPREAD',gap,peak,flush=True)
 if peak<.001:break
report['findings']['capSpreadGeometryOnly']=spread
# Fit mockup: retain the removed original material as a separate loose keeper.
# The two pieces are intentionally not accepted until retention and the full
# downstream insertion sequence have been designed and verified.
def export_stl(shape,path):
 m=shape.to_mesh();trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False).export(path)
keeper=support^slot
export_stl(candidate,D/'open-seat-main-FIT-MOCKUP.stl')
export_stl(keeper,D/'loose-keeper-RETENTION-UNRESOLVED.stl')
manifest=SIM/'team-share-20261001/02-STL-and-Editable-Projects/STL-Instance-Manifest.json'
stock=json.loads(manifest.read_text());stockrows=stock['instances']
stockmatches=[r for r in stockrows if any(t in json.dumps(r).lower() for t in ['motor-support','bearing','smallring','community-24'])]
report['findings']['stock']={'source':str(manifest.relative_to(SIM)),'sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'matchingRows':stockmatches,'retainedStock':data['coverage']['retainedStock'],'conclusion':'Confirmed manifest contains revised coaxial support, not original open support plus a separate mouth bearing; retained stock does not establish a compatible replacement mouth bearing.'}
report['findings']['fitMockup']={'mainFile':'open-seat-main-FIT-MOCKUP.stl','keeperFile':'loose-keeper-RETENTION-UNRESOLVED.stl','mainConnectedComponents':len(candidate.decompose()),'keeperConnectedComponents':len(keeper.decompose()),'keeperVolumeMm3':float(keeper.volume()),'combinedReconstructionDifferenceMm3':float(((candidate+keeper)-support).volume()),'assemblyValidated':False,'printReady':False,'retentionStatus':'Unsecured fit mockup. No fastener/keeper capture or load path has been designed; do not treat as a completed redesign.','lowerSlotWidthMm':10.6,'lowerSlotTopWorldZMm':118.6146,'nominalBossMm':10,'closedBoreMm':10.4,'seamClearanceMm':0}
(D/'head-fit-investigation.json').write_text(json.dumps(report,indent=2)+'\n')

# Full reproducible diagnosis and clearance-only feature candidates.
# All feature STLs remain unaccepted fit mockups.
negative=[]
for v in [[0,32,0],[0,-32,0],[32,0,0],[-32,0,0],[0,0,-32],[0,0,32],[0,32,-32],[32,32,0],[32,32,-32]]:
 r=samples({k:solid(k) for k in ['jaw_frame','lower_pad']},{'motor15':solid('motor15'),'support':candidate,'shell':solid('head_bottom')},v,step=.5)
 negative.append({'startMm':v,'peakContactsMm3':r['peakContactsMm3']})
report['findings']['lowerShellOrderNegativeControl']={'shellFirstJawPadRoutes':negative,'jawMotorPadIntoShell':samples(jaw_group,{'support':candidate,'shell':solid('head_bottom')},[0,0,-32]),'scope':'Nine bounded routes fail; this is not proof against every possible rigid maneuver.'}
jaw=solid('jaw_frame')+solid('lower_pad')
print('BEGIN',flush=True)
sweep=jaw.minkowski_sum(box([-.15,-.15,-.15],[.15,32.15,.15]))
print('SWEEP',sweep.status(),flush=True)
features={}
for k in ['jaw_support','head_bottom']:
 s=solid(k);cut=s^sweep;rem=s-sweep;features[k]={'originalVolume':float(s.volume()),'removalVolumeMm3':float(cut.volume()),'removalBoundsMm':list(cut.bounding_box()),'remainingComponents':len(rem.decompose()),'removedComponents':len(cut.decompose())};print(k,features[k],flush=True)
 m=rem.to_mesh();trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False).export(D/(k+'-side-access-FIT-MOCKUP.stl'))
 features[k]['sampledRoute']=samples({'jaw':solid('jaw_frame'),'pad':solid('lower_pad')},{k:rem},[0,32,0]);print('VERIFY',k,features[k]['sampledRoute']['peakContactsMm3'],flush=True)
face=solid('face_panel');cap=solid('head_cap');sweepface=face.minkowski_sum(box([-.15,-.15,-48.15],[.15,.15,.15]));cut=cap^sweepface;rem=cap-sweepface
features['head_cap']={'originalVolume':float(cap.volume()),'removalVolumeMm3':float(cut.volume()),'removalBoundsMm':list(cut.bounding_box()),'remainingComponents':len(rem.decompose()),'removedComponents':len(cut.decompose())};print('cap',features['head_cap'],flush=True)
m=rem.to_mesh();trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False).export(D/'head-cap-front-lip-FIT-MOCKUP.stl')
features['head_cap']['sampledRoute']=samples({'cap':rem},{'face':face},[0,0,48]);print('VERIFYCAP',features['head_cap']['sampledRoute']['peakContactsMm3'],flush=True)
(D/'head-local-feature-candidates.json').write_text(json.dumps(features,indent=2))

report['findings']['localFeatureCandidates']=features
report['findings']['localFeatureCandidates']['scope']='Clearance-only cut using exact Minkowski swept jaw+pad (+Y32) or face (-Z48), with 0.15 mm clearance. No retention, tool, strength or complete assembly acceptance.'
report['findings']['decision']={'jawSupport': 'Redesign the added closed bearing as a removable bearing cheek/keeper. A simple open slot only resolves loose-bench entry and is not retained. Do not recommend forcing PLA.', 'lowerShell': 'Redesign a removable mouth-side access cheek together with support keeper so jaw can enter from motor-output-compatible +Y direction after shell/support/motor placement. Merely opening the bottom bearing slot or swapping shell/jaw order is insufficient.', 'cap': 'Revise the localized face-engagement rail/undercut for a clear insertion path, or make it separately retained after cap placement. Do not recommend spreading cap sides: 3 mm each side increases intersection. Swept local relief removes 347.46 mm3 (0.92 percent of cap) and clears cap-versus-face rigid descent only.', 'physicalForceApproved': False, 'readyForProductionOrPrint': False, 'remainingEngineering': 'Positive keeper retention and complete assembly/tool/structure verification; no whole-head redesign is justified by these local failures alone.'}
report['sourceDataUnchangedDuringRun']=hashlib.sha256((G/'full-build-data.json').read_bytes()).hexdigest()==report['sourceDataSha256']
report['reportScriptSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
(D/'head-fit-investigation.json').write_text(json.dumps(report,indent=2)+'\n')
