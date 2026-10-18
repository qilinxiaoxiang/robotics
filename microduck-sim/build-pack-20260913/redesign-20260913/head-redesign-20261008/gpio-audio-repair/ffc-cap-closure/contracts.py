from pathlib import Path
import hashlib,json
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pointer(value,p):
 for key in p.strip('/').split('/')if p else []:
  key=key.replace('~1','/').replace('~0','~');value=value[int(key)]if isinstance(value,list)else value[key]
 return value
def load_contract(path):
 path=Path(path);a=json.loads(path.read_text())
 if a.get('mode')=='diagnostic':return load_diagnostic(a)
 if a.get('mode')=='local-geometric-candidate':return load_local(a)
 assert a['frozen']is True,'FFC route is not frozen';assert a['completePath']is True and abs(a['lengthMm']-200)<1e-6
 mesh=Path(a['mesh']);assert mesh.is_file() and sha(mesh)==a['meshSha256']
 expected={'completePath':True,'lengthMm':200,'selfAccepted':True,'staticAccepted':True,'meshSha256':a['meshSha256']}
 for key,value in expected.items():
  e=a['evidenceClaims'][key];p=Path(e['file']);assert sha(p)==e['sha256'];actual=pointer(json.loads(p.read_text()),e['jsonPointer'])
  valid=abs(float(actual)-200)<1e-6 if key=='lengthMm' else (actual is True if value is True else actual==value)
  assert valid,(key,'evidence assertion failed')
 return a

def load_diagnostic(a):
 assert a['candidateOnly'] is True and a['wholeHarnessAccepted'] is False
 assert a['completePath'] is True and abs(a['lengthMm']-200)<1e-6
 assert sha(a['mesh'])==a['meshSha256']
 for f,h in a['sourceHashes'].items():assert sha(f)==h,('stale diagnostic source',f)
 static=json.loads(Path(a['staticReceipt']).read_text());own=json.loads(Path(a['selfReceipt']).read_text())
 assert static['sourceHashes'][a['mesh']]==a['meshSha256']
 assert static['materialLengthMm']==200 and static['completedObstacles']==static['expectedObstacles']
 assert own['expectedSelfPairs']==own['completedSelfPairs']==4851 and own['self']==[]
 for f,h in static['sourceHashes'].items():assert sha(f)==h,('stale static evidence',f)
 return a

def load_local(a):
 assert a['candidateOnly']is True and a['wholeHarnessAccepted']is False
 assert sha(a['mesh'])==a['meshSha256']
 for f,h in a['sourceHashes'].items():assert sha(f)==h,('stale local evidence',f)
 r=json.loads(Path(a['localReceipt']).read_text())
 assert r['complete']and r['localGeometricCandidatePassed']and r['staticClear']and r['selfClear']
 assert r['completedSelfPairs']==r['expectedSelfPairs']==4221 and r['self']==[]
 assert r['fullMeshSha256']==a['meshSha256']and abs(r['materialLengthMm']-200)<1e-6
 return a
