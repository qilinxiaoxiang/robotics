from context import *
import sys
sys.path.insert(0,str(I));from wire_geometry import primitives,sample,tube
parts,hashes=inventory();obs=load_obstacles(parts,np.array([[12,8,110],[79,31,153]]));src=F/'smt-header-package.json';ports=read(src)['gpioHeaderProposal']['piPorts'];out=[]
for net,pin,x in [('gnd',9,24.45),('3v3',1,25.55),('sda',3,26.65),('scl',5,27.75)]:
 p=next(p for p in ports if p['physicalPin']==pin);start=np.array(p['wireExitWorldMm']);u=np.array(p['outwardAxis']);y=start[1]+1.27
 pts=[start.tolist(),(start+u*2).tolist(),[73.4,y,116],[73.4,y,148],[65,y,148],[54,y,146],[46,y,142],[46,12,137],[x,12,137],[x,12,125]]
 try:
  pr=primitives(pts,2);q,t=sample(pr);self=self_check_streamed(pr,q,.8);m=tube(q,t,.4);c=check(m,obs);hits=[r for r in c if r['volumeMm3']>1e-6];f=D/(net+'-head.stl');m.export(f);row={'key':'imu_'+net+'_head','file':str(f),'sha256':sha(f),'points':pts,'radius':2,'diameter':.8,'length':sum(p['lengthMm']for p in pr),'primitives':pr,'self':self,'checks':c,'hits':hits,'passed':not hits};out.append(row);print(net,hits,flush=True)
 except Exception as e:out.append({'key':net,'error':str(e)});print(net,str(e),flush=True)
(D/'imu-head-check.json').write_text(json.dumps({'sourceHashes':hashes|{str(Path(__file__)):sha(__file__),str(D/'context.py'):sha(D/'context.py')},'rows':out,'scope':'Head end of the four IMU conductors; route and other-wire acceptance pending.'},indent=2))
