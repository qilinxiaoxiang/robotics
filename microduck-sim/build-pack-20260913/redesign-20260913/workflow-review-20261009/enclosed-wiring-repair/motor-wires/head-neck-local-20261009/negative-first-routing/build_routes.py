from check_local import *
from wire_geometry import primitives,sample,tube,self_check
plan=json.loads((D/'plan.json').read_text());rows=[]
for r in plan['routes']:
 a=plan['ports'][r['fromPort']];b=plan['ports'][r['toPort']]
 for k in [-1,0,1]:
  A=np.array(a['shoulder'])+2.5*k*np.array(a['width'])-.6*np.array(a['outward']);B=np.array(b['shoulder'])+2.5*k*np.array(b['width'])-.6*np.array(b['outward'])
  if r['id']=='ttl-15-14':
   z=132-1.6*k;pts=[A,[A[0],12,A[2]],[A[0],12,z],[-20,12,z],[-20,B[1],z],[-20,B[1],B[2]],B]
  elif r['id']=='ttl-14-13':
   y=-18+1.8*k;z=131.8+1.8*k;pts=[A,[-20,A[1],A[2]],[-20,y,A[2]],[-20,y,z],[B[0],y,z],[B[0],B[1],z],B]
  elif r['id']=='ttl-13-11':
   z=132.8+1.8*k;y=14+1.8*k;x=6+1.8*k;pts=[A,[A[0],A[1],z],[A[0],y,z],[x,y,z],[x,y,98],[x,-18,98],[x,-18,B[2]],[B[0],-18,B[2]],B]
  else:
   # Keep spare dressable along the stationary neck side, not a rigid cross-leg bridge.
   x=43+1.8*k;y=-23-1.8*k;z=57.4+1.8*k
   pts=[A,[A[0],y,A[2]],[x,y,A[2]],[x,y,z],[x+8,y,z],[x+8,y,B[2]],[B[0],y,B[2]],B]
  pts=np.array(pts,dtype=float);pr=primitives(pts,R=2);p,t=sample(pr);check=self_check(pr,p)
  mesh=tube(p,t);key=r['id']+'-wire-'+str(k+2);f=D/(key+'.stl');mesh.export(f)
  length=sum(x['lengthMm']for x in pr)
  rows.append({'key':key,'routeId':r['id'],'file':str(f),'sha256':sha(f),'controlPointsMm':pts.tolist(),'primitives':pr,'lengthMm':length,'nominalCableLengthMm':100 if length<90 else 180,'diameterReceivingMm':1.5,'bendRadiusAssumptionMm':2,'selfClearance':check,'wireSlot':k,'fromPort':r['fromPort'],'toPort':r['toPort']});print(key,round(length,3),flush=True)
(D/'routes.json').write_text(json.dumps({'parts':rows,'candidateOnly':True,'sourceHashes':{str(D/'plan.json'):sha(D/'plan.json'),str(Path(__file__)):sha(__file__)},'wholeHarnessAccepted':False,'stockFlexibleSpanVerified':False},indent=2)+'\n')
