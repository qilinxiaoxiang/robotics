"""Manufacturing candidate for a removable passive jaw cheek; no exterior enlargement."""
from pathlib import Path
import json,hashlib,sys,base64,numpy as np,trimesh,manifold3d as mf
OUT=Path(__file__).resolve().parent;src=OUT.parent/'head-fit-investigation.py';ns={'__file__':str(src)};exec(src.read_text().split("report={'problemIds'")[0],ns)
solid=ns['solid'];box=ns['box'];samples=ns['samples'];data=ns['data'];PIV=np.array([26.1,0,118.6146])
def pose(s,a):return s.translate(-PIV).rotate([0,a,0]).translate(PIV)
def cy(r,y0,y1,x,z):return mf.Manifold.cylinder(y1-y0,r,r,circular_segments=64,center=True).rotate([90,0,0]).translate([x,(y0+y1)/2,z])
def points(x,a):
 q=np.radians(a);R=np.array([[np.cos(q),0,np.sin(q)],[0,1,0],[-np.sin(q),0,np.cos(q)]]);return (R@(np.array(x)-PIV)+PIV).tolist()
jaw=solid('jaw_frame');pad=solid('lower_pad');S=solid('jaw_support');H=solid('head_bottom');M=solid('motor15')
arm=jaw^box([-100,-100,0],[150,-30.1,250]);main=jaw^box([-100,-29.9,0],[150,100,250]);joins=[];newbolts={}
for i,x in enumerate([60.,76.],1):
 arm_lug=box([x-2.8,-37,97.9],[x+2.8,-30.1,105.0]);main_lug=box([x-2.8,-29.9,97.9],[x+2.8,-23,105.0]);key=box([x-3,-30.2,98.9],[x+3,-27.6,100.1]);socket=box([x-3.15,-30.2,98.75],[x+3.15,-27.45,100.25])
 arm=arm+arm_lug+key;main=(main+main_lug)-socket
 arm=arm-cy(1.4,-55,-30,x,102.5)-cy(2.2,-55,-34,x,102.5)
 main=main-cy(1.05,-30.2,-25.5,x,102.5)
 bolt=cy(1.25,-34,-26,x,102.5)+cy(2,-35.5,-34,x,102.5);newbolts[f'jaw_cheek_screw_{i}']=bolt
 joins.append({'id':f'jaw-cheek-{i}','spec':'M2.5 x 8 TAP; head <=4 mm diameter x1.5 mm high; no nut','seatWorldMm':[x,-34,102.5],'outwardAxis':[0,-1,0],'pilotDiameterMm':2.1,'pilotDepthMm':4.4,'engagementMm':3.9,'tipMarginMm':.5,'headCounterboreDiameterMm':4.4,'clearanceHoleMm':2.8,'keyWidthMm':6,'keyProjectionMm':2.5,'keyClearanceMm':.15})
# Pad underside follows the new internal lugs; outer contact face is untouched.
envelope=jaw+pad
# Permit material inside the existing vertical outer skin, including its air gap.
# This closes internal holes without expanding either top or bottom exterior.
local_skin=envelope^box([55,-40,95],[81,-20,110])
vertical_fill=envelope+(local_skin.minkowski_sum(box([0,0,-3],[0,0,0])) ^ local_skin.minkowski_sum(box([0,0,0],[0,0,3])))
print('LOCAL_ENVELOPE_BUILT',flush=True)
main=main^vertical_fill;arm=arm^vertical_fill
added=(main+arm)-jaw
for x in [60.,76.]:
 pad=pad-box([x-3.2,-55,98.55],[x+3.2,-22.85,105.15])
pad=pad-jaw.minkowski_sum(box([-.02,-.02,-.02],[.02,.02,.02]))
shapes={'jaw_main':main,'jaw_passive_cheek':arm,'lower_pad_jaw_access':pad}
relief=mf.Manifold()
for k in ['motor14','motor15','head_roll_ring_a','head_roll_ring_b']:
 relief+=solid(k).minkowski_sum(box([-.15,-.15,-.15],[.15,.15,.15]))
print('PAD_AND_JAW_BUILT',flush=True)
H_original=H;H=H-relief-(S.minkowski_sum(box([-.02,-.02,-.02],[.02,.02,.02])) ^ box([-100,-100,0],[150,100,111.55]))
fixed={k:solid(k) for k in ['jaw_support','head_bottom','motor15','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']};fixed['head_bottom']=H;at30={k:pose(v,30) for k,v in shapes.items()};routes={}
for name,m,f,v in [('main_and_pad',{'jaw_main':at30['jaw_main'],'pad':at30['lower_pad_jaw_access']},fixed,[0,32,0]),('passive_cheek',{'jaw_passive_cheek':at30['jaw_passive_cheek']},fixed|{'jaw_main':at30['jaw_main'],'pad':at30['lower_pad_jaw_access']},[0,-32,0]),('pad_bench',{'pad':pad},{'jaw_main':main},[0,0,32])]:
 r=samples(m,f,v,step=.25);routes[name]=r;print('ROUTE',name,r['peakContactsMm3'],flush=True)
# Required pre-jaw ordering is tested independently, including the fixed neck.
neck={k:solid(k) for k in ['motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']}
for name,m,f,v in [('motor_support_bench',{'motor15':M},{'support':S},[0,0,-32]),('lower_shell',{'shell':H},neck,[0,0,-40]),('support_motor_group',{'support':S,'motor15':M},neck|{'shell':H},[0,0,40])]:
 r=samples(m,f,v,step=.25);routes[name]=r;print('PRE_ROUTE',name,r['peakContactsMm3'],flush=True)
# Tools are shaft envelopes, not threaded engagement material. All other parts,
# including the two new jaw pieces, are retained in the obstacle set.
tools=[];obstacles=fixed|at30
for j in joins:
 x,y,z=points(j['seatWorldMm'],30);shaft=cy(1.5,y-45,y-.5,x,z)
 hits={k:float((shaft^s).volume()) for k,s in obstacles.items() if (shaft^s).volume()>1e-6};tools.append({'id':j['id'],'shaftDiameterMm':3,'shaftLengthMm':44.5,'poseDegrees':30,'seatWorldMm':[x,y,z],'intersectionsMm3':hits});print('TOOL',j['id'],hits,flush=True)
# Full normal articulation, including the complete original head enclosure.
static={k:solid(k) for k in ['jaw_support','head_bottom','motor15','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b','head_cap','face_panel','upper_pad','eye_trim','pi']}
static['head_bottom']=H
angular=[]
for angle in np.linspace(0,30,121):
 hits={}
 for k,s in (shapes|newbolts).items():
  m=pose(s,float(angle))
  for q,f in static.items():
   vol=float((m^f).volume())
   if vol>1e-6:hits[k+'--'+q]=vol
 angular.append({'degrees':float(angle),'contactsMm3':hits})
print('ARTICULATION_PEAK', {k:max(r['contactsMm3'].get(k,0) for r in angular) for k in set().union(*(set(r['contactsMm3']) for r in angular))},flush=True)
# Write world STLs plus jaw_soft frame STLs for editable CAD integration.
sys.path.insert(0,str(ns['SIM']/'hardware-design-20260912/whole-robot-20260912/assembly'));from assembly_fk import fk
bodies,geoms=fk();inv=np.linalg.inv(bodies['jaw_soft']);parts=[]
for key,s in (shapes|{'head_bottom_clearance':H}|newbolts).items():
 m=s.to_mesh();mesh=trimesh.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False);file=key+'-world.stl';mesh.export(OUT/file);mesh.copy().apply_transform(inv).export(OUT/(key+'-jaw_soft.stl'))
 parts.append({'key':key,'name':{'jaw_main':'下颌主体','jaw_passive_cheek':'可拆被动轴侧颊','lower_pad_jaw_access':'下唇垫（内侧让位）','head_bottom_clearance':'原曲面下壳（内部座面让位）','jaw_cheek_screw_1':'侧颊 M2.5×8 TAP 1','jaw_cheek_screw_2':'侧颊 M2.5×8 TAP 2'}[key],'mesh':'jaw-access/'+file,'color':'#e5ba54' if key!='lower_pad_jaw_access' else '#e2bd75','volumeMm3':float(s.volume()),'connectedComponents':len(s.decompose()),'watertight':mesh.is_watertight})
report={'schemaVersion':2,'checked':'2026-10-08','scope':'Manufacturing candidate, full gates pending; no force, strength or material certification','sourceSha256':hashlib.sha256((ns['G']/'full-build-data.json').read_bytes()).hexdigest(),'newFastenerQuantity':2,'fasteners':joins,'routes':routes,'toolChecks':tools,'articulation':angular,'parts':parts,'originalSupportRetained':True,'originalHeadShellMeshUnchanged':False,'headShellExternalBoundsUnchanged':list(H.bounding_box())==list(H_original.bounding_box()),'headShellRemovedVolumeMm3':float((H_original-H).volume()),'headShellChange':'0.15 mm clearance about motor/ring seat envelopes and 0.02 mm about support foot seats below Z=111.55 mm; exterior verification recorded separately','originalBearingAxisRetained':True,'padRemovedVolumeMm3':float((solid('lower_pad')-pad).volume()),'fullHeadAssemblyPassed':False,'physicalStrengthVerified':False,'materialVerified':False}
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n')
fragment={'integrationReady':False,'replacementMeshes':{'jaw_frame':'jaw-access/jaw_main-world.stl','lower_pad':'jaw-access/lower_pad_jaw_access-world.stl'},'additionalParts':[{'key':'jaw_passive_cheek','mesh':'jaw-access/jaw_passive_cheek-world.stl','name':'可拆被动轴侧颊','color':'#e5ba54'}],'removedParts':[],'report':'jaw-access/report.json'}
(OUT/'viewer-fragment.json').write_text(json.dumps(fragment,indent=2)+'\n')
# Qualification is pair/phase specific. No global endpoint subtraction is used.
from scipy.spatial.transform import Rotation
from scipy.spatial import ConvexHull
def shaft(a,b,r=1.5):
 a=np.asarray(a);b=np.asarray(b);v=b-a;rot=Rotation.align_vectors([v/np.linalg.norm(v)],[[0,0,1]])[0].as_matrix();return mf.Manifold.cylinder(float(np.linalg.norm(v)),r,r,circular_segments=48).transform(np.column_stack([rot,a]))
def bounded_contact(m,f,maxvol,axis,maxwidth):
 it=m^f;bb=np.asarray(it.bounding_box()).reshape(2,3);return {'volumeMm3':float(it.volume()),'boundsMm':bb.tolist(),'allowed':bool(float(it.volume())<=maxvol and bb[1,axis]-bb[0,axis]<=maxwidth)}
allow_motor=bounded_contact(at30['jaw_main'],M,.149,1,.0011)
shell_it=S^H
shell_patches=[{'volumeMm3':float(c.volume()),'boundsMm':np.asarray(c.bounding_box()).reshape(2,3).tolist()} for c in shell_it.decompose()]
allow_support_shell={'volumeMm3':float(shell_it.volume()),'patches':shell_patches,'allowed':bool(shell_it.volume()<.00003 and all((p['boundsMm'][1][1]-p['boundsMm'][0][1]<.0011 and ((-39.5011<=p['boundsMm'][0][1]<=p['boundsMm'][1][1]<=-39.4999) or (-37.5001<=p['boundsMm'][0][1]<=p['boundsMm'][1][1]<=-37.4988))) for p in shell_patches))}
allow_support_ring=bounded_contact(S,neck['head_roll_ring_a'],.000008,0,.0000005)
accepted=[];failures=[]
allowed={'main_and_pad':{'jaw_main--motor15':allow_motor},'support_motor_group':{'support--shell':allow_support_shell,'support--head_roll_ring_a':allow_support_ring}}
for name,r in routes.items():
 for i,row in enumerate(r['samples']):
  for pair,volume in row['contactsMm3'].items():
   detail=allowed.get(name,{}).get(pair)
   if name=='support_motor_group' and pair=='support--head_roll_ring_a':
    offset=row['translationMm'] if 'translationMm' in row else None
    # Original ring plane is X=6; source float32 triangulation differs by <0.5 nm.
    z=40*(1-i/(len(r['samples'])-1));detail=bounded_contact(S.translate([0,0,z]),neck['head_roll_ring_a'],.000008,0,.0000005)
   if detail and detail['allowed'] and (i==len(r['samples'])-1 or (name=='support_motor_group' and pair=='support--head_roll_ring_a')):
    accepted.append({'route':name,'pair':pair,'phase':'final sample only' if i==len(r['samples'])-1 else 'source ring plane rounding at X=6 mm; no cross-plane travel',**detail})
   else:failures.append({'route':name,'sample':i,'pair':pair,'volumeMm3':volume})
# Recheck all seated motor-boundary contacts during actual joint motion.
angular_bounds=[]
for row in angular:
 for pair,vol in row['contactsMm3'].items():
  if pair!='jaw_main--motor15':failures.append({'articulation':row});continue
  a=row['degrees'];d=bounded_contact(pose(main,a),M,.149,1,.0011);angular_bounds.append({'degrees':a,**d})
  if not d['allowed']:failures.append({'articulationMotorContact':d})
# Existing support and output screws remain individually accessible in their
# actual assembly state. Output screws follow the motor shaft/jaw pose.
existing_tools=[]
for screw in data['screws']:
 if screw['id'].startswith('E-motor_support_frame-'):
  seat=np.array(screw['world_center_mm']);axis=np.array(screw['world_axis']);obs=fixed
 elif screw['id'].startswith('S15-horn-'):
  seat=np.array(points(screw['world_center_mm'],30));axis=Rotation.from_rotvec(np.array([0,np.radians(30),0])).apply(screw['world_axis']);obs=fixed|{'jaw_main':at30['jaw_main'],'pad':at30['lower_pad_jaw_access']}
 else:continue
 t=shaft(seat+axis*.5,seat+axis*45);hits={k:float((t^v).volume()) for k,v in obs.items() if (t^v).volume()>1e-6};existing_tools.append({'id':screw['id'],'seatWorldMm':seat.tolist(),'outwardAxis':axis.tolist(),'intersectionsMm3':hits})
 if hits:failures.append({'existingTool':existing_tools[-1]})
for t in tools:
 if t['intersectionsMm3']:failures.append({'newTool':t})
# The new pad may have pockets but no new part extends the original beak outline.
beak_extra=float(((main+arm+pad+sum(newbolts.values(),mf.Manifold()))-vertical_fill).volume())
if beak_extra>1e-4:failures.append({'beakEnvelopeExpandedMm3':beak_extra})
# Preserve the convex exposed outer curved wall; permit only internal seat cuts.
hm=H_original.to_mesh();hv=np.asarray(hm.vert_properties)[:,:3];hull=ConvexHull(hv);eq=hull.equations;eq=eq[eq[:,2]<.99]
removed=H_original-H;rv=np.asarray(removed.to_mesh().vert_properties)[:,:3];maxplane=float(np.max(rv@eq[:,:3].T+eq[:,3]))
if maxplane>=-.01:failures.append({'headExteriorModified':maxplane})
roof=[]
for x in [60.,76.]:
 for y in [-40,-37,-34,-31,-28,-25]:
  col=pad^box([x-.01,y-.01,105.15],[x+.01,y+.01,120]);roof.append({'xyMm':[x,y],'remainingRoofMm':float(col.volume())/.0004})
for p in parts:
 if not p['watertight'] or p['connectedComponents']!=1:failures.append({'mesh':p})
report.update({'acceptedContacts':accepted,'articulationMotorContactBounds':angular_bounds,'existingScrewTools':existing_tools,'candidateBeakOutsideOriginalVerticalSkinEnvelopeMm3':beak_extra,'headShellRemovedBoundsMm':list(removed.bounding_box()),'headShellRemovedMaximumConvexHullPlaneValueMm':maxplane,'headShellOriginalConvexCurvedExteriorPreserved':maxplane<-.01,'padRoofSamples':roof,'digitalFailures':failures,'digitalAssemblyPassed':not failures,'fullHeadAssemblyPassed':not failures,'motorOutputAssemblyPoseDegrees':30,'motionScopeDegrees':[0,30],'operationalMotionSource':{'path':'microduck-simulator/app/src/game/duck.js','symbol':'JAW_MAX_OPEN','radians':.32,'degrees':float(np.degrees(.32)),'assemblyPoseDegrees':30,'note':'Geometry checked through 30 degrees; the simulator operation limit remains 0.32 rad. The assembly pose does not extend the operational command limit.'},'physicalStrengthVerified':False,'materialVerified':False,'sourceUnchangedDuringRun':hashlib.sha256((ns['G']/'full-build-data.json').read_bytes()).hexdigest()==report['sourceSha256'],'bodyFrameToWorldMm':bodies['jaw_soft'].tolist()})
steps=[
 {'id':'jaw-access-shell','movingKeys':['head_bottom'],'points':[[0,0,-40],[0,0,0]],'fixedKeys':list(neck),'instruction':'未装下颌时，从下方放入曲面下壳；内部电机座和环座已留 0.15 mm 空间。'},
 {'id':'jaw-access-motor-bench','movingKeys':['motor15'],'points':[[0,0,-32],[0,0,0]],'fixedKeys':['jaw_support'],'isolated':True,'instruction':'在台面将 ID15 从下方放入完整原支架。'},
 {'id':'jaw-access-support','movingKeys':['jaw_support','motor15'],'points':[[0,0,40],[0,0,0]],'fixedKeys':list(neck)+['head_bottom'],'instruction':'把支架与 ID15 组合从上方放入下壳，先拧原有四颗 M2.5×6 支架螺丝。'},
 {'id':'jaw-access-pad-bench','movingKeys':['lower_pad'],'points':[[0,0,32],[0,0,0]],'fixedKeys':['jaw_frame'],'isolated':True,'instruction':'把带内侧让位槽的下唇垫装到下颌主体上；被动侧颊暂不安装。'},
 {'id':'jaw-access-main','movingKeys':['jaw_frame','lower_pad'],'points':[[0,32,0],[0,0,0]],'pose':{'keys':['jaw_frame','lower_pad'],'axis':[0,1,0],'pivot':PIV.tolist(),'degrees':30},'fixedKeys':list(fixed),'instruction':'断电，把 ID15 输出转到对应的张嘴 30° 装配姿态；下颌主体与垫从电机外侧装入，拧原有四颗输出螺丝。'},
 {'id':'jaw-access-cheek','movingKeys':['jaw_passive_cheek'],'points':[[0,-32,0],[0,0,0]],'pose':{'keys':['jaw_frame','lower_pad','jaw_passive_cheek'],'axis':[0,1,0],'pivot':PIV.tolist(),'degrees':30},'fixedKeys':list(fixed)+['jaw_frame','lower_pad'],'instruction':'从另一侧插入侧颊：原凸台进入完整同轴轴座，两只定位舌进入下颌主体。'},
 {'id':'jaw-access-lock','screwIds':[j['id'] for j in joins],'instruction':'从外侧工具槽拧入两颗新增 M2.5×8 TAP；无需螺母。不要靠螺丝把未对齐的侧颊拉合。'},
 {'id':'jaw-access-rotate','movingKeys':['jaw_frame','lower_pad','jaw_passive_cheek','jaw_cheek_screw_1','jaw_cheek_screw_2'],'rotation':{'axis':[0,1,0],'pivot':PIV.tolist(),'fromDegrees':30,'toDegrees':0},'instruction':'完整移动组一起闭合；后续张嘴也包含侧颊与两颗新螺丝。'}]
fragment.update({'integrationReady':False,'replacementMeshes':{'jaw_frame':'jaw-access/jaw_main-world.stl','lower_pad':'jaw-access/lower_pad_jaw_access-world.stl','head_bottom':'jaw-access/head_bottom_clearance-world.stl'},'additionalParts':[{'key':key,'mesh':'jaw-access/'+key+'-world.stl','name':'可拆被动轴侧颊' if key=='jaw_passive_cheek' else 'M2.5×8 TAP 侧颊螺丝','color':'#e5ba54' if key=='jaw_passive_cheek' else '#7c8490'} for key in ['jaw_passive_cheek',*newbolts]],'assemblySteps':steps,'movingJawKeys':['jaw_frame','lower_pad','jaw_passive_cheek',*newbolts],'newFasteners':joins,'acceptance':{'digitalAssemblyPassed':not failures,'physicalStrengthVerified':False,'materialVerified':False,'sourceGeometryContactsExplicitlyBounded':True}})
(OUT/'report.json').write_text(json.dumps(report,indent=2)+'\n');(OUT/'viewer-fragment.json').write_text(json.dumps(fragment,indent=2)+'\n')
print('GATE',json.dumps({'passed':not failures,'failures':failures,'outerHullClearanceMm':-maxplane,'beakEnvelopeExtraMm3':beak_extra},indent=2),flush=True)

if failures:raise SystemExit(1)
