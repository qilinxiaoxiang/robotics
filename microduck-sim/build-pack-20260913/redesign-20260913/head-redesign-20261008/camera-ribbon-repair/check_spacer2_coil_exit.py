from pathlib import Path
f=Path(__file__).parent/'check_spacer2_full_ribbon.py';exec(compile(f.read_text().split('keys=sorted(')[0],str(f),'exec'))
# One turn, closed ribbon with actual inner exit; not full harness.
theta=np.linspace(0,2*math.pi,801);rr=8-.5*theta/(2*math.pi);pp=np.c_[60+rr*np.cos(theta),-26+rr*np.sin(theta),np.full(len(theta),121.5)];tt=np.c_[-.5/(2*math.pi)*np.cos(theta)-rr*np.sin(theta),-.5/(2*math.pi)*np.sin(theta)+rr*np.cos(theta),np.zeros(len(theta))];tt/=np.linalg.norm(tt,axis=1)[:,None];ww=np.tile([0.,0,1],(len(theta),1));P=[*pp];W=[*ww];N=[*np.cross(tt,ww)];p=pp[-1].copy();t=tt[-1].copy();w=ww[-1].copy();length=float(sum(np.linalg.norm(np.diff(pp,axis=0),axis=1)))
def bend(angle,R,direction):
 global p,t,w,length
 # q is the bending direction; preserve exact orthonormal frame.
 q=np.array(direction,float);q-=t*np.dot(q,t);q/=np.linalg.norm(q);axis=np.cross(t,q);wwparallel=axis*np.dot(w,axis);wwperp=w-wwparallel
 for a in np.linspace(0,angle,161)[1:]:
  tn=t*math.cos(a)+q*math.sin(a);wn=wwparallel+wwperp*math.cos(a)+np.cross(axis,wwperp)*math.sin(a);pn=p+R*math.sin(a)*t+R*(1-math.cos(a))*q;P.append(pn);W.append(wn);N.append(np.cross(tn,wn))
 p=np.array(P[-1]);t=t*math.cos(angle)+q*math.sin(angle);w=np.array(W[-1]);length+=R*angle
bend(math.pi,3.75,[-1,0,0]);bend(math.pi/2,1,[0,0,1])
for d in np.linspace(0,10,51)[1:]:P.append(p+t*d);W.append(w);N.append(np.cross(t,w))
p=p+10*t;length+=10
bend(math.pi/2,1,[0,1,0]);P=np.array(P);W=np.array(W);N=np.array(N);nv=9;vv=np.linspace(-5.75,5.75,nv);co=(P[:,None,:]+W[:,None,:]*vv[None,:,None]).reshape(-1,3);nn=np.repeat(N,nv,axis=0);count=len(co);fs=[]
for i in range(len(P)-1):
 for j in range(nv-1):
  a=i*nv+j;b=a+1;c=b+nv;d=a+nv;fs.extend([[a,c,b],[a,d,c],[a+count,b+count,c+count],[a+count,c+count,d+count]])
for i in range(len(P)-1):
 for j in [0,nv-1]:a=i*nv+j;b=a+nv;fs.extend([[a,b,b+count],[a,b+count,a+count]])
for i in [0,len(P)-1]:
 for j in range(nv-1):a=i*nv+j;b=a+1;fs.extend([[a,b,b+count],[a,b+count,a+count]])
mesh=tm.Trimesh(np.r_[co-.15*nn,co+.15*nn],fs,process=True);tm.repair.fix_normals(mesh);assert mesh.is_watertight;solid=mf.Manifold(mf.Mesh64(mesh.vertices.astype(np.float64),mesh.faces.astype(np.uint64)));assert solid.status()==mf.Error.NoError
r={'accepted':False,'scope':'Single coil and physical inner escape only; neither terminal attached','materialLengthMm':length,'bounds':solid.bounding_box(),'start':P[0].tolist(),'end':P[-1].tolist(),'endTangent':t.tolist(),'endWidth':w.tolist(),'checks':[],'sourceHashes':n['hashes']}
keys=sorted((set(n['P'])|set(files))-removed)
for key in keys:
 if key=='openrb':
  em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));solids=[load(Path(z['mesh'])) for z in em['components'] if not (np.any(np.array(z['bounds'])[1]<np.array(solid.bounding_box())[:3]) or np.any(np.array(z['bounds'])[0]>np.array(solid.bounding_box())[3:]))];v=sum(n['volume'](solid,z)[0] for z in solids);del solids
 else:
  ob=load(H/files[key]) if key in files else n['source'](key)
  if key in shiftKeys:ob=ob.translate(delta)
  v,bb=n['volume'](solid,ob);del ob
 r['checks'].append({'obstacle':key,'overlapMm3':v});gc.collect()
 if v>1e-6:print(key,v,flush=True)
r['mesh']=export(solid,'spacer2-onecoil-inner-exit');(O/'spacer2-onecoil-inner-exit.json').write_text(json.dumps(r,indent=2)+'\n');print('length',length)
