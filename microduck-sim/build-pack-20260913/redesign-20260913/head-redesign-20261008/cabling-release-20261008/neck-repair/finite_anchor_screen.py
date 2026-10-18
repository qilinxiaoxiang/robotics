"""Finite stdlib anchor comparison: three declared body points, three bow axes."""
from pathlib import Path
import json,math,hashlib
from prepare_single_candidate import moved,add,sub,mul,norm,dot
from single_circle_candidate import arc,line
D=Path(__file__).resolve().parent;H=D.parent.parent;SOURCE=H/'usb-access/usb-repair/rigid-domain.json'
A=[-47.,23.2,103.];TA=[0.,0.,-1.];R=16.;RESERVE=8.
BS=[[26.,38.,42.],[0.,0.,47.],[0.,-25.,47.]]
US=[[-1.,0.,0.],[-2**-.5,2**-.5,0.],[-2**-.5,-2**-.5,0.]]
def terms(q,B,u):
 a=moved(A,q);ta=moved(TA,q,True);prefix,pl=arc(a,ta,u,R);c=prefix[-1];delta=sub(B,c);dy=dot(delta,u);trans=sub(delta,mul(u,dy));d=norm(trans);rr=min(R,d/2)
 return prefix,pl,c,trans,d,rr,pl+d+(math.pi-2)*rr+abs(dy)+2*RESERVE

def path(q,B,u,L):
 prefix,pl,c,trans,d,rr,need=terms(q,B,u);e=mul(trans,1/d);dy=dot(sub(B,c),u);across=d-2*rr;left=(L-pl-across-math.pi*rr+dy)/2;right=left-dy
 if min(left,right)<RESERVE-1e-7:return None
 pts=prefix[:];top=add(c,mul(u,left));pts+=line(c,top)[1:];p,l1=arc(top,u,e,rr);pts+=p[1:];end=add(p[-1],mul(e,across));pts+=line(p[-1],end)[1:];p,l2=arc(end,e,mul(u,-1),rr);pts+=p[1:];pts+=line(p[-1],B)[1:]
 return {'points':pts,'receivingBounds':[[v-3.5 for v in map(min,zip(*pts))],[v+3.5 for v in map(max,zip(*pts))]],'minimumCenterRadiusMm':rr,'analyticLengthMm':pl+left+right+across+l1+l2}
def main():
 base=json.loads(SOURCE.read_text());cases=[]
 for bi,B in enumerate(BS):
  for ui,u in enumerate(US):
   stats=[terms(r['jointDegrees'],B,u) for r in base['samples']];clear=[i for i,r in enumerate(base['samples']) if not r['nativeShellOriginalBottomIntersectionsMm3']];L=5*math.ceil(max(stats[i][-1] for i in clear)/5);neutral=path({},B,u,L);neutral.pop('points')
   rows=[{'index':i,'jointDegrees':r['jointDegrees'],'nativeBaselineBlocked':i not in clear,'requiredLengthMm':stats[i][-1],'availableAtSelectedLength':L>=stats[i][-1]-1e-7,'coreRadiusMm':stats[i][-2]} for i,r in enumerate(base['samples'])]
   c={'case':f'B{bi}U{ui}','B':B,'bowAxis':u,'selectedConstantLengthForNativeClearMm':L,'all229RequiredLengthMm':5*math.ceil(max(t[-1] for t in stats)/5),'nativeClearRadiusFailCount':sum(stats[i][-2]<9 for i in clear),'all229RadiusFailCount':sum(t[-2]<9 for t in stats),'neutral':neutral,'rows':rows};cases.append(c)
 report={'accepted':False,'CADExecuted':False,'purpose':'Exactly 3 predeclared fixed body points x 3 fixed bow axes. No random optimization. Retain all229 values; native-clear186 determines proposed mechanical prototype design targets, not revised XML limits.','headAnchorNeutral':A,'headTangentNeutral':TA,'receivingODMm':7,'minimumCenterRadiusCriterionMm':9,'neutralDesignGoals':{'maxAbsYmm':80,'minXmm':-95,'maxZmm':140,'maxFlexibleLengthMm':240},'cases':cases,'sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,Path(__file__),D/'single_circle_candidate.py',D/'prepare_single_candidate.py']}}
 (D/'finite-anchor-screen.json').write_text(json.dumps(report,indent=2)+'\n')
 for c in cases:print(json.dumps({k:c[k] for k in ['case','B','bowAxis','selectedConstantLengthForNativeClearMm','all229RequiredLengthMm','nativeClearRadiusFailCount','all229RadiusFailCount','neutral']}))
if __name__=='__main__':main()
