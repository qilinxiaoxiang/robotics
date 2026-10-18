from pathlib import Path
import json,base64,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;R=D.parents[1];S=R.parents[1];C=D.parent/'central-cad';A=S/'hardware-design-20260912/whole-robot-20260912/assembly/compact-battery';manifest=json.loads((D/'fusion-import-manifest.json').read_text());hashes={};cache={}
def load(k):
 if k not in cache:
  p=C/'current-mesh'/f'{k}.json';hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();d=json.loads(p.read_text());m=trimesh.Trimesh(np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True);s=mf.Manifold(mf.Mesh(np.array(m.vertices,np.float32),np.array(m.faces,np.uint32)));assert m.is_watertight and s.status()==mf.Error.NoError,k;cache[k]=(m,s)
 return cache[k]
def gap(a,b):return max(np.max(a[0]-b[1]),np.max(b[0]-a[1]))
rows=[]
for new in ['regulator','regulator_insert']:
 m,s=load(new)
 for p in manifest['parts']:
  key=p['key']
  if key==new:continue
  bb=np.array(p['expectedFinalBoundsMm']);sep=gap(m.bounds,bb)
  if sep>0:rows.append({'moving':new,'fixed':key,'intersectionMm3':0,'proof':'separated AABBs','separationLowerBoundMm':float(sep)});continue
  om,os=load(key);hit=s^os;assert hit.status()==mf.Error.NoError;rows.append({'moving':new,'fixed':key,'intersectionMm3':float(hit.volume()),'proof':'valid mesh solid intersection','minimumGapMm':float(s.min_gap(os,2)),'gapCappedAtMm':2})
board,bs=load('regulator');insert,is_=load('regulator_insert');mount,ms=load('power_support')
originalP=A/'original-power-support-body.stl';original=trimesh.load(originalP,force='mesh');os=mf.Manifold(mf.Mesh(np.array(original.vertices,np.float32),np.array(original.faces,np.uint32)));assert original.is_watertight and os.status()==mf.Error.NoError
comparison={'originalCommunitySupportBoundsMm':original.bounds.tolist(),'retainedIntegratedSupportBoundsMm':mount.bounds.tolist(),'originalVolumeMm3':float(os.volume()),'integratedVolumeMm3':float(ms.volume()),'boardVsOriginalSupportMm3':float((bs^os).volume()),'insertVsOriginalSupportMm3':float((is_^os).volume()),'meaning':'Provenance comparison only. Do not replace the already modeled/printed integrated support in this baseline restoration.'}
paths=[]
for name,moving,obstacle,start in [('board-into-loose-insert',bs,is_,[0,0,28]),('wired-insert-into-support',bs+is_,ms,[-28,0,0])]:
 vols=[]
 for u in np.linspace(0,1,57):
  moved=moving.translate(np.array(start)*(1-u));hit=moved^obstacle;assert hit.status()==mf.Error.NoError;vols.append(float(hit.volume()))
 paths.append({'name':name,'samples':57,'stepMm':.5,'startOffsetMm':start,'maxIntersectionMm3':max(vols),'scope':'Rigid modeled boxes/carrier only. Prewired leads and solder fillets not modeled; no continuous-path or full harness acceptance.'})
old=R/'mechanical-geometry-verification.json';e=json.loads(old.read_text());sources=[D/'fusion-import-manifest.json',Path(__file__),old,R/'mechanical_geometry_check.py',A/'design.json',originalP,S/'hardware-design-20260912/whole-robot-20260912/assembly/build_compact_battery.py']
report={'status':'ORIGINAL SPACING RESTORED; EXISTING CONVERTER MOUNT REUSED','date':'2026-10-09','expectedStaticPairs':2*(len(manifest['parts'])-1),'completedStaticPairs':len(rows),'staticClear':all(r['intersectionMm3']<1e-7 for r in rows),'rows':rows,'boardToCarrierGapMm':float(bs.min_gap(is_,2)),'boardToSupportGapMm':float(bs.min_gap(ms,10)),'paths':paths,'sourceSupportComparison':comparison,'manufacturerEvidence':{'url':'https://www.dfrobot.com/product-2907.html','verified':'2026-10-09','publishedDimensionsMm':[30,26,8],'retention':'Existing insert uses insulating edge liner and ties. The supplier module is a solder-pad board, no plug-body CAD or installed lead shape is represented.','thermal':'Manufacturer back thermal pad is intended to couple to copper heat spreading; this local fit does not validate loaded thermal performance.'},'retentionGeometry':{'carrierXYZMm':[12.4,31,61],'boardXYZMm':[8,26,30],'boardSideClearanceMm':.3,'backLipClearanceMm':.3,'bottomClearanceMm':.6,'frontFrameClearanceMm':2,'bandCentersZMm':[-30.821742128,5.877257872],'supportSlotOpeningMm':[2.1,6.2],'bandSource':'Existing design specified two4.8mm bands, not a newly invented clamp. Actual tie position must avoid components and pads.'},'assembly':['Wire and insulate the module while the insert is off robot and both module faces are accessible.','Seat board in loose insert; no converter mounting screws required.','Offer wired insert from negativeX into the original battery bay, before rear IMU cover/cable closure; use existing two band stations.','Keep soldered lead exits and the rear thermal surface open. Do not show invented seated USB/JST plugs on this solder-pad module.'],'priorEvidence':{'path':str(old),'passed':e['passed'],'sampledFrames':e['sampled_frames'],'pairChecks':e['pair_checks'],'scope':'Historical source trajectory and then-current scene, retained evidence only; not rerun/rebranded as current full robot motion acceptance.'},'physicalFitAccepted':False,'newPrintRequiredByThisRestoration':False,'connectorClearanceAccepted':False,'connectorBoundary':'Existing8x26x30box is full published module size; populated details/soldered wire exit not native CAD. Exact solder-pad coordinates and wire attachment side are not established by a box. Bench prewiring avoids an in-situ solder-tool access claim.','sourceHashes':{**hashes,**{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources}}}
(D/'converter-local-fit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['expectedStaticPairs','completedStaticPairs','staticClear','boardToCarrierGapMm','boardToSupportGapMm','paths','sourceSupportComparison']},indent=2))
