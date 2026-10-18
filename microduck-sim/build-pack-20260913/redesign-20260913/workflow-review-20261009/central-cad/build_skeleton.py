from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;R=D.parents[1];G=R/'leg-guide-20261006';f=G/'full-build-data.json';d=json.loads(f.read_text());pr=[]
def box(key,lo,hi,role):pr.append({'key':key,'kind':'box','originMinMm':lo,'dimensionsMm':[b-a for a,b in zip(lo,hi)],'color':'#b99256','role':role})
box('upper_central_bridge',[-22,-17.5,20],[15,17.5,22],'Cross-body load path above battery and behind ID12; 2 mm is conceptual, not strength-qualified.')
for sign,label in [(1,'left'),(-1,'right')]:
 def y(a,b):return [a,b]if sign>0 else [-b,-a]
 a,b=y(15.5,17.5);box(label+'_inner_web',[-20,a,20],[17.5,b,26.5],'Connect bridge to hip upper case rails; does not shift the neck axis.')
 for name,x in [('rear',-16.5),('front',13.5)]:
  a,b=y(16,40);box(label+'_'+name+'_hip_rail',[x-4,a,24],[x+4,b,26.5],'Upper hip case saddle aligned with source screw axes. Underside seat stack and screw lengths still require detailed design.')
 a,b=y(16,19);box(label+'_neck_carrier',[15,a,24],[38,b,43],'Replacement neck cheek around unchanged source shaft/hole pattern; uncut block is only a load-path primitive, not a finished bearing pocket.')
anchors=[]
for s in d['screws']:
 if s['id']in ['S10-case-069','S10-case-070','S10-case-071','S10-case-072','S05-case-073','S05-case-074','S05-case-075','S05-case-076'] or s['id'].startswith('S12-horn-'):
  q=s['world_center_mm'].copy();dy=11 if s['id'].startswith('S10-')else -11 if s['id'].startswith('S05-')else 0;q[1]+=dy
  anchors.append({'sourceScrewId':s['id'],'sourceComponent':s['component'],'sourceIds':s['source_ids'],'sourceWorldCenterMm':s['world_center_mm'],'candidateCenterMm':q,'axis':s['world_axis'],'sourceEvidence':s['evidence'],'newScrewLengthVerified':False,'meaning':'Measured original hole axis translated with whole hip case, or unchanged neck interface; not an invented mounting hole.'})
r={'status':'LOAD-PATH SKELETON ONLY / NOT PRINTABLE','units':'mm','baselineC':'Original C bank centre remains [-5,0,-6] in mesh comparison. This independent skeleton candidate lowers only bank by 8 mm.','batterySolid':{'name':'C lowered8 nominal bank','originMinMm':[-45.45,-13,-46.95],'dimensionsMm':[80.9,26,65.9],'translationFromOriginalC':[0,0,-8]},'primitiveSolids':pr,'interfaceAxes':anchors,'clearanceTargets':{'batteryTopToBridgeBottomMm':1.05,'bridgeTopToID12BoundingBoxMm':.921499252319336,'innerWebToHipCaseInnerBoundingFaceMm':1.0},'preserved':['Complete leg internal mechanisms, each leg shifted 11 mm only.','Neck joint axes and current head exterior.'],'nextDetailedFeatures':['Retain exact neck bearing/pilot seat profiles from current community8/10 around recorded axes; primitive cheeks are not pocket designs.','Reuse/reshape the original hip bottom seat islands around S10-case069/070 and S05-case073/074 and join them to the rails outside battery. These lower constraints are not represented by the upper-frame primitive.','Integrate a bottom-support tray/strap stops with both X end faces open; extraction direction and plug slack must be checked.','Relocate DFR to a side wing after power architecture selection; it is not included in this skeleton.','Verify section strength, threaded engagement, hardware/tool access and joint motion before any print release.'],'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [f,Path(__file__)]}}
(D/'central-bridge-primitives.json').write_text(json.dumps(r,indent=2)+'\n');print(len(pr),'solids',len(anchors),'real source screw axes')
