from pathlib import Path
import json,hashlib,numpy as np,base64
import s_bend_lead_search as s
c=s.c;D=Path(__file__).resolve().parent
candidates=[]
for lead in [1.,1.2,1.3]:
 r=c.make(top=c.pi[1]+3+lead+.3+.5,width=5,lead=lead);st=c.self_test(r[4],r[3]);candidates.append({'row':r[-1],'self':st});print('LEAD',lead,r[-1]['intersectionsMm3'],flush=True)
# Retain1.0mm free straightlead rather than publish a shape at its own fit limit.
lead=1.;r=c.make(top=c.pi[1]+3+lead+.3+.5,width=5,lead=lead);cable,mesh,points,arc,vv,row=r;st=c.self_test(vv,arc);assert not row['intersectionsMm3'] and not st['nonadjacentCellIntersections']
# Test geometric dimensions around the same centerline without assuming real
# material tolerances. Both intermediate body width/thickness and routed bands
# are varied; end16/11.5 dimensions remain receiver conventions.
sensitivity=[]
for w,t in [(5,.3),(5.1,.4),(5.2,.5),(5.4,.7),(5.6,.9)]:
 q=c.make(top=row['topYmm'],width=w,thick=t,lead=lead);ss=c.self_test(q[4],q[3]);sensitivity.append({'middleWidthMm':w,'totalThicknessMm':t,'hits':q[-1]['intersectionsMm3'],'nonlocalGapMm':ss['minimumNonlocalSolidGapMm'],'selfPairCount':len(ss['nonadjacentCellIntersections'])})
moving=['curved_cap','openrb','audio-roof-posts','speaker','amplifier','speaker-cradle','speaker-keeper','cap-eight-screw-heads-four-nuts'];closure=[];peak={}
for dz in np.arange(40,-.001,-.25):
 hit={}
 for name in moving:
  vol=max(0,(c.obs[name].translate([0,0,float(dz)])^cable).volume())
  if vol>1e-5:hit[name]=vol;peak[name]=max(peak.get(name,0),vol)
 closure.append({'offsetZmm':float(dz),'intersectionsMm3':hit})
# Driver approaches are the declared detached-face operation, cable temporarily
# laid aside/unlatched. Additional geometric check with nominal cable in place.
ret_report=json.loads((c.R/'camera-retainer-report.json').read_text());driver_hits={}
for sc in ret_report['fasteners']:
 center=np.array(sc['worldHeadSeatMm']);axis=np.array(sc['outwardAxis']);origin=center+axis*1.55
 tool=c.mf.Manifold.cylinder(45,1.5,circular_segments=48).rotate([0,90,0]).translate([min(origin[0],origin[0]+45*axis[0]),origin[1],origin[2]])
 driver_hits[sc['id']]=max(0,(tool^cable).volume())
# Pi latch work is deliberately before board attachment. Exact latch/finger
# geometry unavailable: require it explicitly, never erase components to pass.
report={'date':'2026-10-08','status':'CONDITIONAL_DIGITAL_ROUTE_WITH_MEASUREMENT_AND_RETENTION_GATES','parameters':row,'sourceCable':'ExistingSC1892,200mm15-to22, no replacement','selfCheck':st,'stiffenerLeadSensitivity':candidates,'dimensionalReceivingSensitivity':sensitivity,'closure':{'moving':moving,'stepMm':.25,'samples':closure,'peakIntersectionsMm3':peak,'passes':not bool(peak)},'cameraScrewShaftIntersectionMm3':driver_hits,'clearanceInterpretation':'0.5mm is exact nominal gap between separated ribbon sections. It is not measured tolerance, a clamp retention proof, or a global0.5mm shell clearance guarantee.','stiffenerReceivingConditions':{'maximumMiniStiffenerProjectionOutsideClosedLatchMm':1.,'assumedInsertedMiniTipMm':4.4,'cameraOutsideStraightBeforeFirstBendMm':35.9-3-c.cam[1],'cameraEndWidthMm':16,'miniEndWidthMm':11.5,'bothTipPlanesNeedMeasurement':True},'materialReceivingConditions':{'bodyMaximumWidthMm':5.,'totalThicknessMm':.3,'staticBendRadiusMm':3.,'manufacturerMinBendRadiusKnown':False,'physicalBendTestDone':False,'isManufacturerSpecification':False},'assemblySequence':['Keep originalpublishedcameraorientation;this90degvariantisnotreleased.','For theconditionalvariant,onbenchinstallcameraontoitsframe,thencompleteall6frame/facescrews.','OpenroutingretainersmustbeavailablebeforelatchingfreeFFCends;do notthreadclosedclipsorclosedheadholes.','Latchcamera15pinendwhilePiabsent;holdFFConwideuncreasedsupportandformafulllengthlooseU/Sloop.','WithPiunmountedandsupported,open22pinlatch,insertstraightandlock;verifyrigidtabprotrusion<=1mm,thenmountPi.','Onlyafteractualcablegeometryandbendacceptanceandpositiveclipretentionaretickedorverifiedcanpopulatedcapdescend;do notforcecableintothe0.5mmnominalgap.'],'remainingMechanicalGate':'Retention clips/keeper locations must hold the two longlanes andthetopSsegment without compressingFFC. No new clip geometry or clamp-load validation is claimed.','latchAccessBoundary':'Actuallatchbody/travelandfingertipenvelopearenotinZeroWsourceCAD. Benchunmountedboardsequencepreventsshellocclusionbutdoesnotcertifytheunknownlatchgeometry.','physicalFitVerified':False,'assemblyRelease':False,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*c.files.values(),c.G/'full-build-data.json',c.R/'camera-retainer-report.json',D/'conditional_u_route.py',D/'s_bend_lead_search.py']}}
# Official PCN36 invalidates this historical5mm experiment as SC1892.
report.update(status='INVALID_FOR_SC1892_OFFICIAL_BODY_WIDTH', assemblyAcceptance=False, invalidatedBy='sc1892-official-spec.json', invalidationReason='The5mmbody contradicts official11.5mmRev2and16mmRev1; preserve numericalhistory only.')
(D/'conditional-S-verification.json').write_text(json.dumps(report,indent=2)+'\n');mesh.export(D/'sc1892-200mm-conditional-S-world.stl')
part={'key':'eye_camera_sc1892_conditional_S','name':'Invalid for SC1892: historical5mm S/U experiment','color':'#d24b45','moduleId':'camera','partKind':'cable','geometryKind':'conditional-routing-candidate','description':'Only assumed5mm x0.3mm body,R3,and<=1mm mini rigidtaboutside latch. Notphysicalfit or assemblyrelease. Requires90degcamera candidate.','positionB64':base64.b64encode(np.asarray(mesh.vertices,dtype='<f4').tobytes()).decode(),'indexB64':base64.b64encode(np.asarray(mesh.faces,dtype='<u4').tobytes()).decode(),'bounds':mesh.bounds.tolist(),'center':mesh.bounds.mean(axis=0).tolist(),'sourceTransformWorld':np.eye(4).tolist(),'triangles':len(mesh.faces),'approachVector':[0,0,0]}
(D/'conditional-S-viewer-fragment.json').write_text(json.dumps({'status':'INVALID_FOR_SC1892_OFFICIAL_BODY_WIDTH','diagnosticOnly':True,'invalidatedBy':'sc1892-official-spec.json','conditionalOnly':True,'physicalFitVerified':False,'requiresCameraVariant':'rotated-camera-candidate','append':[part],'replacements':[]},separators=(',',':'))+'\n')
print(json.dumps({'nominal':row['intersectionsMm3'],'closurePeak':peak,'selfGapMm':st['minimumNonlocalSolidGapMm'],'dimensionalSensitivity':sensitivity,'driverHits':driver_hits},indent=2));assert not peak;assert max(driver_hits.values())<1e-5
