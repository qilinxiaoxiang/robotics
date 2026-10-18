from pathlib import Path
import json,hashlib,copy
D=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected={'ttl-05-04','ttl-04-03','ttl-03-02','ttl-02-01','ttl-10-09','ttl-09-08','ttl-08-07','ttl-07-06'}
def check(m,assets=True):
 e=[]
 if {r['id']for r in m['routes']}!=expected:e.append('eight internal leg links required')
 if len(m['parts'])!=40 or len({p['key']for p in m['parts']})!=40:e.append('40 unique cable entities required')
 if assets:
  for p in m['parts']:
   if sha(p['file'])!=p['sha256']:e.append('stale mesh '+p['key'])
  for f,h in m['sourceHashes'].items():
   if sha(f)!=h:e.append('stale source '+f)
  for key,hkey in [('centerlineInput','centerlineSha256'),('verificationFile','verificationSha256')]:
   if sha(m[key])!=m[hkey]:e.append('stale '+key)
  paths=json.loads(Path(m['centerlineInput']).read_text())['paths']
  if len(paths)!=24:e.append('24 native paths required')
  for rid in expected:
   if sum(p['routeId']==rid for p in paths)!=3:e.append('three native conductors required '+rid)
  if not json.loads(Path(m['verificationFile']).read_text())['passed']:e.append('geometry receipt incomplete')
 return e
p=D/'eight-leg-manifest.json';m=json.loads(p.read_text());assert not check(m),check(m)
n=copy.deepcopy(m);n['routes']=[r for r in n['routes']if r['id']!='ttl-03-02'];assert check(n,False)
n=copy.deepcopy(m);n['parts'][0]['sha256']='0'*64;assert any('stale mesh'in x for x in check(n))
# Closure order must actually enforce the preconnection deadline.
deps=json.loads((D/'operation-dependencies.json').read_text());required=set(deps['dependencies'][0]['ports']);assert required=={f'motor-{i}-socket-{s}'for i in[2,3,7,8]for s in[13,14]}
def sequence_ok(events):
 completed=set()
 for event in events:
  if event in['left-leg-01','right-leg-01']:
   motors=[7,8]if event.startswith('left')else[2,3]
   if not {f'motor-{i}-socket-{s}'for i in motors for s in[13,14]}<=completed:return False
  completed.add(event)
 return True
assert sequence_ok(sorted(required)+['right-leg-01','left-leg-01']);assert not sequence_ok(['right-leg-01']+sorted(required))
r={'passed':True,'manifestSha256':sha(p),'requiredRoutes':sorted(expected),'meshAndInputHashesCurrent':True,'missingIntermediateLinkNegativeRejected':True,'staleMeshNegativeRejected':True,'closeBeforePreplugNegativeRejected':True};(D/'eight-leg-handoff-check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
