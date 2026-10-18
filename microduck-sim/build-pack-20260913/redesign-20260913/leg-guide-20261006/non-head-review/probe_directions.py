from pathlib import Path
import json,numpy as np
D=Path(__file__).resolve().parent;p=D.parent.parent/'head-redesign-20261008/head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns)
r=json.loads((D/'remaining-motion-review.json').read_text());wanted=['torso_base','ring10_torso','ring5_torso','imu_clamp'];out=[]
for k in wanted:
 row=next(x for x in r['rows'] if x['moving']==[k]);m={k:ns['solid'](k)};f={q:ns['solid'](q) for q in row['fixed']};results=[]
 for v in [[40,0,0],[-40,0,0],[0,40,0],[0,-40,0],[0,0,40],[0,0,-40]]:
  z=ns['samples'](m,f,v,step=1);nonterminal=max((max(x['contactsMm3'].values(),default=0) for x in z['samples'][:-1]),default=0);final=z['samples'][-1]['contactsMm3'];results.append({'vector':v,'preterminalMaxMm3':nonterminal,'finalContactsMm3':final,'peak':z['peakContactsMm3']});print(k,results[-1],flush=True)
 out.append({'moving':k,'fixed':row['fixed'],'directions':results})
(D/'direction-probes.json').write_text(json.dumps(out,indent=2)+'\n')
