"""Fast source/order/coverage gate, including deliberately broken candidates."""
import copy,hashlib,json
from pathlib import Path
from check_delta import data,D,G
canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify(overlay,modules,check_files=True):
 assert overlay['integrationReady'] is True
 if check_files:
  for path,digest in overlay['sourceHashes'].items():assert sha(Path(path))==digest,path
 byid={m['id']:copy.deepcopy(m) for m in modules}
 assert len(overlay['operationPatches'])==90
 for patch in overlay['operationPatches']:
  op=next(o for o in byid[patch['moduleId']]['operations'] if o['id']==patch['operationId'])
  assert hashlib.sha256(canonical(op)).hexdigest()==patch['expectedOperationSha256'],patch['operationId']
  op.update(patch['set'])
 for mid,order in overlay['moduleOrders'].items():
  ops=byid[mid]['operations'];assert len(order)==len(set(order))==len(ops) and set(order)=={o['id'] for o in ops}
  byid[mid]['operations']=[next(o for o in ops if o['id']==k) for k in order]
 for side in ['left','right']:
  mid=side+'-leg';ops=byid[mid]['operations'];order=[o['id'] for o in ops];get=lambda n:next(o for o in ops if o['id']==f'{mid}-{n:02}')
  assert order.index(f'{mid}-12')<order.index(f'{mid}-09')<order.index(f'{mid}-10')
  assert order.index(f'{mid}-14')<order.index(f'{mid}-15') and order.index(f'{mid}-18')<order.index(f'{mid}-19')
  foot='foot' if side=='left' else 'right_foot';motor='motor6' if side=='left' else 'motor1'
  assert foot in get(9)['moveKeys'] and f'{side}-foot-retainer' in get(9)['movingScrewIds']
  assert len(get(9)['movingScrewIds'])==8 and get(9)['movingScrewPartKeys'][f'{side}-foot-retainer']==('ankle' if side=='left' else 'right_ankle')
  assert 'thigh' not in get(12)['isolatedPartKeys'] and 'right_thigh' not in get(12)['isolatedPartKeys']
  assert get(7)['requiresPhysicalFit'] and get(11)['motionStop']['stop'][2]<0
  assert get(7)['motionEvidence']['status']=='physical-fit-checkpoint' and get(11)['motionEvidence']['status']=='measured-contact-stop'
 for m in byid.values():
  for o in m['operations']:
   assert all(o['tutorial'].get(k) for k in ['prepare','assemble','check'])
   assert set(o['movingScrewIds'])==set(o['movingScrewPartKeys'])
 neck=next(o for o in byid['neck']['operations'] if o['id']=='neck-14')
 assert neck['toolAccessModels']['S10-case-071']['handleAxis']==[0,1,0]
 assert neck['toolAccessModels']['S05-case-075']['handleAxis']==[0,-1,0]
 torso=next(o for o in byid['torso']['operations'] if o['id']=='torso-service-28')
 assert torso['toolAccessModels']['S10-case-069']=={'handleAxis':[0,-1,0],'handleLengthMm':25}
 assert torso['toolAccessModels']['S05-case-074']=={'handleAxis':[0,1,0],'handleLengthMm':25}
 return byid
if __name__=='__main__':
 base,effective,service=data();modules=[service['module'] if m['id']=='torso' else m for m in effective['modules'] if m['id'] in ['left-leg','right-leg','torso','power','imu','neck']];overlay=json.loads((D/'assembly-motion-overlay.json').read_text());verify(overlay,modules)
 tests=[]
 for name in ['late-foot','missing-carried-foot','missing-retainer','wrong-tool-direction','stale-source-operation']:
  bad=copy.deepcopy(overlay);mods=copy.deepcopy(modules)
  if name=='late-foot':bad['moduleOrders']['left-leg']=[o['id'] for o in mods[0]['operations']]
  elif name=='missing-carried-foot':next(p for p in bad['operationPatches'] if p['operationId']=='left-leg-09')['set']['moveKeys'].remove('foot')
  elif name=='missing-retainer':next(p for p in bad['operationPatches'] if p['operationId']=='left-leg-09')['set']['movingScrewIds'].remove('left-foot-retainer')
  elif name=='wrong-tool-direction':next(p for p in bad['operationPatches'] if p['operationId']=='neck-14')['set']['toolAccessModels']['S10-case-071']['handleAxis']=[0,-1,0]
  else:mods[0]['operations'][0]['partApproachVectors']['motor7']=[0,45,0]
  try:verify(bad,mods,False)
  except AssertionError:tests.append(name)
  else:raise AssertionError('negative passed '+name)
 receipt={'passed':True,'sourceSha256':sha(G/'full-build-data.json'),'overlaySha256':sha(D/'assembly-motion-overlay.json'),'negativeMutationsRejected':tests,'actualGeometryNegativeControls':['negative-original-order/left-leg-12-tool.json','negative-original-order/right-leg-12-tool.json','negative-original-order/torso-service-28-tool.json','negative-original-order/neck-14-tool.json'],'physicalAssemblyVerified':False}
 (D/'overlay-verification.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
