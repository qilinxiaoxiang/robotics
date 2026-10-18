from check_local import *
from wire_geometry import primitives,sample,tube,self_check
plan=json.loads((D/'plan.json').read_text());rows=[]
for r in plan['routes']:
 a=plan['ports'][r['fromPort']];b=plan['ports'][r['toPort']]
 for k in [-1,0,1]:
  A=np.array(a['shoulder'])+2.5*k*np.array(a['width'])-.6*np.array(a['outward']);B=np.array(b['shoulder'])+2.5*k*np.array(b['width'])-.6*np.array(b['outward'])
  if r['id']=='ttl-15-14':
   z=132.7-1.6*k;back=-23;lane=[-20.4,-18.6,-14.8][k+1];vx=-18.8;zb=B[2]+5*(k+1);pts=[A,[A[0],12,A[2]],[A[0],12,z],[-14,12,z],[-14,lane,z],[vx,lane,126.7],[vx,lane,zb],[back,lane,zb],[back,B[1],zb]];pts+=([[back,B[1],B[2]]] if k!=-1 else []);pts+=[B]
  elif r['id']=='ttl-14-13':
   z=132.5;y=[-16.8,-13,-10.5][k+1];back=-22.3-1.8*k;turn=2.2-2.2*k;pts=[A,[back,A[1],A[2]],[back,y,A[2]],[back+3,y,128],[-12,y,128],[-12,y,z],[turn,y,z],[turn,B[1]+2.8,z],[B[0],B[1]+2.8,z],[B[0],B[1],128],B]
  elif r['id']=='ttl-13-11':
   z=134.4;y=A[1]+4;x=13.8+1.8*k;lead=[[A[0],A[1],126.45],[37.3,A[1]+4.8,z]] if k==-1 else [[A[0],A[1],126.45],[A[0],y,z]];y=A[1]+(4.8 if k==-1 else 4);pts=[A,*lead,[x,y,z],[x,8,z],[x,8,130.2],[x,12,130.2],[x,12,101.5],[x,-20,93],[10+2.4*k,-20,88],[10+2.4*k,-20,B[2]],[B[0],-20,B[2]],B]
  else:
   # Keep spare dressable along the stationary neck side, not a rigid cross-leg bridge.
   x=40+1.8*k;y=-23-1.8*k;z=57.4+1.8*k
   pts=[A,[A[0],y,A[2]],[x,y,A[2]],[x,y,z],[x+4.5,y,z],[x+4.5,y,B[2]],[B[0],y,B[2]],B]
  pts=np.array(pts,dtype=float);pr=primitives(pts,R=2);p,t=sample(pr);check=self_check(pr,p)
  mesh=tube(p,t);key=r['id']+'-wire-'+str(k+2);f=D/(key+'.stl');mesh.export(f)
  length=sum(x['lengthMm']for x in pr)
  rows.append({'key':key,'routeId':r['id'],'file':str(f),'sha256':sha(f),'controlPointsMm':pts.tolist(),'primitives':pr,'lengthMm':length,'nominalCableLengthMm':100 if r['id'] in ['ttl-14-13','ttl-11-12'] else 180,'diameterReceivingMm':1.5,'bendRadiusAssumptionMm':2,'selfClearance':check,'wireSlot':k,'fromPort':r['fromPort'],'toPort':r['toPort']});print(key,round(length,3),flush=True)
(D/'routes.json').write_text(json.dumps({'parts':rows,'candidateOnly':True,'sourceHashes':{str(D/'plan.json'):sha(D/'plan.json'),str(Path(__file__)):sha(__file__)},'wholeHarnessAccepted':False,'stockFlexibleSpanVerified':False},indent=2)+'\n')
