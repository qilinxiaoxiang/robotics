from context import *
import sys
sys.path.insert(0,str(I));from wire_geometry import primitives,sample,tube,self_check
parts,hashes=inventory();obs=load_obstacles(parts,np.array([[-12,-40,54],[42,40,135]]));out=[]
for key,x,y,side,R,od in [('head5v',17.9,-7.6,21,4,2.5),('headgnd',20.7,-3.8,24,4,2.5),('data',23,1,27,3,1.5)]:
 lane={'head5v':-4,'headgnd':1,'data':6}[key]
 pts=([[6,y,55],[6,y,61],[lane,y,69],[lane,side,78],[lane,side,84]] if lane!=6 else [[6,y,55],[6,y,63],[6,side,74],[6,side,84]])+[[x,side,93],[x,side,104],[x,12,104],[x,12,133]]
 try:
  pr=primitives(pts,R);q,t=sample(pr);self=self_check_streamed(pr,q,od);m=tube(q,t,od/2);c=check(m,obs);hits=[r for r in c if r['volumeMm3']>1e-6];f=D/(key+'-lower-entry.stl');m.export(f);row={'key':key,'file':str(f),'sha256':sha(f),'points':pts,'radius':R,'diameter':od,'length':sum(p['lengthMm']for p in pr),'primitives':pr,'self':self,'checks':c,'hits':hits,'passed':not hits};out.append(row);print(key,hits,flush=True)
 except Exception as e:out.append({'key':key,'error':str(e)});print(key,str(e),flush=True)
(D/'lower-entry-check.json').write_text(json.dumps({'sourceHashes':hashes|{str(Path(__file__)):sha(__file__)},'scope':'Neutral lower neck wiring example; dynamic slack and self/other-wire checking still required','rows':out},indent=2))
