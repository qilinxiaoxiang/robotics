"""Restore original material removed by the recorded rear USB cutter only."""
from pathlib import Path
import os,sys,json,types,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
P=Path(__file__).resolve().parent;W=P.parents[1];R=W.parent;H=R/'head-redesign-20261008';S=W/'roof-wiring-stage'
sys.path.insert(0,str(H/'gpio-audio-repair'));import precision_mesh as pm
c=types.SimpleNamespace(np=np,tm=tm,mf=mf)
paths={'native':H/'curved-head/community-curved-head-world.stl','current':S/'roof/head-cap-roof-restored-candidate-world.stl','oldUsbReceiving':H/'usb-access/openrb-usb-c-receiving-world.stl','cutDirection':H/'usb-access/usb-report.json','cutGenerator':H/'curved-head/finalize_cap.py'}
native=pm.load(c,paths['native']);current=pm.load(c,paths['current']);usb=pm.load(c,paths['oldUsbReceiving']);direction=np.array(json.loads(paths['cutDirection'].read_text())['outwardAxis'])
# Reconstruct the original cutter with a 0.02 mm overlap rim wholly in native material.
selector=mf.Manifold.batch_hull([usb,usb.translate(direction*30)]).minkowski_sum(mf.Manifold.cube([1.04]*3,True))
patch=native^selector;result=(current+patch).as_original().simplify(0.000001);assert result.status()==mf.Error.NoError and len(result.decompose())==1
out=P/'cap-crown-and-rear-restored-world.stl';io=pm.export(c,result,out);rb=pm.load(c,out)
checks={'existingMaterialRemovedMm3':max(0,(current-rb).volume()),'addedOutsideOriginalMaterialMm3':max(0,((rb-current)-native).volume()),'missingRequiredRearPatchMm3':max(0,(patch-rb).volume()),'addedOutsideRecordedRearCutMm3':max(0,((rb-current)-selector).volume())}
numericalVolumeBoundMm3=max(1e-5,float(current.surface_area()+rb.surface_area())*0.000001)
assert all(v<numericalVolumeBoundMm3 for v in checks.values()),checks
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
report={'status':'REAR_AND_CROWN_MATERIAL_RESTORED_COMPONENT_ONLY','sourceHashes':{str(p):sha(p)for p in paths.values()},'scriptSha256':sha(Path(__file__)),'output':str(out),'outputSha256':sha(out),'addedRearMaterialMm3':max(0,(rb-current).volume()),'checks':checks,'kernelSimplificationToleranceMm':0.000001,'numericalVolumeBoundMm3':numericalVolumeBoundMm3,'toleranceMeaning':'Area times explicit 1e-6mm export simplification tolerance; residuals reported, not a collision waiver.','export':io,'headAssemblyAccepted':False,'reason':'Original crown and rear cut restored; placement of populated boards, internal USB, wire installation and enclosure closure remain separate checks. No hole is excused by watertightness.'}
(P/'rear-restoration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
