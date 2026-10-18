"""One manually dimensioned CSI exit turn; no layout or route optimization."""
from pathlib import Path
import json,math,os,sys,gc,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent.parent;O=D/'audio-relocation';Q=Path(__file__).resolve().parent
ns={'__file__':str(O/'check_one_pose.py')};exec((O/'check_one_pose.py').read_text().split('Tp=')[0],ns)
np=ns['np'];tm=ns['tm'];mf=ns['mf'];load=ns['load'];pm=ns['pm'];ctx=ns['ctx'];sha=ns['sha']
# Start at the current Pi mouth; the mating tongue itself is not a routing obstacle test.
p=np.array([59.,-33.4999981,133.81]);t=np.array([0.,-1.,0.]);w=np.array([1.,0.,0.]);n=np.cross(t,w);R=1.5;lead=.5;tail=8.;width=11.5;th=.3
stations=[(p,w,n),(p+t*lead,w,n)]
for a in np.linspace(0,math.pi,81)[1:]:
 c=p+t*lead+t*R*math.sin(a)+n*R*(1-math.cos(a));tt=t*math.cos(a)+n*math.sin(a);stations.append((c,w,np.cross(tt,w)))
c=stations[-1][0];stations.append((c-t*tail,w,-n))
vs=[]
for c,ww,nn in stations:
 for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]:vs.append(c+ww*x*width/2+nn*y*th/2)
fs=[[0,2,1],[0,3,2]]
for k in range(len(stations)-1):
 for j in range(4):a=k*4+j;b=k*4+(j+1)%4;cc=b+4;d=a+4;fs += [[a,b,cc],[a,cc,d]]
z=4*(len(stations)-1);fs += [[z,z+1,z+2],[z,z+2,z+3]]
m=tm.Trimesh(vs,fs,process=True);m.fix_normals();assert m.is_watertight;s=mf.Manifold(mf.Mesh64(np.array(m.vertices),np.array(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError
out=Q/'pi-exit-U-R1p5-world.stl';pm.export(ctx,s,out)
r={'completeRoute':False,'purpose':'One hand-selected bend at the current Pi CSI mouth; no rigid printed part change','radiusMm':R,'outsideStraightMm':lead,'widthMm':width,'thicknessReceivingMm':th,'receivingAssumptionsNotManufacturerLimits':True,'portMouthMm':p.tolist(),'checks':[],'sources':{},'mesh':str(out),'meshSha256':sha(out)}
inv=json.loads((O/'positive-y13-check.json').read_text())['inventory'];amp={'id':'current_amp','file':str(O/'amplifier-positive-y13-world.stl'),'worldTransform':np.eye(4).tolist()};inv+= [amp]
for row in inv:
 f=Path(row['file']);T=np.array(row['worldTransform'])
 if row['id']=='current_cap':f=O/'positive-y13-native/closed-cap-Pi-audio-positive-y13-world.stl';T=np.eye(4)
 ob=load(f).transform(T[:3]);a=np.array(s.bounding_box()).reshape(2,3);b=np.array(ob.bounding_box()).reshape(2,3);sep=np.any(a[1]<b[0])or np.any(b[1]<a[0]);v=0 if sep else max(0,(s^ob).volume());r['checks'].append({'key':row['id'],'volumeMm3':v});r['sources'][str(f)]=sha(f);del ob;gc.collect()
r['hits']=[x for x in r['checks'] if x['volumeMm3']>1e-6];r['localTurnClear']=not r['hits'];r['sourceScriptSha256']=sha(__file__);(Q/'pi-exit-U-R1p5.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'checks':len(r['checks']),'hits':r['hits'],'localTurnClear':r['localTurnClear']}))
