from context import *
import sys
sys.path.insert(0,str(I));from wire_geometry import primitives,sample,tube
parts,hashes=inventory();obs=load_obstacles(parts,np.array([[-14,-37,54],[33,36,135]]));out=[]
for i,(net,x) in enumerate(zip(['gnd','3v3','sda','scl'],[24.45,25.55,26.65,27.75])):
 y=-29+i;ys=-32+3*i;side=25+1.1*i;far=31+1.1*i;lane=-8-1.2*i
 pts=[[6,y,55],[6,y,58],[6,ys,61],[6,ys,70],[lane,ys,79-3*i],[lane,far,79-3*i],[lane,far,91],[x,far,91],[x,side,95],[x,side,104],[x,12,104],[x,12,133]]
 try:
  pr=primitives(pts,2);q,t=sample(pr);self=self_check_streamed(pr,q,.8);m=tube(q,t,.4);c=check(m,obs);hits=[r for r in c if r['volumeMm3']>1e-6];f=D/(net+'-extension-lower.stl');m.export(f);row={'key':'imu_'+net+'_extension','file':str(f),'sha256':sha(f),'points':pts,'radius':2,'diameter':.8,'length':sum(p['lengthMm']for p in pr),'primitives':pr,'self':self,'checks':c,'hits':hits,'passed':not hits};out.append(row);print(net,hits,flush=True)
  splice=trimesh.creation.cylinder(radius=1.0/np.cos(np.pi/48),height=6,sections=48);splice.apply_translation([6,ys,65]);sc=check(splice,obs);sf=D/(net+'-extension-splice.stl');splice.export(sf);sh=[r for r in sc if r['volumeMm3']>1e-6];row['splice']={'key':'imu_'+net+'_splice','file':str(sf),'sha256':sha(sf),'center':[6,ys,65],'axis':[0,0,1],'length':6,'diameter':2,'checks':sc,'hits':sh};print(net,'splice',sh,flush=True)
 except Exception as e:out.append({'key':net,'error':str(e)});print(net,str(e),flush=True)
(D/'imu-extension-check.json').write_text(json.dumps({'sourceHashes':hashes|{str(Path(__file__)):sha(__file__),str(D/'context.py'):sha(D/'context.py')},'scope':'Four body-side IMU extensions to the head entry; complete head termination and other-wire checks not yet accepted.','rows':out},indent=2))
