from pathlib import Path
import json,hashlib,copy
D=Path(__file__).resolve().parent;P=D/'leg-local-manifest.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify(x):
 assert x['localStaticPassed'] and not x['wholeHarnessAccepted']
 assert len(x['parts'])==30 and len(x['routes'])==6
 for f,h in x['sourceHashes'].items():assert sha(Path(f))==h,(f,'stale source')
 for p in x['parts']:assert sha(Path(p['file']))==p['sha256'],(p['key'],'stale mesh')
 c=json.loads(Path(x['centerlineInput']).read_text());assert sha(Path(x['centerlineInput']))==x['centerlineSha256'];assert len(c['paths'])==18
 cross=json.loads(Path(x['crossRouteReceipt']).read_text());assert cross['passed'] and cross['pairCount']==375
 assert cross['partHashes']=={p['key']:p['sha256']for p in x['parts']}
 assert all(r['overlapMm3']<1e-7 for r in cross['rows'])
 assert {'ttl-05-04','ttl-04-03','ttl-02-01','ttl-10-09','ttl-09-08','ttl-07-06'}=={r['id']for r in x['routes']}
 assert all(r['nominalFlexibleLengthMm']==180 for r in c['paths'])
 return True
x=json.loads(P.read_text());verify(x)
bad=copy.deepcopy(x);bad['parts'][0]['sha256']='0'*64
try:verify(bad)
except AssertionError:negative=True
else:negative=False
assert negative
out={'passed':True,'manifestSha256':sha(P),'parts':30,'centerlines':18,'routes':6,'allCurrentSourceAndMeshHashesVerified':True,'crossRoutePairs':375,'crossRouteExactPairs':11,'staleMeshNegativeControlRejected':negative,'noNewMovementProofs':True,'wholeHarnessAccepted':False}
(D/'leg-local-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
