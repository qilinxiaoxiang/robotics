"""Lightweight exact line-segment diagnostic of the reported pair only."""
from pathlib import Path
import json,hashlib
from compact_segments import geometry
from prepare_single_candidate import sub,add,mul,dot,norm
D=Path(__file__).resolve().parent

def dist(a,b,c,d):
 u=sub(b,a);v=sub(d,c);w=sub(a,c);uu=dot(u,u);vv=dot(v,v);uv=dot(u,v);uw=dot(u,w);vw=dot(v,w);den=uu*vv-uv*uv
 def ep(x,p,q):
  z=sub(q,p);zz=dot(z,z);t=max(0,min(1,dot(sub(x,p),z)/zz)) if zz>1e-14 else 0;return norm(sub(x,add(p,mul(z,t))))
 dd=min(ep(a,c,d),ep(b,c,d),ep(c,a,b),ep(d,a,b))
 if den>1e-14:
  s=(uv*vw-vv*uw)/den;t=(uu*vw-uv*uw)/den
  if 0<=s<=1 and 0<=t<=1:dd=min(dd,norm(sub(add(a,mul(u,s)),add(c,mul(v,t)))))
 return dd

def main():
 parts=geometry({});a=parts[0]['points'];b=parts[2]['points'];minimum=1e9;where=None
 for i,(aa,ab) in enumerate(zip(a,a[1:])):
  for j,(ba,bb) in enumerate(zip(b,b[1:])):
   if any(max(min(aa[k],ab[k]),min(ba[k],bb[k]))-min(max(aa[k],ab[k]),max(ba[k],bb[k]))>=minimum for k in range(3)):continue
   dd=dist(aa,ab,ba,bb)
   if dd<minimum:minimum=dd;where=[i,j]
 r={'scope':'Reported torso_entry / neck_to_head_pitch pair ONLY. First20oldfailures were a truncation, not all selfcrossings.','CADExecuted':False,'fullSelfCheckRun':False,'originalFirst20MinimumCenterDistanceMm':6.157516235292108,'repairedPairMinimumCenterDistanceMm':minimum,'receivingDiameterMm':7,'minimumSurfaceGapMm':minimum-7,'closestSegments':where,'localChange':'EntrybodyanchorY-66 derives from neckbridge minimumY-56 minus7mmdiameter minus3mmmargin. Turnaround R14 sitsX38..52 then approaches fixedneckanchor fromfront; otheranchors/loopsunchanged.','oldFailureTracesPreserved':'compact-isolated-v1-self-failed','sourceSha256':hashlib.sha256((D/'compact_segments.py').read_bytes()).hexdigest()};(D/'compact-local-repair-v2.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
