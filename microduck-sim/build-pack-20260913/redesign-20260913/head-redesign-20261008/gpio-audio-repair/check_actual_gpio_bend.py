import argparse,json,math
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
import check_speaker_rewire as s
from prepare_speaker_rewire import transform,add,mul
D=Path(__file__).resolve().parent;H=D.parent;O=D/'gpio-fanout/x225';P=H/'camera-ribbon-repair/positive-x225-pose.json';M=H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';p=argparse.ArgumentParser();p.add_argument('--tilt',type=float,required=True);a=p.parse_args();c.guarded_import();T=json.loads(P.read_text())['worldTransform'];pin=35;start=transform(T,[49.31,-24.141+2.54*((pin-1)//2),118.2796]);n=[-T[i][0] for i in range(3)];beta=math.radians(a.tilt);b=[T[i][1]*math.cos(beta)+T[i][2]*math.sin(beta) for i in range(3)];center=add(start,mul(b,3));pts=[]
for j in range(21):
 t=math.pi/2*j/20;pts.append(add(center,add(mul(b,-3*math.cos(t)),mul(n,3*math.sin(t)))))
wire=s.tube(pts,.4);f=O/f'actual-pin35-tilt{a.tilt}-world.stl';pm.export(c,wire,f);base=json.loads((D/'speaker-rewire/scene-plan.json').read_text())['rows'];manifest=json.loads(M.read_text());rows=[]
for key in ['jaw_support','motor15','head_bottom']:
 row={'path':str(H/manifest['replacementMeshes'][key])} if key in manifest['replacementMeshes'] else base[key];ob=s.solid(row);v=max(0,float((wire^ob).volume()));rows.append({'key':key,'volumeMm3':v,'gapMm':wire.min_gap(ob,2) if v<1e-5 else 0})
r={'integrationReady':False,'physical4397DiameterMm':.8,'Rmm':3,'tiltDegrees':a.tilt,'rows':rows,'inputHashes':c.fingerprint([Path(__file__),P,M,D/'check_speaker_rewire.py']),'scope':'Original purchased4397 female cutoff only, no extension-wire diameter change; first90deg bend only.'};c.atomic_json(f.with_suffix('.json'),r);print(json.dumps(r['rows']))
