"""One finite circular alternative at relocated anchors. Pure stdlib."""
from pathlib import Path
import json,math,hashlib
from prepare_single_candidate import moved,add,sub,mul,norm,dot
from single_circle_candidate import arc,line
D=Path(__file__).resolve().parent;H=D.parent.parent;SOURCE=H/'usb-access/usb-repair/rigid-domain.json'
A=[-47.,23.2,103.];B=[26.,38.,42.];TA=[0,0,-1.];Y=[-2**-.5,2**-.5,0];R=16.;RESERVE=8.
def terms(q):
 a=moved(A,q);ta=moved(TA,q,True);prefix,pl=arc(a,ta,Y,R);c=prefix[-1];delta=sub(B,c);axial=dot(delta,Y);delta=sub(delta,mul(Y,axial));d=norm(delta);rr=min(R,d/2);minimum=pl+d+(math.pi-2)*rr+abs(axial)+2*RESERVE
 return prefix,pl,c,delta,d,rr,minimum

def candidate(q,L):
 prefix,pl,c,delta,d,rr,minimum=terms(q);e=mul(delta,1/d);across=d-2*rr;left=(L-pl-across-math.pi*rr+dot(sub(B,c),Y))/2;right=left-dot(sub(B,c),Y)
 assert min(left,right)>=RESERVE-1e-8
 pts=prefix[:];top=add(c,mul(Y,left));pts+=line(c,top)[1:];p,l1=arc(top,Y,e,rr);pts+=p[1:];end=add(p[-1],mul(e,across));pts+=line(p[-1],end)[1:];p,l2=arc(end,e,mul(Y,-1),rr);pts+=p[1:];pts+=line(p[-1],B)[1:]
 bounds=[list(map(min,zip(*pts))),list(map(max,zip(*pts)))];return {'points':pts,'minimumRequiredLengthMm':minimum,'analyticLengthMm':pl+left+right+across+l1+l2,'minimumCenterRadiusMm':rr,'receivingBounds':[[v-3.5 for v in bounds[0]],[v+3.5 for v in bounds[1]]],'straightLegsMm':[left,right]}
def main():
 base=json.loads(SOURCE.read_text());L=5*math.ceil(max(terms(r['jointDegrees'])[-1] for r in base['samples'])/5);rows=[]
 for i,row in enumerate(base['samples']):
  r=candidate(row['jointDegrees'],L);r.pop('points');rows.append({'index':i,'jointDegrees':row['jointDegrees'],'nativeBaselineBlocked':bool(row['nativeShellOriginalBottomIntersectionsMm3']),**r})
 neutral=candidate({},L);neutral.pop('points');summary={'constantLengthMm':L,'maxLengthDriftMm':max(abs(r['analyticLengthMm']-L) for r in rows),'minimumCenterRadiusMm':min(r['minimumCenterRadiusMm'] for r in rows),'radiusFailuresBelow9mm':[r['index'] for r in rows if r['minimumCenterRadiusMm']<9],'neutralReceivingBounds':neutral['receivingBounds'],'maximumWorldYAcross229Mm':max(r['receivingBounds'][1][1] for r in rows),'completed229':len(rows)==229}
 report={'accepted':False,'CADExecuted':False,'family':'R16 endpoint conditioning + one U of tangent arcs and two variable straight legs. Same relocated anchors as short spline; torso arrives along the opposite of the fixed rear/side 45-degree bow axis.','A':A,'B':B,'headNeutralTangent':TA,'torsoIncomingTangent':mul(Y,-1),'bowAxis':Y,'receivingODMm':7,'summary':summary,'neutral':neutral,'rows':rows,'stillUnverified':['All obstacle solids','Nonadjacent receiver self-distance','Continuous angular paths','Anchor hardware','Actual available stock and full terminal fanouts'],'sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,Path(__file__),D/'single_circle_candidate.py',D/'prepare_single_candidate.py']}}
 (D/'short-circular-diagonal-screen.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
