from pathlib import Path
import json,math,hashlib
D=Path(__file__).resolve().parent;W=D.parents[2];H=W.parent/'head-redesign-20261008'
def add(a,b):return [x+y for x,y in zip(a,b)]
def mul(a,s):return [x*s for x in a]
def line(a,b):return {'kind':'line','start':a,'end':b,'lengthMm':math.dist(a,b)}
def arc(p,t,u,r):
 return {'kind':'arc','start':p,'mid':add(p,add(mul(t,r/math.sqrt(2)),mul(u,r*(1-1/math.sqrt(2))))),'end':add(p,mul(add(t,u),r)),'radiusMm':r,'lengthMm':r*math.pi/2}
S=[19,-9.911,133.6];F=[-22.5,-8.5,98];A=[-22.5,-8.5,50.1];C=[-26.27,.015,60.1]
vertical=[0,F[1]-S[1],F[2]-S[2]];norm=math.sqrt(sum(x*x for x in vertical));u=mul(vertical,1/norm)
pr=[line(S,[-12.5,S[1],S[2]])];pr.append(arc(pr[-1]['end'],[-1,0,0],u,10));pr.append(line(pr[-1]['end'],F))
Lsc=sum(q['lengthMm']for q in pr)
def ac(h):
 p=[line(C,[C[0],C[1],h])]
 def turn(t,u,r):p.append(arc(p[-1]['end'],t,u,r))
 def end(q):p.append(line(p[-1]['end'],q))
 turn([0,0,1],[1,0,0],8);end([-8,C[1],h+8]);turn([1,0,0],[0,0,-1],8);end([0,C[1],60.1]);turn([0,0,-1],[0,-1,0],4);end([0,A[1]+4,56.1]);turn([0,-1,0],[0,0,-1],4);end([0,A[1],48.1]);turn([0,0,-1],[-1,0,0],8);end([-14.5,A[1],40.1]);turn([-1,0,0],[0,0,1],8);end(A)
 return p
p0=ac(68);h=68+(102.5-sum(x['lengthMm']for x in p0))/2;acpr=ac(h);Lac=sum(q['lengthMm']for q in acpr);assert abs(Lac-102.5)<1e-6
rows=[{'key':'sc0727_flexible_route','primitives':pr,'radiusMm':1.75},{'key':'adafruit4472_flexible_route','primitives':acpr,'radiusMm':2.25},{'key':'usb_a_female_receiving','boundsMm':[[F[0]-10,F[1]-6,73],[F[0]+10,F[1]+6,98]]},{'key':'usb_a_male_receiving','boundsMm':[[F[0]-10,F[1]-6,50.1],[F[0]+10,F[1]+6,73]]},{'key':'pi_microb_receiving','boundsMm':[[19,-16.411,130.6],[44,-3.411,136.6]]}]
r={'status':'ONE_MANUAL_INTERFACE_CANDIDATE_NOT_ACCEPTED','nativeLengthMm':{'SC0727_requiredFlexibleRun':Lsc,'Adafruit4472':Lac},'stockLengthBoundary':{'SC0727NominalMm':80,'SC0727FlexibleLengthConfirmed':False,'microBMouldAssumedMm':25,'femaleMouldAssumedMm':25,'if80ExcludesBodiesMarginMm':80-Lsc,'if80IncludesBothAssumedBodiesShortfallMm':Lsc-30,'Adafruit4472NominalShoulderToShoulderMm':152.4,'Adafruit4472FlexibleRunMm':102.5},'assumptions':{'SC0727ODmm':3.5,'SC0727RadiusMm':10,'femaleBodyMm':[20,12,25],'maleBodyMm':[20,12,22.9],'AdafruitODmm':4.5,'AdafruitRadiusMm':[4,8],'manufacturerMinimumBendRadiusKnown':False,'meaning':'Hard mould/OD dimensions not sourced are receiving assumptions; R4 is a local packaging test, not manufacturer permitted minimum.'},'routes':[{'key':'sc0727_flexible_route','primitives':pr,'start':S,'end':F},{'key':'adafruit4472_flexible_route','primitives':acpr,'start':C,'end':A}],'parts':rows,'matePlaneMm':[F[0],F[1],73],'femaleTailMm':F,'maleTailMm':A,'sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [Path(__file__),H/'usb-access/full-harness/adafruit-4472-drawing.pdf',H/'usb-access/full-harness/full-harness-report.json',W/'enclosed-wiring-repair/head-layout/pi-front-up05-pose.json',W/'enclosed-wiring-repair/head-layout/body-partition/native-usb-passage/passage-spec.json']}}
(D/'candidate.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'lengths':r['nativeLengthMm'],'topH':h,'parts':len(rows)}))
