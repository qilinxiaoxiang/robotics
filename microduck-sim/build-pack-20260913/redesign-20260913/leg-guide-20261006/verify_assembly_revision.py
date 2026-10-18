"""Current digital-guide regression gate; never certifies physical assembly."""
from pathlib import Path
import hashlib,json,math,importlib.util
D=Path(__file__).resolve().parent
read=lambda name:json.loads((D/name).read_text())
sha=lambda name:hashlib.sha256((D/name).read_bytes()).hexdigest()

def service_frame_issues(data,service,frames):
 """Compare observed DOM positions with independently calculated step positions."""
 issues=[];ops=service['module']['operations'];screws={s['id']:s for s in data['screws']}
 expected_frames={(i,p) for i in range(len(ops)) for p in [0,50,100]}
 observed=[(f.get('operation'),f.get('progress')) for f in frames]
 if len(observed)!=len(expected_frames) or set(observed)!=expected_frames:
  issues.append('Service browser frames must contain each operation at 0/50/100 exactly once')
 def offsets(rows,expected):
  return (isinstance(rows,list) and len(rows)==len(expected) and
          len({r.get('key') for r in rows})==len(rows) and
          all(r.get('key') in expected and len(r.get('offset',[]))==3 and
              all(isinstance(x,(int,float)) and math.isfinite(x) and abs(x-y)<=1e-7
                  for x,y in zip(r['offset'],expected[r['key']])) for r in rows))
 for f in frames:
  label=f"Torso service op {f.get('operation')} at {f.get('progress')}%"
  if (f.get('operation'),f.get('progress')) not in expected_frames:continue
  try:
   op=ops[f['operation']];progress=f['progress']/100;rb=f['readback'];v=rb['viewport']
   assert not rb['error'] and rb['title']==op['title']
   assert v['buildSection']=='torso' and v['serviceWorkflow']=='true' and int(v['stage'])==1
   assert int(v['operation'])==f['operation'] and abs(float(v['motionProgress'])-progress)<=1e-7
   assert v['playing']=='false' and int(v['renderedFrames'])>0
   assert v['screwAction']==op.get('screwAction','install')
   visible=json.loads(v['visibleParts']);wanted=op['visiblePartKeys']
   assert len(visible)==len(set(visible))==len(set(wanted)) and set(visible)==set(wanted)
   active=[s['id'] for s in data['screws'] if s['id'] in op['screwIds']]
   markers=json.loads(v['visibleScrews']);assert len(markers)==len(active) and set(markers)==set(active)
   expected={};retained={}
   if 'motionWaypoints' in op:
    points=op['motionWaypoints']['points'];lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
    distance=progress*sum(lengths);index=0
    while index<len(lengths)-1 and distance>lengths[index]:distance-=lengths[index];index+=1
    fraction=min(1,distance/lengths[index]) if lengths[index] else 1
    vector=[a+(b-a)*fraction for a,b in zip(points[index],points[index+1])]
    assert set(op['motionWaypoints']['movingKeys'])==set(op['moveKeys'])
    expected={key:vector for key in op['motionWaypoints']['movingKeys']}
    retained={sid:vector for sid in op.get('movingScrewIds',[])};expected.update(retained)
   elif active:
    # Screws move in source screw-list order, one at a time. Removal goes
    # outward from zero; installation and refastening end at zero.
    assert not op.get('moveKeys') and not op.get('add')
    for index,sid in enumerate(active):
     local=max(0,min(1,progress*len(active)-index))
     travel=local if op.get('screwAction')=='remove' else 1-local
     expected[sid]=[x*18*travel for x in screws[sid]['world_axis']]
   else:
    # The only stationary setup is the plate on the bench; never accept a
    # generic approach animation for an unreviewed new service operation.
    assert op['id']=='torso-service-11' and op['add']==['torso_base']
    assert op['partApproachVectors']['torso_base']==[0,0,0]
    expected={'torso_base':[0,0,0]}
   assert offsets(json.loads(v['motionParts']),expected)
   assert offsets(json.loads(v['movingScrews']),retained)
  except (AssertionError,KeyError,ValueError,TypeError,IndexError):
   issues.append(label+' fails scene, direction, whole-group or retained-screw readback')
 return issues

def check_service_and_imu(check,ui,datahash,htmlhash,current_html):
 data=read('full-build-data.json');service=read('non-head-review/torso-service-steps.json')
 spec=importlib.util.spec_from_file_location('service_bundle_gate',D/'bundle_guide.py')
 binder=importlib.util.module_from_spec(spec);spec.loader.exec_module(binder)
 try:
  binder.validate_torso_service(data,service,D/'non-head-review/torso-service-steps.json')
  binding_ok=True
 except (ValueError,KeyError,OSError):binding_ok=False
 check(binding_ok,'Torso service source, payload, verifier and input hashes pass the bundle binder')
 revision_path=D.parent/'fastener-review-20261008/fastener-patch-proposal.json'
 effective=binder.apply_fastener_revision(data,json.loads(revision_path.read_text()),revision_path)
 service=binder.apply_effective_torso_service(data,service,effective)
 independent=read('non-head-review/service-independent-review.json')
 bindings=independent.get('sourceBindings',{})
 required={'full-build-data.json','viewer.js','bundle_guide.py','non-head-review/torso-service-steps.json','non-head-review/torso-service-verification.json','non-head-review/verify_torso_service.py'}
 check(independent.get('acceptedIndependentSourceReview') is True and required<=set(bindings) and all(sha(p)==h for p,h in bindings.items()),'Independent torso service review binds every current source')
 try:embedded,_=json.JSONDecoder().raw_decode(current_html.split('const TORSO_SERVICE=',1)[1])
 except (ValueError,IndexError):embedded=None
 check(embedded==service,'Deployed bundle contains exactly the accepted torso service payload')
 frames=[f for f in ui['checks'] if f['kind']=='torso service frame']
 check(ui['bundleSha256']==htmlhash and ui['dataSha256']==datahash,'Service browser frames bind the exact current deployed bundle')
 frame_errors=service_frame_issues(effective,service,frames)
 check(len(service['module']['operations'])==28 and len(frames)==84 and not frame_errors,'All 28 service operations match live 0/50/100 scenes, directions and retained screws')
 for error in frame_errors:check(False,error)
 imu=read('non-head-review/imu-corrected-path.json');prior=set();target=None
 for module in data['modules']:
  for op in module['operations']:
   if op['id']=='imu-01':target=op;break
   prior.update(op['add'])
  if target:break
 check(imu.get('passed') is True and imu['sourceSha256']==datahash and imu['scriptSha256']==sha('non-head-review/verify_imu_path.py'),'IMU corrected-route evidence binds current data and verifier')
 check(target is not None and target.get('partApproachVectors',{}).get('imu_clamp')==[-28,0,0] and 'isolatedPartKeys' not in target and set(imu['fixed'])==prior and imu['currentVectorBinding']=={'field':'partApproachVectors.imu_clamp','value':[-28,0,0]},'IMU negative-X approach preserves every previously assembled obstacle')
 positive=imu['path'];negative=imu['negativeOriginalPositiveX']
 for name,path,sign in [('positive',positive,-1),('negative control',negative,1)]:
  samples=path['samples']
  valid=(path['start']==[28*sign,0,0] and path['stop']==[0,0,0] and path['spacingMm']==.25 and len(samples)==113 and all(all(abs(a-b)<=1e-7 for a,b in zip(row['translation'],[sign*(28-i*.25),0,0])) for i,row in enumerate(samples)))
  check(valid,'IMU '+name+' retains all 113 quarter-millimetre samples')
 check(not positive['peakContactsMm3'] and all(not row['contactsMm3'] for row in positive['samples']),'Corrected IMU route is clear at every sampled pose')
 limits={'imu_clamp--power_support':1000,'imu_clamp--regulator_insert':300,'imu_clamp--regulator':40}
 check(all(negative['peakContactsMm3'].get(pair,0)>limit for pair,limit in limits.items()) and any(row['contactsMm3'] for row in negative['samples']),'Original positive-X IMU route still reproduces its three blocking collisions')
 return {'serviceFrameCount':len(frames),'serviceFrameErrors':frame_errors,'independentReviewSha256':sha('non-head-review/service-independent-review.json'),'serviceVerificationSha256':sha('non-head-review/torso-service-verification.json'),'imuVerificationSha256':sha('non-head-review/imu-corrected-path.json')}

def main():
 errors=[];checks=[]
 def check(ok,label):
  checks.append({'check':label,'passed':bool(ok)})
  if not ok:errors.append(label)
 datahash=sha('full-build-data.json');htmlhash=sha('LEFT-LEG.html')
 for name,passed,hashkey in [
 ('leg-assembly-access.json','passed','dataSha256'),('nonleg-access-audit.json','passed','dataSha256'),
 ('nut-approach-verification.json','passed','dataSha256'),('full-guide-review.json','passed','full_data_sha256'),
 ('audit-20261008/head-articulation-access.json','passed','sourceDataSha256'),
 ('audit-20261008/head-stopped-routes.json','passed','sourceSha256'),
 ('audit-20261008/leg-final-contacts.json','passedScopedContactReview','sourceDataSha256')]:
  r=read(name);check(r[passed] and r[hashkey]==datahash,name+' passes on current source')
 paths=read('audit-20261008/final-motion-paths.json')
 check(paths['dataSha256']==datahash and paths['crossings']==0,'No unhandled traversal in current sampled-motion investigation')
 check(paths['maxStepMm']==.25,'Translation sampling no greater than 0.25 mm')
 # Final interference is preserved as an unresolved/source-contact finding, never waived by the crossing count.
 check(paths['dataSha256']==datahash,'Motion scan binds current assembly metadata; its visible-module scope remains explicit')
 contacts=[r for r in paths['rows'] if r['status']=='source-final-contact']
 deployment=read('audit-20261008/deployment.json')
 check(deployment['httpStatus']==200 and deployment['matched'] and deployment['localSha256']==deployment['servedSha256']==htmlhash,'Original live URL serves exact current bundle')
 ui=read('assembly-revision-ui-20261008.json');by={c['kind']:c for c in ui['checks']}
 # A header-only navigation addition can reuse the prior assembly-control receipt
 # only when reversing that exact addition reproduces the ENTIRE previous bundle.
 current_html=(D/'LEFT-LEG.html').read_text()
 added='<div class="row"><a id="head-review-link" href="/HEAD-EYE-REVIEW.html">Eye camera review · Zero reference</a><span class="tag">5 motors · existing printed parts · unpowered assembly</span></div>'
 original='<span class="tag">5 motors · existing printed parts · unpowered assembly</span>'
 prior_hash=hashlib.sha256(current_html.replace(added,original,1).encode()).hexdigest()
 nav_path=D/'hosting/head-review-navigation-acceptance.json'
 nav=json.loads(nav_path.read_text()) if nav_path.exists() else {}
 header_only=(current_html.count(added)==1 and prior_hash==ui['bundleSha256'] and nav.get('bundleSha256')==htmlhash and nav.get('accepted') is True)
 check((ui['bundleSha256']==htmlhash or header_only) and ui['dataSha256']==datahash,'Browser receipt bound to deployed source or exact header-only addition with live navigation receipt')
 modules=[c for c in ui['checks'] if c['kind']=='moduleNavigation']
 check(len(modules)==10 and all(not c['readback']['error'] for c in modules),'All ten modules render')
 for prefix,sign in [('Left leg',-1),('Right leg · IDs1–5',1)]:
  for label,y in [('start',28*sign),('middle',14*sign),('end',0)]:
   parts=json.loads(by[prefix+' knee '+label]['readback']['viewport']['motionParts'])
   check(len(parts)==5 and all(p['offset']==[0,y,0] for p in parts),prefix+' knee '+label+' carries complete group')
  visible=json.loads(by[prefix+' exposed yaw screws']['readback']['viewport']['visibleParts'])
  check(len(visible)==2,prefix+' yaw fastens before roll obstruction')
 for label,z in [('start',-40),('scrub middle',-30.112637519836426),('end',-20.22527503967285)]:
  key='head shell stopped route '+label if label!='scrub middle' else 'head shell scrub middle'
  v=by[key]['readback']['viewport'];p=json.loads(v['motionParts'])
  check(abs(p[0]['offset'][2]-z)<1e-7 and v['targetReached']=='false','Shell '+label+' preserves measured stop')
 check(by['head shell pause']['readback']['viewport']['playing']=='false','Pause stops playback')
 check('motionStopped' not in by['conditional support screws after actual fit']['readback']['viewport'],'Step change clears stopped-state metadata')
 for k in ['head cap work side jaw30 upperpad absent','head cap reverse side jaw30']:
  v=by[k]['readback']['viewport'];check(json.loads(v['fixedPoses'])[0]['degrees']==30 and 'upper_pad' not in json.loads(v['visibleParts']),k)
 for k,offset in [('upper pad segmented start',[40,0,-3]),('upper pad end',[0,0,0])]:
  check(json.loads(by[k]['readback']['viewport']['motionParts'])[0]['offset']==offset,k)
 check('Route and close in this order' in by['camera wiring route and closure']['snapshot'],'Camera wiring shows routing before closure')
 check('heading "Connect the torso IMU"' in by['IMU before cover jumps to stage8']['snapshot'],'IMU assembly jumps to correct wiring stage')
 service_and_imu=check_service_and_imu(check,ui,datahash,htmlhash,current_html)
 out=dict(problemIds=['P5','P6'],passedDigitalRevision=not errors,errors=errors,checks=checks,dataSha256=datahash,bundleSha256=htmlhash,sourceContactFindings=contacts,physicalAssemblyVerified=False,completeRigidAssemblyPathVerified=False,scope='Checks repaired digital guide, source identity, scoped tool/path regressions and observed live controls. Source mating interference, stopped full-entry routes, connector-body/cable clearance and physical tool fit remain separate bench checks.')
 out['serviceAndImuAcceptance']=service_and_imu
 (D/'audit-20261008/revision-acceptance.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'passedDigitalRevision':not errors,'checks':len(checks),'errors':errors,'sourceContactFindings':len(contacts),'physicalAssemblyVerified':False}))
 raise SystemExit(bool(errors))
if __name__=='__main__':main()
