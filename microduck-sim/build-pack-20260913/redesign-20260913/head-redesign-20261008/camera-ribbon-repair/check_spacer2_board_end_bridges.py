from pathlib import Path
f=Path(__file__).parent/'check_spacer2_prefix_current.py';exec(compile(f.read_text().split("solid=load(O/")[0],str(f),'exec'))
r={'accepted':False,'scope':'Two finite port-to-board-end bridge candidates, no200mm/closure claim; actualRev2 narrowbody,width16 first35mmfrommaterialtip+taper5,.3receiving,R1','cases':[],'sourceHashes':n['hashes']}
for case in ['negative-end-C50p5','positive-end-free22']:
 p=np.array([75.63,9.3706236,131.1145958]);t=np.array([0.,1,0]);w=np.array([0.,0,1]);P=[p.copy()];N=[np.cross(t,w)];ss=[5.];length=5.
 def line(L):
  global p,length
  for z in np.linspace(0,L,math.ceil(L/.5)+1)[1:]:P.append(p+t*z);N.append(np.cross(t,w));ss.append(length+z)
  p=P[-1].copy();length+=L
 def turn(angle,sign):
  global p,t,length
  nn=np.cross(t,w)
  for a in np.linspace(0,angle,math.ceil(angle/.025)+1)[1:]:P.append(p+t*math.sin(a)+sign*nn*(1-math.cos(a)));N.append(np.cross(t*math.cos(a)+sign*nn*math.sin(a),w));ss.append(length+a)
  p=P[-1].copy();t=t*math.cos(angle)+sign*nn*math.sin(angle);length+=angle
 if case.startswith('negative'):
  line(4);turn(math.pi-.07,-1);line(50.5);turn(math.pi/2,1);line(10);turn(math.pi/2,1);line(6)
 else:
  line(22);turn(math.pi/2,-1);line(13.5);turn(math.pi/2,-1);line(6)
 P=np.array(P);N=np.array(N);ss=np.array(ss);ww=np.where(ss<=35,16,np.where(ss<40,16-.9*(ss-35),11.5));nv=9;vv=np.linspace(-.5,.5,nv);co=(P[:,None,:]+w[None,None,:]*vv[None,:,None]*ww[:,None,None]).reshape(-1,3);nn=np.repeat(N,nv,axis=0);count=len(co);fs=[]
 for i in range(len(P)-1):
  for j in range(nv-1):
   a=i*nv+j;b=a+1;c=b+nv;d=a+nv;fs.extend([[a,c,b],[a,d,c],[a+count,b+count,c+count],[a+count,c+count,d+count]])
 for i in range(len(P)-1):
  for j in [0,nv-1]:a=i*nv+j;b=a+nv;fs.extend([[a,b,b+count],[a,b+count,a+count]])
 for i in [0,len(P)-1]:
  for j in range(nv-1):a=i*nv+j;b=a+1;fs.extend([[a,b,b+count],[a,b+count,a+count]])
 mesh=tm.Trimesh(np.r_[co-.15*nn,co+.15*nn],fs,process=True);tm.repair.fix_normals(mesh);assert mesh.is_watertight;solid=mf.Manifold(mf.Mesh64(mesh.vertices.astype(np.float64),mesh.faces.astype(np.uint64)));assert solid.status()==mf.Error.NoError
 keys=sorted((set(n['P'])|set(files))-removed);row={'case':case,'materialPrefixLengthMm':length,'end':p.tolist(),'tangent':t.tolist(),'mesh':export(solid,case),'expectedObstacles':len(keys),'completedObstacles':0,'checks':[]}
 for key in keys:
  if key=='openrb':
   em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));bb=np.array(solid.bounding_box()).reshape(2,3);v=0
   for z in em['components']:
    zb=np.array(z['bounds'])
    if np.any(bb[1]<zb[0]) or np.any(zb[1]<bb[0]):continue
    ob=load(Path(z['mesh']));v+=n['volume'](solid,ob)[0];del ob
   bounds=None
  else:
   ob=load(H/files[key]) if key in files else n['source'](key)
   if key in shiftKeys:ob=ob.translate(delta)
   v,bounds=n['volume'](solid,ob);del ob
  row['checks'].append({'obstacle':key,'overlapMm3':v,'bounds':bounds});row['completedObstacles']+=1;gc.collect()
  if v>1e-6:print(case,key,v,flush=True)
 r['cases'].append(row);(O/'spacer2-board-end-bridges.json').write_text(json.dumps(r,indent=2)+'\n');del solid,mesh;gc.collect()
