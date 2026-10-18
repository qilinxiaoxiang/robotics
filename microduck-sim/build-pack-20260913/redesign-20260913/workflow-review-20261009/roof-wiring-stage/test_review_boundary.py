"""Lightweight publication-boundary regressions; no geometry computation."""
from pathlib import Path
import tempfile,json,copy,hashlib,importlib.util,contextlib,io
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('review_builder',P/'build_review.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d))
def fixture(root):
 mesh=root/'one.stl';mesh.write_bytes(b'fixture source body')
 manifest={'parts':[{'key':'body','file':str(mesh),'sha256':b.sha(mesh)}]};write(root/'fusion/fusion-import-manifest.json',manifest);mh=b.sha(root/'fusion/fusion-import-manifest.json')
 write(root/'fusion/fusion-receipt.json',{'status':'COMPLETE','readbackPassed':True,'manifestSha256':mh,'meshBodies':1,'wireBodies':1})
 write(root/'roof/patch-static-check.json',{'passed':True})
 write(root/'fusion/motor-wires-stage-summary.json',{'routeCount':1,'routes':[{'id':'m1','neutralStaticCollisionFree':True,'sourceMeshInterferences':[]}],'neutralStaticClearCount':1,'failedOrUnresolvedCount':0})
 write(root/'fusion/head-wires-stage-summary.json',{'integrationReady':True,'remainingFailures':[],'unclosedChecks':[]})
 write(root/'fusion/head-wires-manifest.json',{'parts':[{'key':'h1'}]})
 for f in ['head-closed-readback.png','head-wires.png','whole-wiring.png','whole-closed-readback.png']:(root/'fusion'/f).write_bytes(b'fixture PNG')
 a={'assemblyManifestSha256':mh,'topology':'pi-usb-to-openrb-internal','exteriorEnclosed':True,'unresolvedOpenings':[],'routeInventory':{'motor':['m1'],'head':['h1']},'inputHashes':{},'scopeEvidence':{}}
 for rel in ['fusion/motor-wires-stage-summary.json','fusion/head-wires-stage-summary.json','fusion/head-wires-manifest.json']:a['inputHashes'][rel]=b.sha(root/rel)
 for scope in b.REQUIRED_SCOPES:
  f='checks/'+scope+'.json';write(root/f,{'assemblyManifestSha256':mh,'scope':scope,'passed':True,'coverageComplete':True,'unresolved':[],'testedValidBodyCount':2,'expectedCheckIds':['fixture-pair'],'checks':[{'id':'fixture-pair','status':'complete','validInputs':True,'validResult':True,'result':'clear'}]});a['scopeEvidence'][scope]={'file':f,'sha256':b.sha(root/f)}
 write(root/'repair-acceptance.json',a);return a
checks=[]
def check(name,fn):fn();checks.append(name)
actual=b.validate_repair(P);assert actual and any('motor' in e.lower() for e in actual) and any('head' in e.lower() for e in actual)
checks.append('actual 11/15 failures rejected despite successful Fusion readback and patch check')
page=P.parent/'DESIGN-REVIEW.html';old=page.read_bytes() if page.exists() else None
try:b.main([],root=P)
except SystemExit:pass
else:raise AssertionError('current failed assembly built')
assert (page.read_bytes() if page.exists() else None)==old;checks.append('actual failed build preserves existing page byte-for-byte')
with tempfile.TemporaryDirectory() as t:
 root=Path(t)/'stage';root.mkdir();a=fixture(root);assert b.validate_repair(root)==[]
 with contextlib.redirect_stdout(io.StringIO()):b.main([],root=root)
 assert (root.parent/'DESIGN-REVIEW.html').is_file();checks.append('complete source-bound fixture builds successfully')
 accepted=(root.parent/'DESIGN-REVIEW.html').read_text()
 assert 'The Pi connects internally to OpenRB' in accepted
 for stale in ['Mac connects to the OpenRB','rear USB opening remain','still have interference','stay unresolved','AI assistance was used']:
  assert stale not in accepted,stale
 checks.append('success rendering uses accepted internal topology with no stale failure badges or unsolicited disclosure')
 baseline=(root.parent/'DESIGN-REVIEW.html').read_bytes()
 for label,mut in [('one remaining collision',lambda x:x.update(remainingFailures=['collision'])),('unrun scope',lambda x:x.update(unclosedChecks=['joint motion']))]:
  fixture(root);f=root/'fusion/head-wires-stage-summary.json';d=json.loads(f.read_text());mut(d);write(f,d)
  a=json.loads((root/'repair-acceptance.json').read_text());a['inputHashes']['fusion/head-wires-stage-summary.json']=b.sha(f);write(root/'repair-acceptance.json',a)
  assert b.validate_repair(root);checks.append(label+' rejects even after honest source hash refresh')
 for key,value in [('exteriorEnclosed',False),('unresolvedOpenings',['rear USB']),('topology','mac-usb-external'),('routeInventory',{'motor':['m1'],'head':[]})]:
  a=fixture(root);a[key]=value;write(root/'repair-acceptance.json',a);assert b.validate_repair(root);checks.append(key+' negative rejected')
 for change in ['failed','skipped','stale']:
  a=fixture(root);f=root/'checks/closure.json';d=json.loads(f.read_text())
  if change=='failed':d['passed']=False
  elif change=='skipped':d['coverageComplete']=False
  else:d['assemblyManifestSha256']='wrong'
  write(f,d);a['scopeEvidence']['closure']['sha256']=b.sha(f);write(root/'repair-acceptance.json',a);assert b.validate_repair(root);checks.append(change+' native scope rejects')
 for label,field,value in [('empty native bodies','testedValidBodyCount',0),('missing native rows','checks',[]),('invented passed boolean','expectedCheckIds',[])]:
  a=fixture(root);f=root/'checks/static-routing.json';d=json.loads(f.read_text());d[field]=value;write(f,d);a['scopeEvidence']['static-routing']['sha256']=b.sha(f);write(root/'repair-acceptance.json',a);assert b.validate_repair(root);checks.append(label+' rejects')
 fixture(root);(root/'one.stl').write_bytes(b'changed geometry');assert b.validate_repair(root);checks.append('adopted mesh mutation rejects')
 fixture(root);f=root/'checks/closure.json';f.write_text('{}');assert b.validate_repair(root);checks.append('report hash mutation rejects')
 fixture(root)
 for out in [root.parent/'DESIGN-REVIEW.html',root/'diagnostics/DESIGN-REVIEW.html',root.parent/'other.html']:
  try:b.main(['--diagnostic-output',str(out)],root=root)
  except SystemExit:pass
  else:raise AssertionError('diagnostic escaped private directory')
 checks.append('diagnostic cannot target deployed name or leave private directory')
 a=fixture(root);a['exteriorEnclosed']=False;write(root/'repair-acceptance.json',a)
 with contextlib.redirect_stdout(io.StringIO()):b.main(['--diagnostic-output',str(root/'diagnostics/failure.html')],root=root)
 text=(root/'diagnostics/failure.html').read_text();assert 'INTERNAL DIAGNOSTIC ONLY' in text and 'repair incomplete' in text;checks.append('explicit private diagnostic remains usable and visibly incomplete')
report={'passed':True,'checks':checks,'actualRejectedReasons':actual,'builderSha256':b.sha(P/'build_review.py'),'geometryTestsRun':0}
write(P/'review-boundary-test-report.json',report);print(json.dumps(report,indent=2))
