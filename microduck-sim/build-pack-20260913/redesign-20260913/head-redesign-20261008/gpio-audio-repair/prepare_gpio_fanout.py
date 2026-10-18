"""Exact source pin positions; guarded geometry only with explicit --build."""
import json,argparse,math
from pathlib import Path
import bounded_amp_check as c
from prepare_speaker_rewire import transform,add,mul
D=Path(__file__).resolve().parent;H=D.parent;O=D/'gpio-fanout';O.mkdir(exist_ok=True)
NETS={1:('imu-vin',.8),2:('pi-5v-2',1.8),3:('imu-sda',.8),4:('pi-5v-4',1.8),5:('imu-scl',.8),6:('pi-gnd-6',1.8),9:('imu-gnd',.8),12:('BCLK',1.5),14:('pi-gnd-14',1.8),20:('audio-ground',1.5),35:('LRCLK',1.5),40:('DIN',1.5)}
p=argparse.ArgumentParser();p.add_argument('--build',action='store_true');a=p.parse_args();pose=H/'camera-ribbon-repair/lowered-pose-pair-checks.json';T=json.loads(pose.read_text())['worldTransform'];out=[-T[i][0] for i in range(3)];rows=[]
for pin,(net,diameter) in NETS.items():
 start=transform(T,[49.31,-24.141+2.54*((pin-1)//2),118.2796+(2.54 if pin%2==0 else 0)]);end=add(start,mul(out,4))
 rows.append({'pin':pin,'net':net,'diameterMm':diameter,'startMm':start,'endMm':end,'direction':out,'lengthMm':4,'endpointScope':'18mm conservative female housing receiver boundary, not invented actual plastic shoulder measurement.','ownedStatus':'4397 actual four IMU leads received' if pin in [1,3,5,9] else 'Club stock requirement; exact contacts/wire not confirmed present'})
r={'integrationReady':False,'purpose':'First4mm straight exit feasibility only, not a full route or specified bend radius','rows':rows,'inputHashes':c.fingerprint([Path(__file__),pose,D/'scene.py',D/'connector-dimensions.json'])}
if a.build:
 c.guarded_import();from check_speaker_rewire import tube;import precision_mesh as pm
 for x in rows:
  f=O/f'pin-{x["pin"]:02}-first4mm-world.stl';s=tube([x['startMm'],x['endMm']],x['diameterMm']/2);pm.export(c,s,f);x.update(mesh=str(f),meshSha256=c.sha(f))
c.atomic_json(O/'first4mm-plan.json',r);print(json.dumps({'pins':len(rows),'built':a.build,'integrationReady':False}))
