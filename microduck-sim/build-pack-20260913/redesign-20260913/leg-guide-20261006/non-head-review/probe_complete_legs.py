from pathlib import Path
import json,numpy as np
D=Path(__file__).resolve().parent;p=D.parent.parent/'head-redesign-20261008/head-fit-investigation.py';n={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],n);s=n['solid'];test=n['samples'];data=n['data'];out=[]
base={k:s(k) for k in ['torso_base','power_support','ring10_torso','ring5_torso']}
for mod in data['modules'][:2]:
 moving={k:s(k) for k in mod['ownedPartKeys']};axis_results=[]
 for vec in [[40,0,0],[-40,0,0],[0,40,0],[0,-40,0],[0,0,40],[0,0,-40]]:
  r=test(moving,base,vec,step=1);row={'vector':vec,'peak':r['peakContactsMm3'],'preterminalMaxMm3':max(max(x['contactsMm3'].values(),default=0) for x in r['samples'][:-1]),'final':r['samples'][-1]['contactsMm3']};axis_results.append(row);print(mod['id'],row,flush=True)
 out.append({'moving':list(moving),'fixed':list(base),'module':mod['id'],'directions':axis_results})
(D/'complete-leg-joining-probes.json').write_text(json.dumps(out,indent=2)+'\n')
# Separate immediate IMU repair, with complete previously assembled context.
old=json.loads((D/'remaining-motion-review.json').read_text());row=next(x for x in old['rows'] if x['moving']==['imu_clamp']);r=test({'imu_clamp':s('imu_clamp')},{k:s(k) for k in row['fixed']},[-28,0,0],step=.25)
(D/'imu-corrected-path.json').write_text(json.dumps({'sourceSha256':old['sourceSha256'],'fixed':row['fixed'],'path':r,'passed':not r['peakContactsMm3']},indent=2)+'\n');print('IMU_CORRECTION',r['peakContactsMm3'],flush=True)
