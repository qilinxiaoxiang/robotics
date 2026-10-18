import json,hashlib,itertools,math
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[2];G=R/'leg-guide-20261006';M=R/'workflow-review-20261009/original-body-converter/fusion-import-manifest.json'
p={x['key']:x for x in json.loads((G/'full-build-data.json').read_text())['parts']}
man=json.loads(M.read_text()); (D/'obstacles').mkdir(exist_ok=True)
# Isolated input files avoid retaining the full viewer payload in each CAD worker.
for row in man['parts']:
 (D/'obstacles'/f"{row['key']}.json").write_text(json.dumps(row))
reg=json.loads((R/'workflow-review-20261009/leg-ports/registered-ports.json').read_text())
ports={}
for n in range(1,16):
 t=p[f'motor{n}']['sourceTransformWorld']
 def pt(q):return [sum(t[i][j]*q[j] for j in range(3))+t[i][3] for i in range(3)]
 def vec(q):return [sum(t[i][j]*q[j] for j in range(3)) for i in range(3)]
 ports[str(n)]=[{'motor':n,'sourceSocket':13+k,'mouth':pt([8.4,s*7.7,-9]),'shoulder':pt([10.5,s*8,-9]),'outward':vec([1,0,0]),'width':vec([0,0,1]),'transform':t,'housingLocalBounds':[[3.4,s*8-1.9,-13.75],[10.5,s*8+1.9,-4.25]],'pinOrderVerified':False} for k,s in enumerate([-1,1])]
chain=[15,14,13,11,12,5,4,3,2,1,6,7,8,9,10]
# Each internal motor uses two different sockets. Choose a globally short neutral assignment.
best=None
for bits in itertools.product([0,1],repeat=len(chain)):
 val=sum(math.dist(ports[str(a)][1-bits[i]]['shoulder'],ports[str(b)][bits[i+1]]['shoulder'])for i,(a,b)in enumerate(zip(chain,chain[1:])))
 if best is None or val<best[0]:best=(val,bits)
routes=[]
for i,(a,b)in enumerate(zip(chain,chain[1:])):
 A=ports[str(a)][1-best[1][i]];B=ports[str(b)][best[1][i+1]]
 routes.append({'id':f'ttl-{a:02}-{b:02}','from':A,'to':B,'role':'Three-conductor physical receiving route; DATA continuity only is adopted in current branch-isolated ledger. GND/VDD termination remains electrical-contract dependent; no permission to bridge supplies.','stockNominalLengthMm':180,'stockLengthMeaning':'Nominal bundled X3P cable; this candidate route is not yet a full 180 mm spare-length qualification.'})
obj={'schemaVersion':1,'status':'CANDIDATE_ONLY_NOT_PHYSICAL_ACCEPTANCE','units':'mm','sourceManifest':str(M),'sourceManifestSha256':hashlib.sha256(M.read_bytes()).hexdigest(),'portRegistration':str(R/'workflow-review-20261009/leg-ports/registered-ports.json'),'portRegistrationSha256':hashlib.sha256((R/'workflow-review-20261009/leg-ports/registered-ports.json').read_bytes()).hexdigest(),'wireOuterDiameterMm':1.5,'wireDiameterEvidence':'Explicit conservative receiving assumption; actual X3P insulation diameter not manufacturer verified. Not a claim of measured stock.','routes':routes,'unmodeledConnection':{'from':'OpenRB','toMotor':15,'reason':'OpenRB exact DYNAMIXEL socket registration pending; do not create a false centre-to-centre connector.'},'ports':ports}
(D/'route-input.json').write_text(json.dumps(obj,indent=2));print('14 registered motor-to-motor routes prepared')
