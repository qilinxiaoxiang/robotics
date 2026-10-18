"""One hand-dimensioned camera exit, above the current header, no optimizer."""
from pathlib import Path
import json,math,os,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent.parent;O=D/'audio-relocation';Q=Path(__file__).resolve().parent
ns={'__file__':str(O/'check_one_pose.py')};exec((O/'check_one_pose.py').read_text().split('Tp=')[0],ns)
np=ns['np'];tm=ns['tm'];mf=ns['mf'];load=ns['load'];pm=ns['pm'];ctx=ns['ctx'];sha=ns['sha'];H=ns['H']
p=np.array([75.63,4.3706236,131.1145958]);t=np.array([0.,1,0]);w=np.array([0.,0,1]);L=0.;bends=[];pr=[]
ops=[('S',15.6293764),('B',math.pi,0,1,1),('S',8),('B',math.pi,math.pi/4,-1,1),('S',16.16396273092082),('B',math.pi/2,0,-1,1),('S',38.63)]
for op in ops:
 if op[0]=='S':
  x=op[1];pr.append({'kind':'straight','s0':L,'s1':L+x,'p':p.copy(),'t':t.copy(),'w':w.copy()});p+=t*x;L+=x
 else:
  a,ph,sg,R=op[1:];n=np.cross(t,w);e=w*math.cos(ph)+t*math.sin(ph);q=t*math.cos(ph)-w*math.sin(ph);x=R*a/math.cos(ph);b={'kind':'cylindrical','s0':L,'s1':L+x,'p':p.copy(),'t':t.copy(),'w':w.copy(),'n':n.copy(),'e':e,'q':q,'angle':a,'phi':ph,'sign':sg,'R':R};bends.append(b);pr.append(b);p=p+e*(R*a*math.tan(ph))+q*R*math.sin(a)+n*(sg*R*(1-math.cos(a)));qp=q*math.cos(a)+n*sg*math.sin(a);t=e*math.sin(ph)+qp*math.cos(ph);w=e*math.cos(ph)-qp*math.sin(ph);L+=x
src=H/'camera-ribbon-repair/check_spacer2_tilted_complete.py';frag=src.read_text().split('def at(s,v):')[1].split('overlay=json.loads')[0];exec('def at(s,v):'+frag)
s=build(5,L);out=Q/'camera-manual-over-header-world.stl';pm.export(ctx,s,out)
r={'completeRoute':False,'prefixMaterialLengthMm':L,'endpoint':p.tolist(),'tangent':t.tolist(),'widthAxis':w.tolist(),'widthReceiving':'16mm first35mm, taper to11.5 by40, engineering conservative terminal transition—not manufacturer length','thicknessReceivingMm':.3,'minimumRadiusMm':1,'primitives':[{k:v.tolist()if isinstance(v,np.ndarray)else v for k,v in z.items()}for z in pr],'checks':[],'sources':{},'mesh':str(out),'meshSha256':sha(out)}
inv=json.loads((O/'positive-y13-check.json').read_text())['inventory'];inv+=[{'id':'current_amp','file':str(O/'amplifier-positive-y13-world.stl'),'worldTransform':np.eye(4).tolist()}]
for row in inv:
 f=Path(row['file']);T=np.array(row['worldTransform'])
 if row['id']=='current_cap':f=O/'positive-y13-native/closed-cap-Pi-audio-positive-y13-world.stl';T=np.eye(4)
 ob=load(f).transform(T[:3]);a=np.array(s.bounding_box()).reshape(2,3);b=np.array(ob.bounding_box()).reshape(2,3);sep=np.any(a[1]<b[0])or np.any(b[1]<a[0]);qq=None if sep else s^ob;v=0 if sep else max(0,qq.volume());r['checks'].append({'key':row['id'],'volumeMm3':v,'bounds':list(qq.bounding_box())if v>1e-6 else None});r['sources'][str(f)]=sha(f);del ob;gc.collect()
r['hits']=[x for x in r['checks']if x['volumeMm3']>1e-6];r['prefixClear']=not r['hits'];r['scriptSha256']=sha(__file__);(Q/'camera-manual-over-header.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'length':L,'end':p.tolist(),'hits':r['hits']}))
