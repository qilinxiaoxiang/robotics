"""Bind the corrected IMU-clamp route to current canonical operation and geometry."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;G=D.parent;p=G.parent/'head-redesign-20261008/head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns)
raw=ns['raw'];data=ns['data'];prior=set();target=None
for module in data['modules']:
 for op in module['operations']:
  if op['id']=='imu-01':target=op;break
  prior.update(op['add'])
 if target:break
assert target is not None
assert target['add']==['imu_clamp','imu_board']
assert target['partApproachVectors']['imu_clamp']==[-28,0,0]
assert 'isolatedPartKeys' not in target
fixed=sorted(prior);m={'imu_clamp':ns['solid']('imu_clamp')};f={k:ns['solid'](k) for k in fixed}
positive=ns['samples'](m,f,target['partApproachVectors']['imu_clamp'],step=.25)
negative=ns['samples'](m,f,[28,0,0],step=.25)
assert len(positive['samples'])==113 and len(negative['samples'])==113
assert positive['peakContactsMm3']=={}
expected={'imu_clamp--power_support':1000,'imu_clamp--regulator_insert':300,'imu_clamp--regulator':40}
for key,minvol in expected.items():assert negative['peakContactsMm3'].get(key,0)>minvol,(key,negative['peakContactsMm3'])
sha=hashlib.sha256(raw).hexdigest();assert sha==hashlib.sha256((G/'full-build-data.json').read_bytes()).hexdigest()
r={'passed':True,'sourceSha256':sha,'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'operation':'imu-01','currentVectorBinding':{'field':'partApproachVectors.imu_clamp','value':target['partApproachVectors']['imu_clamp']},'fixed':fixed,'path':positive,'negativeOriginalPositiveX':negative,'samplesPerPath':113,'spacingMm':.25,'scope':'IMU clamp before board, against all earlier assembled source parts including washers/nuts; not a cable-route or physical-fit certification.','physicalFitVerified':False}
(D/'imu-corrected-path.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'sourceSha256':sha,'samplesPerPath':113,'positivePeak':positive['peakContactsMm3'],'negativePeak':negative['peakContactsMm3']},indent=2))
