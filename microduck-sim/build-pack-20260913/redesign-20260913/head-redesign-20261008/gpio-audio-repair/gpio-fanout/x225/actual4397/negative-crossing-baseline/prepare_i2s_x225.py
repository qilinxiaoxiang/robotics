"""Finite full-route candidates; no acceptance implied by construction."""
import json,math,argparse
from pathlib import Path
from prepare_speaker_rewire import transform,add,mul,rounded,sha
p=argparse.ArgumentParser();p.add_argument('--tilt',type=float,default=0);args=p.parse_args()
D=Path(__file__).resolve().parent;H=D.parent;O=D/'gpio-fanout/x225';O.mkdir(exist_ok=True);pf=H/'camera-ribbon-repair/positive-x225-pose.json';T=json.loads(pf.read_text())['worldTransform'];n=[-T[i][0] for i in range(3)];routes=[]
for pin,net,yend in [(12,'BCLK',-28.27999939),(20,'GND',-18.11999939),(35,'LRCLK',-30.81999939),(40,'DIN',-25.73999939)]:
 start=transform(T,[49.31,-24.141+2.54*((pin-1)//2),118.2796+(2.54 if pin%2==0 else 0)]);sign=1 if pin in [35,40] else -1;beta=math.radians(60 if pin==35 else 30 if pin==40 else 0);b=[sign*T[i][1]*math.cos(beta)+T[i][2]*math.sin(beta) for i in range(3)];bendStart=add(start,mul(n,2)) if pin==12 else start;center=add(bendStart,mul(b,3));pts=[start] if pin==12 else []
 for j in range(21):
  theta=math.pi/2*j/20;pts.append(add(center,add(mul(b,-3*math.cos(theta)),mul(n,3*math.sin(theta)))))
 endarc=pts[-1];end=[56.257000885,yend,135.5849994]
 # Distinct static routing lanes. They deliberately retain OD1.5 andR3.
 lane=yend if pin in [12,20] else 21 if pin==35 else 32.2
 low={12:128,20:127.5,35:135.5,40:132}[pin];high={12:140,20:142,35:142.5,40:141}[pin];outside={12:62.5,20:64.5,35:63,40:63}[pin]
 q=add(endarc,mul(b,(lane-endarc[1])/b[1]));wp=[endarc,q,[q[0],q[1],low],[outside,q[1],low]]
 if abs(lane-yend)>1e-5:wp.append([outside,yend,low])
 wp.extend([[outside,yend,high],[end[0],yend,high],end])
 # Remove almost-collinear waypoint only; renderer rounds every remaining turn.
 from prepare_speaker_rewire import sub,dot,unit
 clean=[wp[0]]
 for i in range(1,len(wp)-1):
  u=unit(sub(wp[i],clean[-1]));v=unit(sub(wp[i+1],wp[i]));
  if dot(u,v)>.99999:continue
  clean.append(wp[i])
 clean.append(wp[-1])
 try:tail,segs,length=rounded(clean,3);pts+=tail[1:];error=None
 except AssertionError as e:tail=[];segs=[];length=None;error=str(e)
 routes.append({'pin':pin,'firstBendPlaneTiltDegrees':60 if pin==35 else 30 if pin==40 else 0,'net':net,'diameterMm':1.5,'radiusMm':3,'startMm':start,'ampPadMm':end,'waypointsAfterFirstBendMm':clean,'centerlineMm':pts,'analyticTailSegments':segs,'analyticLengthMm':None if length is None else length+3*math.pi/2+(2 if pin==12 else 0),'constructionError':error,'scope':'Complete static pin-to-pad candidate only. Constant-length service motion, solder shoulder allowance, strain relief and all obstacle checks remain required.'})
r={'integrationReady':False,'poseFile':str(pf),'sourceHashes':{str(p):sha(p) for p in [Path(__file__),pf,D/'prepare_speaker_rewire.py']},'routes':routes};(O/'i2s-route-proposal.json').write_text(json.dumps(r,indent=2)+'\n');print([(x['pin'],x['analyticLengthMm'],x['constructionError']) for x in routes])
