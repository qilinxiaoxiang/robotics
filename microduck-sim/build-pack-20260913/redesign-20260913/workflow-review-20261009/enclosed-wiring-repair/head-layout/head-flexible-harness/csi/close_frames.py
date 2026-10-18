"""One exact three-fold frame closure, then a four-by-four linear length solve.
No route optimizer, board motion, or acceptance claim.
"""
from pathlib import Path
import json,math
import numpy as np
D=Path(__file__).resolve().parent;R=D.parents[4];H=R/'head-redesign-20261008';old=json.loads((H/'gpio-audio-repair/ffc-terminal-adjustment/dogleg-0.25.json').read_text());pr=old['primitives'];start=pr[10];P=np.array(start['p']);T=np.array(start['t']);W=np.array(start['w']);S=start['s0'];target=np.array([65.47490590945819,-28.0999981,128.29887270958935]);tt=np.array([0.,1,0]);ww=np.array([-.17364817766693028,0,-.984807753012208]);F=np.column_stack([T,W,np.cross(T,W)]);G=np.column_stack([tt,ww,np.cross(tt,ww)]);M=F.T@G
out=[]
for sign in [1,-1]:
 angle=sign*math.acos(np.clip(M[2,2],-1,1));phi1=.5*math.atan2(-M[1,2]/math.sin(angle),M[0,2]/math.sin(angle));phi3=.5*math.atan2(M[2,1]/math.sin(angle),-M[2,0]/math.sin(angle));p=P.copy();t=T.copy();w=W.copy();dirs=[t.copy()];length=0;bs=[]
 for an,phi,rad in [(math.pi,phi1,1.5),(abs(angle),0,2),(math.pi,phi3,1.5)]:
  sg=-sign if phi==0 else 1;n=np.cross(t,w);e=w*math.cos(phi)+t*math.sin(phi);q=t*math.cos(phi)-w*math.sin(phi);L=rad*an/math.cos(phi);b={'angle':an,'phi':phi,'R':rad,'sign':sg,'length':L};bs.append(b);p=p+e*(rad*an*math.tan(phi))+q*rad*math.sin(an)+n*(sg*rad*(1-math.cos(an)));qp=q*math.cos(an)+n*sg*math.sin(an);t=e*math.sin(phi)+qp*math.cos(phi);w=e*math.cos(phi)-qp*math.sin(phi);dirs.append(t.copy());length+=L
 A=np.vstack([np.array(dirs).T,np.ones(4)]);v=np.r_[target-p,200-S-length];ls=np.linalg.solve(A,v);out.append({'branch':sign,'folds':bs,'straightLengthsMm':ls.tolist(),'endTangent':t.tolist(),'endWidth':w.tolist(),'frameError':float(np.linalg.norm(t-tt)+np.linalg.norm(w-ww)),'allLengthsPositive':bool(min(ls)>=0)})
(D/'three-fold-frame-diagnostic.json').write_text(json.dumps({'start':start,'target':target.tolist(),'branches':out},indent=2)+'\n');print(json.dumps(out,indent=2))
