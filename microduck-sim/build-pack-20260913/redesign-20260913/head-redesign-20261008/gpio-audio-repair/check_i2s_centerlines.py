"""Fast exact sample-distance diagnostic; positive margin subtracts full0.25mm sampling bound."""
import json,math,itertools
from pathlib import Path
D=Path(__file__).resolve().parent;P=D/'gpio-fanout/x225/i2s-route-proposal.json';cuts={12:36,20:36,35:40,40:40};lines={}
for r in json.loads(P.read_text())['routes']:
 s=0;arr=[]
 for i,p in enumerate(r['centerlineMm']):
  if i:s+=math.dist(p,r['centerlineMm'][i-1])
  cut=cuts[r['pin']];radius=1.4 if cut-6<=s<=cut+2 else .75 if s>=cut-4 else .4;arr.append((p,s,radius))
 lines[r['pin']]=arr
out=[]
for a,b in itertools.combinations(lines,2):
 best=min((math.dist(x[0],y[0])-x[2]-y[2],x,y) for x in lines[a] for y in lines[b]);out.append({'pair':[a,b],'sampleGap':best[0],'continuousLowerBoundMm':best[0]-.25,'a':best[1],'b':best[2]})
(D/'gpio-fanout/x225/actual4397/centerline-pair-diagnostic.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
