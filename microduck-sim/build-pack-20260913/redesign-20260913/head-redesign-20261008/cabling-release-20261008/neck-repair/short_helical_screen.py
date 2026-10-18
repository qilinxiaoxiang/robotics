"""Four finite tapered-helical math screens, standard library only."""
from pathlib import Path
import math,json,hashlib,time
from prepare_single_candidate import moved,add,sub,mul,dot,cross,norm,rot
from prepare_short_selected import A,B,TA,U,L,OD,RMIN,SOURCE,H,D
TB=mul(U,-1)
def unit(v):return mul(v,1/norm(v))
u0=unit(sub(B,A));n0=unit(sub([0,1,0],mul(u0,dot(u0,[0,1,0]))))
def frame(q):
 a=moved(A,q);ta=moved(TA,q,True);u=unit(sub(B,a));cr=cross(u0,u);s=norm(cr);c=dot(u0,u)
 if c<-.999:raise ValueError('Antipodal frame; cannot silently switch')
 n=n0 if s<1e-12 else rot(n0,mul(cr,1/s),math.atan2(s,c))
 return a,ta,n,cross(u,n),c

def prepared(q,turns,m,N):
 a,ta,n,v,c=frame(q);w=2*math.pi*turns;out=[]
 for i in range(N+1):
  t=i/N;t2=t*t;t3=t2*t
  cf=[2*t3-3*t2+1,t3-2*t2+t,-2*t3+3*t2,t3-t2]
  df=[6*t2-6*t,3*t2-4*t+1,-6*t2+6*t,3*t2-2*t]
  ddf=[12*t-6,6*t-4,-12*t+6,6*t-2]
  vectors=[a,mul(ta,m),B,mul(TB,m)]
  basic=[[sum(f*x[k] for f,x in zip(fs,vectors)) for k in range(3)] for fs in [cf,df,ddf]]
  g=math.sin(math.pi*t)**2;gp=math.pi*math.sin(2*math.pi*t);gpp=2*math.pi**2*math.cos(2*math.pi*t)
  z=add(mul(n,math.cos(w*t)),mul(v,math.sin(w*t)));zp=mul(add(mul(n,-math.sin(w*t)),mul(v,math.cos(w*t))),w)
  wave=[mul(z,g),add(mul(z,gp),mul(zp,g)),add(mul(z,gpp-w*w*g),mul(zp,2*gp))]
  out.append((basic,wave))
 return out,c

def evaluate(pr,r,all_values=False):
 N=len(pr)-1;speeds=[];pts=[];radii=[]
 for basic,wave in pr:
  d=add(basic[1],mul(wave[1],r));speed=norm(d);speeds.append(speed)
  if all_values:
   p=add(basic[0],mul(wave[0],r));dd=add(basic[2],mul(wave[2],r));den=norm(cross(d,dd));pts.append(p);radii.append(speed**3/den if den>1e-12 else 1e20)
 length=(speeds[0]+speeds[-1]+sum((4 if i%2 else 2)*speeds[i] for i in range(1,N)))/(3*N)
 if not all_values:return length
 return {'lengthMm':length,'minimumSampledRadiusMm':min(radii),'minimumSpeed':min(speeds),'receivingBounds':[[v-OD/2 for v in map(min,zip(*pts))],[v+OD/2 for v in map(max,zip(*pts))]]}
def main():
 source=json.loads(SOURCE.read_text());summary=[]
 for turns,m in [(1,80),(1,120),(2,80),(2,120)]:
  started=time.time();rows=[]
  for i,entry in enumerate(source['samples']):
   q=entry['jointDegrees'];pr,c=prepared(q,turns,m,64);lowL=evaluate(pr,0);highL=evaluate(pr,35);row={'index':i,'jointDegrees':q,'nativeBaselineBlocked':bool(entry['nativeShellOriginalBottomIntersectionsMm3']),'zeroRadiusLengthMm':lowL,'frameReferenceCosine':c}
   if not lowL<=L<=highL:row.update(available=False,reason='Target outside finite radius[0,35] branch')
   else:
    lo=0.;hi=35.
    for _ in range(25):
     mid=(lo+hi)/2
     if evaluate(pr,mid)<L:lo=mid
     else:hi=mid
    radius=(lo+hi)/2;fine,_=prepared(q,turns,m,256);result=evaluate(fine,radius,True);row.update(available=True,amplitudeMm=radius,mathScreenPass=result['minimumSampledRadiusMm']>=RMIN and result['minimumSpeed']>1 and abs(result['lengthMm']-L)<.05,**result)
   rows.append(row)
  def group(rs):
   av=[r for r in rs if r['available']];return {'expected':len(rs),'completed':len(rs),'available':len(av),'sampledMathPass':sum(r.get('mathScreenPass',False) for r in rs),'minimumSampledRadiusMm':min((r['minimumSampledRadiusMm'] for r in av),default=None),'maxAmplitudeMm':max((r['amplitudeMm'] for r in av),default=None),'worstRadiusIndex':min(av,key=lambda r:r['minimumSampledRadiusMm'])['index'] if av else None}
  report={'accepted':False,'CADExecuted':False,'family':'Cubic Hermite endpoint base plus r*sin(pi*t)^2 rotating normal with 1 or2 turns. Endpoint positions and derivatives unchanged; amplitude solves a fixed215mm length. This is not the bare constant-radius helix formula, because endpoint transition curvature is evaluated explicitly.','parameters':{'turns':turns,'endpointDerivativeMagnitudeMm':m,'freeSpanLengthMm':L,'radiusRangeMm':[0,35],'receivingODMm':OD,'minimumCenterRadiusMm':RMIN,'A':A,'B':B,'TA':TA,'TB':TB},'groups':{'all229':group(rows),'nativeClear186':group([r for r in rows if not r['nativeBaselineBlocked']]),'nativeBlocked43':group([r for r in rows if r['nativeBaselineBlocked']])},'rows':rows,'scope':'Finite math rejection screen only. Simpson64 versus256 length;257 curvature samples. No obstacle/self/angular-path acceptance. Existing stock not sufficient merely because modeled span is shorter.','sourceHashes':{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,Path(__file__),D/'prepare_short_selected.py',D/'prepare_single_candidate.py']},'seconds':time.time()-started}
  (D/f'short-helical-N{turns}-M{m}.json').write_text(json.dumps(report,indent=2)+'\n');summary.append({'turns':turns,'m':m,'groups':report['groups'],'seconds':report['seconds']});print(json.dumps(summary[-1]),flush=True)
if __name__=='__main__':main()
