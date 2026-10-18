"""Reused purchased4397 female tails plus insulated extension joint; exact inventory boundary."""
import argparse,json,math
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
from check_speaker_rewire import tube
from tube_with_end_frame import tube_with_start_tangent
D=Path(__file__).resolve().parent;O=D/'gpio-fanout/x225';A=O/'actual4397';A.mkdir(exist_ok=True);P=O/'i2s-route-proposal.json';p=argparse.ArgumentParser();p.add_argument('--pin',type=int,required=True);a=p.parse_args();c.guarded_import();route=next(x for x in json.loads(P.read_text())['routes'] if x['pin']==a.pin);assert route['constructionError'] is None;pts=route['centerlineMm'];ss=[0]
for x,y in zip(pts,pts[1:]):ss.append(ss[-1]+math.dist(x,y))
def at(t):
 for j in range(len(ss)-1):
  if ss[j]-1e-9<=t<=ss[j+1]+1e-9:
   u=(t-ss[j])/(ss[j+1]-ss[j]);return [pts[j][k]*(1-u)+pts[j+1][k]*u for k in range(3)]
 raise ValueError(t)
def segment(lo,hi):return [at(lo)]+[p for p,t in zip(pts,ss) if lo+1e-8<t<hi-1e-8]+[at(hi)]
cut={12:36,20:36,35:40,40:40}[a.pin];assert cut<=140-100
# The actual soldered conductor overlap is4mm long and must be a straight portion.
metal=segment(cut-4,cut);axis=c.np.array(metal[-1])-metal[0];unit=axis/c.np.linalg.norm(axis);deviation=max(float(c.np.linalg.norm(c.np.cross(c.np.array(p)-metal[0],unit))) for p in metal);assert deviation<.01,('Joint would require bent solder overlap',a.pin,deviation)
T=json.loads((D.parent/'camera-ribbon-repair/positive-x225-pose.json').read_text())['worldTransform'];normal=[-T[i][0] for i in range(3)]
parts={'purchased_female_tail':tube_with_start_tangent(segment(0,cut),.4,normal),'extension_receiving':tube(segment(cut-4,ss[-1]),.75),'insulated_splice_receiving':tube(segment(cut-6,cut+2),1.4)};combined=c.mf.Manifold.batch_boolean(list(parts.values()),c.mf.OpType.Add);f=A/f'i2s-pin{a.pin}-world.stl';pm.export(c,combined,f)
for key,s in parts.items():pm.export(c,s,A/f'pin{a.pin}-{key}-world.stl')
r={'integrationReady':False,'pin':a.pin,'net':route['net'],'actualPurchasedTailDiameterMm':.8,'retainedFemaleTailMm':cut,'extensionDiameterReceivingMm':1.5,'insulatedSpliceReceiving':{'diameterMm':2.8,'lengthMm':8,'stationStartMm':cut-6,'stationEndMm':cut+2,'metalOverlapLengthMm':4,'metalStraightnessDeviationMm':deviation},'minimumAvailableFemaleCutoffMm':40,'stockArithmetic':'Official4397 flexible span150±10 minus100mm retained onJST side gives40..60mm female cutoff. Cut36/36/40/40mm from four separate originals. Four IMU JST ends need separate club150mm female tails to restore250mm; four power contacts are additional club requirements. No12-line4397 inventory claim.','ownedCountConsumed':1,'sourceOriginalSetOwned':4,'extensionCutLengthBeforePadAllowanceMm':ss[-1]-cut+4,'totalCenterlinePolylineMm':ss[-1],'inputHashes':c.fingerprint([Path(__file__),P,D/'tube_with_end_frame.py',D/'check_speaker_rewire.py',D/'connector-dimensions.json']),'outputSha256':c.sha(f),'pending':['Complete current-scene and interwire checks','Exact insulation stock OD2.8 receiving acceptance','Constant-length opening/closure and all service slack','Solder/strain relief and actual installed physical qualification']};c.atomic_json(A/f'i2s-pin{a.pin}.json',r);print(json.dumps({'pin':a.pin,'tailMm':cut,'length':ss[-1],'spliceStraightness':deviation}))
