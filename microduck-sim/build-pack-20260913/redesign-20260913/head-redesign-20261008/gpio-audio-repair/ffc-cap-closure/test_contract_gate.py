"""Cheap negative controls: no geometry libraries or CAD processes."""
from pathlib import Path
import tempfile,json,copy
from contracts import sha,load_contract
with tempfile.TemporaryDirectory()as tmp:
 d=Path(tmp);mesh=d/'dummy.stl';mesh.write_text('contract-test-only; not geometry');receipt=d/'route.json'
 values={'completePath':True,'lengthMm':200,'selfAccepted':True,'staticAccepted':True,'meshSha256':sha(mesh)};receipt.write_text(json.dumps(values))
 base={'frozen':True,'completePath':True,'lengthMm':200,'mesh':str(mesh),'meshSha256':sha(mesh),'evidenceClaims':{k:{'file':str(receipt),'sha256':sha(receipt),'jsonPointer':'/'+k}for k in values}};path=d/'input.json';path.write_text(json.dumps(base));assert load_contract(path)
 tests=[]
 for key,val in [('frozen',False),('completePath',False),('lengthMm',199.9),('meshSha256','wrong')]:
  a=copy.deepcopy(base);a[key]=val;tests.append((key,a))
 for key in ['selfAccepted','staticAccepted']:
  a=copy.deepcopy(base);a['evidenceClaims'][key]['jsonPointer']='/lengthMm';tests.append((key,a))
 a=copy.deepcopy(base);a['evidenceClaims']['completePath']['sha256']='stale';tests.append(('stale-receipt',a))
 for name,a in tests:
  path.write_text(json.dumps(a))
  try:load_contract(path)
  except(AssertionError,KeyError,ValueError):pass
  else:raise AssertionError('False acceptance: '+name)
 print(json.dumps({'passed':True,'negativeControls':[name for name,_ in tests],'geometryRun':False}))
