"""Read-only, stdlib inventory for populated-cap vs one new frozen FFC obstacle."""
from pathlib import Path
import json,hashlib,struct
D=Path(__file__).resolve().parent;H=D.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def bounds(p):
 data=p.read_bytes();pts=[];lo=[float('inf')]*3;hi=[-float('inf')]*3
 if len(data)>=84 and len(data)==84+50*struct.unpack_from('<I',data,80)[0]:
  def vertices():
   for off in range(84,len(data),50):
    vs=struct.unpack_from('<12f',data,off)
    for i in (3,6,9):yield vs[i:i+3]
  it=vertices()
 else:it=(list(map(float,l.split()[1:]))for l in data.decode().splitlines()if l.strip().startswith('vertex '))
 n=0
 for v in it:
  n+=1
  for k in range(3):lo[k]=min(lo[k],v[k]);hi[k]=max(hi[k],v[k])
 assert n and all(lo[k]<hi[k]for k in range(3)),str(p)
 return [lo,hi]
def main():
 inv=H/'current-closure/cap-inventory.json';plan=H/'usb-access/usb-repair/positive-x225-obstacle-plan.json';components=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';proof=H/'gpio-audio-repair/speaker-final-export/speaker-pilot-fix/pilot-fix-report.json'
 groups=json.loads(inv.read_text())['movingWithCap'];p=json.loads(plan.read_text())['obstacles'];cm=json.loads(components.read_text());pr=json.loads(proof.read_text());sources={str(q):sha(q)for q in [inv,plan,components,proof,Path(__file__)]}
 assert groups==['head_cap','openrb','amplifier','speaker','speaker_cradle','speaker_keeper','curved_cap_hardware']
 assert cm['componentCount']==142 and len(cm['components'])==142 and cm['allSourceTrianglesCoveredExactlyOnce']
 assert sha(Path(cm['sourceFile']))==cm['sourceSha256'];sources[cm['sourceFile']]=cm['sourceSha256']
 assert pr['passed'] and pr['sourceSubsetProof'] and pr['addedVolumeMm3']==0
 assert sha(Path(pr['output']))==pr['outputSha256'];assert sha(Path(pr['source']))==pr['sourceSha256']
 rows=[]
 for group in groups:
  if group=='openrb':
   for c in cm['components']:
    path=Path(c['mesh']);assert sha(path)==c['meshSha256'];bb=bounds(path)
    rows.append({'key':f"openrb-component-{c['index']:04}",'group':group,'path':str(path),'sha256':sha(path),'boundsMm':bb,'representation':'source-containing convex component enclosure','sourceTriangleCount':c['sourceTriangleCount'],'maximumHalfspaceViolationMm':c['maximumHalfspaceViolationMm']})
  else:
   path=Path(pr['output'])if group=='head_cap'else Path(p[group]['source']);rows.append({'key':group,'group':group,'path':str(path),'sha256':sha(path),'boundsMm':bounds(path),'representation':'actual current closed receiving mesh'})
 assert len(rows)==148
 original=H/'current-closure';rootreports=[original/(k+'.json')for k in json.loads(inv.read_text())['tested']]+list(original.glob('*--*.json'))
 rootreports=[q for q in rootreports if not q.name.endswith('-resource.json')]
 inherited=[]
 for q in rootreports:
  a=json.loads(q.read_text());assert a['passed'],str(q)
  inherited.append({'path':str(q),'sha256':sha(q),'passedAsRecorded':True})
 assert len(inherited)==43,len(inherited)
 out={'schemaVersion':1,'prepared':True,'closureAccepted':False,'scope':'Only new fixed complete FFC obstacle against existing populated-cap translation; no printing, no whole-head commissioning claim.','groups':groups,'movingEntities':rows,'movingEntityCount':len(rows),'offsetsZMm':[40-i*.25 for i in range(161)],'sampleCountPerEntity':161,'totalEntitySamples':148*161,'sourceHashes':sources,'rootExistingPairReceipts':inherited,'inheritanceBoundary':'43 root-owned existing-obstacle receipts retained, not rerun or relabeled as proof for changed Pi poses. Current cap is a source-bound strict material subset. This new checker accepts ONLY the added FFC obstacle pairs.','ffcInput':'Await accepted complete200mm world mesh and source-bound input-contract.json; candidate route cannot pass the runner.'}
 (D/'moving-inventory.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'entities':len(rows),'samples':out['totalEntitySamples'],'rootReceipts':len(inherited)}))
if __name__=='__main__':main()
